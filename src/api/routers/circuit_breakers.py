"""Circuit breaker API endpoints."""

import logging
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from src.api.schemas.responses import CircuitBreakerResponse
from src.core.database import get_session
from src.models.risk import CircuitBreaker
from src.services.circuit_breakers import CircuitBreakerService

logger = logging.getLogger(__name__)

router = APIRouter()


class KillSwitchRequest(BaseModel):
    """Request to activate/clear kill switch."""

    action: str  # "activate" or "clear"
    reason: str | None = None


@router.get("/circuit-breakers", response_model=list[CircuitBreakerResponse])
async def get_circuit_breakers():
    """Get all circuit breaker statuses."""
    try:
        async with get_session() as session:
            stmt = select(CircuitBreaker).order_by(CircuitBreaker.timestamp.desc())
            result = await session.execute(stmt)
            breakers = result.scalars().all()

            # Group by breaker_type and get latest status
            breaker_map = {}
            for breaker in breakers:
                if breaker.breaker_type not in breaker_map:
                    breaker_map[breaker.breaker_type] = breaker

            all_breaker_types = [
                "DAILY_LOSS_LIMIT",
                "CONSECUTIVE_LOSSES",
                "MAX_POSITIONS",
                "MAX_DAILY_TRADES",
                "PORTFOLIO_HEAT",
                "VOLATILITY_SPIKE",
                "MANUAL_KILL_SWITCH",
            ]

            return [
                CircuitBreakerResponse(
                    breaker_type=breaker_type,
                    is_active=(
                        breaker_type in breaker_map
                        and breaker_map[breaker_type].cleared_at is None
                    ),
                    triggered_at=(
                        breaker_map[breaker_type].timestamp
                        if breaker_type in breaker_map
                        else None
                    ),
                    cleared_at=(
                        breaker_map[breaker_type].cleared_at
                        if breaker_type in breaker_map
                        else None
                    ),
                    reason=(
                        breaker_map[breaker_type].reason if breaker_type in breaker_map else None
                    ),
                )
                for breaker_type in all_breaker_types
            ]
    except Exception as e:
        logger.error(f"Failed to get circuit breakers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kill-switch")
async def manage_kill_switch(request: KillSwitchRequest):
    """Activate or clear the kill switch."""
    try:
        circuit_breaker = CircuitBreakerService()

        if request.action == "activate":
            await circuit_breaker.activate_kill_switch()
            return {"status": "success", "action": "activated", "reason": request.reason}
        elif request.action == "clear":
            cleared = await circuit_breaker.clear_kill_switch()
            return {"status": "success" if cleared else "failed", "action": "cleared"}
        else:
            raise HTTPException(status_code=400, detail="Invalid action")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to manage kill switch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/circuit-breakers/status")
async def get_breaker_status():
    """Get overall circuit breaker status."""
    try:
        circuit_breaker = CircuitBreakerService()

        # Check all breakers
        breaker_status = await circuit_breaker.check_all_breakers(
            daily_pnl_pct=Decimal("0"),
            consecutive_losses=0,
            portfolio_heat=Decimal("0"),
        )

        return {
            "is_tripped": breaker_status.is_tripped,
            "active_breakers": [b.value for b in breaker_status.active_breakers],
            "reasons": breaker_status.reasons,
            "trading_allowed": not breaker_status.is_tripped,
        }
    except Exception as e:
        logger.error(f"Failed to get breaker status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
