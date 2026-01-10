"""Configuration API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.auth import verify_api_key
from src.api.schemas.responses import ConfigurationResponse
from src.core.config import AutomationMode, TradingConfig

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class ModeChangeRequest(BaseModel):
    """Request to change automation mode."""

    mode: str  # ADVISORY, PAPER_AUTO, LIVE_CONFIRM, LIVE_AUTO


@router.get("/configuration", response_model=ConfigurationResponse)
@limiter.limit("60/minute")
async def get_configuration(
    request: Request,
    _api_key: str = Depends(verify_api_key),
):
    """Get current trading configuration."""
    try:
        config = TradingConfig()

        return ConfigurationResponse(
            automation_mode=config.automation_mode.value,
            max_positions=config.max_positions,
            max_trades_per_day=config.max_trades_per_day,
            risk_per_trade_pct=float(config.risk_per_trade_pct * 100),
            daily_profit_target_pct=float(config.daily_profit_target_pct * 100),
            daily_loss_limit_pct=float(config.daily_loss_limit_pct * 100),
            max_portfolio_heat_pct=float(config.max_portfolio_heat_pct * 100),
            max_consecutive_losses=config.max_consecutive_losses,
            symbols=config.symbols,
        )
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configuration/mode")
@limiter.limit("10/minute")  # Stricter limit for mode changes
async def change_automation_mode(
    request: Request,
    mode_request: ModeChangeRequest = None,
    _api_key: str = Depends(verify_api_key),
):
    """Change automation mode."""
    try:
        if not mode_request:
            raise HTTPException(status_code=400, detail="Request body required")

        # Validate mode
        try:
            mode = AutomationMode(mode_request.mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode. Must be one of: {[m.value for m in AutomationMode]}",
            )

        # TODO: Implement mode change logic
        # This would need to update the config or database

        logger.info(f"Automation mode change requested: {mode_request.mode}")

        return {
            "status": "success",
            "mode": mode_request.mode,
            "message": "Mode change requires system restart to take effect",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change automation mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
