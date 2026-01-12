"""Account API endpoints."""

import logging
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.auth import verify_api_key
from src.api.schemas.responses import AccountResponse
from src.core.config import AlpacaConfig
from src.services.alpaca_api import AlpacaService

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/account", response_model=AccountResponse)
async def get_account(
    request: Request,
    _api_key: str = Depends(verify_api_key),
):
    """Get current account status."""
    try:
        alpaca = AlpacaService(AlpacaConfig())
        account = await alpaca.get_account()

        return AccountResponse(
            balance=Decimal(str(account.equity)),
            buying_power=Decimal(str(account.buying_power)),
            cash=Decimal(str(account.cash)),
            portfolio_value=Decimal(str(account.portfolio_value)),
            market_open=alpaca.is_market_open(),
            timestamp=datetime.utcnow(),
        )
    except Exception as e:
        logger.error(f"Failed to get account status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
