"""Finnhub Data Agent - Handles real-time WebSocket data from Finnhub."""

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from typing import Callable, Coroutine

import websockets
from websockets.exceptions import ConnectionClosed
from websockets.protocol import State

from src.core.config import FinnhubConfig

logger = logging.getLogger(__name__)


class FinnhubDataAgent:
    """
    Agent responsible for streaming real-time trades from Finnhub WebSocket.
    
    Features:
    - WebSocket connection management (reconnect, ping)
    - Real-time trade aggregation (tick -> 1m bars)
    - Rate limit handling
    """

    def __init__(
        self,
        config: FinnhubConfig,
        on_bar_callback: Callable[[str, dict], Coroutine],
    ):
        """
        Initialize Finnhub Data Agent.

        Args:
            config: Finnhub configuration
            on_bar_callback: Async callback for completed bars (symbol, bar_data)
        """
        self.config = config
        self.on_bar_callback = on_bar_callback
        self.ws: websockets.WebSocketClientProtocol | None = None
        self.subscribed_symbols: list[str] = []
        self._running = False
        
        # Aggregation buffer: symbol -> {volume: 0, open: 0, high: 0, low: 0, close: 0, count: 0, start_time: ts}
        self._current_bars: dict[str, dict] = {}

    async def connect(self) -> None:
        """Establish WebSocket connection."""
        if not self.config.api_key.get_secret_value():
            raise ValueError("Finnhub API key not found")

        url = f"{self.config.ws_url}?token={self.config.api_key.get_secret_value()}"
        logger.info(f"Connecting to Finnhub: {self.config.ws_url}")
        
        try:
            self.ws = await websockets.connect(url, ping_interval=self.config.ws_ping_interval)
            self._running = True
            logger.info("Finnhub WebSocket connected")
        except Exception as e:
            logger.error(f"Finnhub connection failed: {e}")
            raise

    async def disconnect(self) -> None:
        """Close connection."""
        self._running = False
        if self.ws:
            await self.ws.close()
            self.ws = None
            logger.info("Finnhub disconnected")

    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to trade updates for symbols."""
        if not self.ws:
            raise RuntimeError("Not connected")

        self.subscribed_symbols = symbols
        for symbol in symbols:
            msg = {"type": "subscribe", "symbol": symbol}
            await self.ws.send(json.dumps(msg))
            logger.info(f"Subscribed to Finnhub: {symbol}")

    async def run(self) -> None:
        """Run message loop."""
        if not self.ws:
            raise RuntimeError("Not connected")

        logger.info("Starting Finnhub message loop")
        
        while self._running:
            try:
                message = await self.ws.recv()
                data = json.loads(message)
                
                if data.get("type") == "trade":
                    for trade in data["data"]:
                        await self._process_trade(trade)
                elif data.get("type") == "ping":
                    pass # Keep-alive
                
            except ConnectionClosed:
                logger.warning("Finnhub connection closed")
                if self._running:
                    raise # Let coordinator handle reconnect
                break
            except Exception as e:
                logger.error(f"Error processing Finnhub message: {e}")

    async def _process_trade(self, trade: dict) -> None:
        """
        Aggregate individual trades into 1-minute bars.
        
        Finnhub trade format: {"p": price, "s": symbol, "t": timestamp_ms, "v": volume}
        """
        symbol = trade["s"]
        price = float(trade["p"])
        volume = int(trade["v"])
        timestamp_ms = trade["t"]
        
        # Determine 1m bar bucket (truncate seconds)
        # Using current system time to ensure consistency with system clock,
        # or use trade time if latency is low. Finnhub sends UTC timestamp in ms.
        # Let's use trade time bucketed.
        trade_dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
        bar_start_time = trade_dt.replace(second=0, microsecond=0)
        
        # Check if we moved to a new bar
        current = self._current_bars.get(symbol)
        
        if current and current["start_time"] < bar_start_time:
            # Finalize previous bar
            await self._finalize_bar(symbol, current)
            # Reset for new bar
            self._current_bars[symbol] = self._init_new_bar(bar_start_time, price, volume)
        elif not current:
            # First bar
            self._current_bars[symbol] = self._init_new_bar(bar_start_time, price, volume)
        else:
            # Update current bar
            current["high"] = max(current["high"], price)
            current["low"] = min(current["low"], price)
            current["close"] = price
            current["volume"] += volume
            current["count"] += 1

    def _init_new_bar(self, start_time: datetime, price: float, volume: int) -> dict:
        return {
            "start_time": start_time,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": volume,
            "count": 1
        }

    async def _finalize_bar(self, symbol: str, bar_data: dict) -> None:
        """Emit completed bar to callback."""
        # Convert to format expected by MarketDataAgent
        final_bar = {
            "timestamp": bar_data["start_time"],
            "open": bar_data["open"],
            "high": bar_data["high"],
            "low": bar_data["low"],
            "close": bar_data["close"],
            "volume": bar_data["volume"],
            "trade_count": bar_data["count"],
            "vwap": None # Finnhub doesn't provide VWAP easily in Aggregation
        }
        
        logger.debug(f"Finnhub bar completed: {symbol} @ {final_bar['timestamp']}")
        await self.on_bar_callback(symbol, final_bar)

    def get_health_status(self) -> dict:
        """Return connection health status."""
        return {
            "connected": self.ws is not None and self.ws.state == State.OPEN,
            "subscribed": len(self.subscribed_symbols)
        }