"""Signals API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select

from src.api.auth import verify_api_key
from src.api.schemas.responses import DecisionResponse, SignalResponse
from src.core.database import get_session
from src.models.execution import Decision
from src.models.signal import Signal

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/signals", response_model=list[SignalResponse])
async def get_signals(
    request: Request,
    limit: int = Query(50, ge=1, le=1000, description="Number of signals to return"),
    strategy: str | None = Query(None, description="Filter by strategy name"),
    direction: str | None = Query(None, description="Filter by direction (LONG/SHORT)"),
    _api_key: str = Depends(verify_api_key),
):
    """Get recent trading signals."""
    try:
        async with get_session() as session:
            stmt = select(Signal).order_by(Signal.timestamp.desc()).limit(limit)

            if strategy:
                stmt = stmt.where(Signal.strategy_name == strategy)
            if direction:
                stmt = stmt.where(Signal.direction == direction)

            result = await session.execute(stmt)
            signals = result.scalars().all()

            # Get decisions for these signals
            signal_ids = [sig.id for sig in signals]
            decision_stmt = select(Decision).where(Decision.signal_id.in_(signal_ids))
            decision_result = await session.execute(decision_stmt)
            decisions = {dec.signal_id: dec for dec in decision_result.scalars().all()}

            return [
                SignalResponse(
                    id=sig.id,
                    timestamp=sig.timestamp,
                    symbol=sig.symbol,
                    direction=sig.direction,
                    strategy_name=sig.strategy_name,
                    timeframe=sig.timeframe,
                    confidence=sig.confidence,
                    signal_strength=sig.signal_strength,
                    suggested_entry=sig.suggested_entry,
                    suggested_stop=sig.suggested_stop,
                    suggested_target=sig.suggested_target,
                    decision=(
                        "APPROVED"
                        if sig.id in decisions and decisions[sig.id].decision == "APPROVE"
                        else "REJECTED" if sig.id in decisions else "PENDING"
                    ),
                )
                for sig in signals
            ]
    except Exception as e:
        logger.error(f"Failed to get signals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decisions", response_model=list[DecisionResponse])
async def get_decisions(
    request: Request,
    limit: int = Query(100, ge=1, le=1000, description="Number of decisions to return"),
    _api_key: str = Depends(verify_api_key),
):
    """Get recent decisions."""
    try:
        async with get_session() as session:
            stmt = select(Decision).order_by(Decision.timestamp.desc()).limit(limit)
            result = await session.execute(stmt)
            decisions = result.scalars().all()

            return [
                DecisionResponse(
                    id=dec.id,
                    timestamp=dec.timestamp,
                    signal_id=dec.signal_id,
                    approved=dec.decision == "APPROVE",
                    rejection_reason=dec.reason if dec.decision != "APPROVE" else None,
                    position_size=dec.position_size,
                    risk_amount=dec.risk_amount,
                    risk_pct=dec.risk_pct,
                )
                for dec in decisions
            ]
    except Exception as e:
        logger.error(f"Failed to get decisions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
