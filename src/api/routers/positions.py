"""Positions API endpoints."""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select

from src.api.auth import verify_api_key
from src.api.schemas.responses import PositionResponse
from src.core.database import get_session
from src.models.position import Position

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/positions", response_model=list[PositionResponse])
async def get_positions(
    request: Request,
    _api_key: str = Depends(verify_api_key),
):
    """Get all open positions."""
    try:
        async with get_session() as session:
            stmt = select(Position).where(Position.is_open == True)
            result = await session.execute(stmt)
            positions = result.scalars().all()

            # TODO: Get current prices from Alpaca and calculate P&L
            return [
                PositionResponse(
                    id=pos.id,
                    symbol=pos.symbol,
                    side=pos.side,
                    qty=pos.qty,
                    entry_price=pos.entry_price,
                    current_price=pos.entry_price,  # TODO: Get current price
                    stop_loss=pos.stop_loss,
                    take_profit=pos.take_profit,
                    unrealized_pnl=Decimal("0"),  # TODO: Calculate
                    unrealized_pnl_pct=Decimal("0"),  # TODO: Calculate
                    opened_at=pos.entry_time,
                )
                for pos in positions
            ]
    except Exception as e:
        logger.error(f"Failed to get positions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
