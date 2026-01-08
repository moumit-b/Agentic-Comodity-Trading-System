"""WebSocket endpoint for real-time updates."""

import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return

        # Convert Decimal to float for JSON serialization
        def decimal_to_float(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            raise TypeError

        message_json = json.dumps(message, default=decimal_to_float)

        # Send to all connections
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Failed to send message to client: {e}")
                disconnected.add(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)

    try:
        # Send initial connection message
        await websocket.send_json(
            {
                "type": "connected",
                "data": {"message": "Connected to trading dashboard"},
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Keep connection alive and listen for messages
        while True:
            try:
                # Wait for messages from client (ping/pong, subscriptions, etc.)
                data = await websocket.receive_text()
                logger.debug(f"Received message from client: {data}")

                # Echo back for now (can add custom handlers)
                await websocket.send_json(
                    {
                        "type": "ack",
                        "data": {"received": data},
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        manager.disconnect(websocket)


async def broadcast_account_update(balance: Decimal, buying_power: Decimal, market_open: bool):
    """Broadcast account update to all clients."""
    await manager.broadcast(
        {
            "type": "account_update",
            "data": {
                "balance": balance,
                "buying_power": buying_power,
                "market_open": market_open,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


async def broadcast_position_update(
    symbol: str, side: str, qty: int, unrealized_pnl: Decimal, unrealized_pnl_pct: Decimal
):
    """Broadcast position update to all clients."""
    await manager.broadcast(
        {
            "type": "position_update",
            "data": {
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


async def broadcast_signal(
    symbol: str, direction: str, strategy: str, confidence: float, entry: Decimal
):
    """Broadcast new signal to all clients."""
    await manager.broadcast(
        {
            "type": "signal_new",
            "data": {
                "symbol": symbol,
                "direction": direction,
                "strategy": strategy,
                "confidence": confidence,
                "entry": entry,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


async def broadcast_circuit_breaker(breaker_type: str, is_active: bool, reason: str | None = None):
    """Broadcast circuit breaker status change."""
    await manager.broadcast(
        {
            "type": "circuit_breaker",
            "data": {
                "breaker_type": breaker_type,
                "is_active": is_active,
                "reason": reason,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


async def broadcast_risk_update(portfolio_heat_pct: float, daily_pnl_pct: float, current_rsi: float):
    """Broadcast risk metrics update."""
    await manager.broadcast(
        {
            "type": "risk_update",
            "data": {
                "portfolio_heat_pct": portfolio_heat_pct,
                "daily_pnl_pct": daily_pnl_pct,
                "current_rsi": current_rsi,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
