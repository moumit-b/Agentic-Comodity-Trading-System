"""Risk metrics API endpoints."""

import logging
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select

from src.agents.risk_manager import RiskManagerAgent
from src.api.auth import verify_api_key
from src.api.schemas.responses import BarResponse, IndicatorResponse, RiskMetricsResponse
from src.core.config import AlpacaConfig, TradingConfig
from src.core.database import get_session
from src.models.account import DailyLimit
from src.models.bars import Bar1m, Indicator
from src.services.alpaca_api import AlpacaService

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/risk/metrics", response_model=RiskMetricsResponse)
@limiter.limit("60/minute")
async def get_risk_metrics(
    request: Request,
    _api_key: str = Depends(verify_api_key),
):
    """Get current risk metrics."""
    try:
        config = TradingConfig()
        alpaca = AlpacaService(AlpacaConfig())
        risk_manager = RiskManagerAgent(config)

        # Get account balance
        account = await alpaca.get_account()
        account_balance = Decimal(str(account.equity))

        # Calculate portfolio heat
        portfolio_risk = await risk_manager.calculate_portfolio_heat(account_balance)
        portfolio_heat_pct = float(portfolio_risk.current_heat * 100)

        # Get today's P&L
        async with get_session() as session:
            today = datetime.utcnow().date()
            stmt = select(DailyLimit).where(DailyLimit.trade_date == today)
            result = await session.execute(stmt)
            daily_limit = result.scalar_one_or_none()

            if daily_limit:
                daily_pnl = daily_limit.current_pnl
                daily_pnl_pct = float((daily_pnl / account_balance) * 100)
                consecutive_losses = daily_limit.consecutive_losses
            else:
                daily_pnl_pct = 0.0
                consecutive_losses = 0

        # Get current RSI (placeholder - would get from indicators table)
        current_rsi = 50.0

        return RiskMetricsResponse(
            portfolio_heat_pct=portfolio_heat_pct,
            daily_pnl_pct=daily_pnl_pct,
            current_rsi=current_rsi,
            daily_target_pct=float(config.daily_profit_target_pct * 100),
            daily_limit_pct=float(config.daily_loss_limit_pct * 100),
            consecutive_losses=consecutive_losses,
            max_consecutive_losses=config.max_consecutive_losses,
        )
    except Exception as e:
        logger.error(f"Failed to get risk metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bars/{symbol}", response_model=list[BarResponse])
@limiter.limit("60/minute")
async def get_bars(
    request: Request,
    symbol: str = "",
    limit: int = 390,
    _api_key: str = Depends(verify_api_key),
):
    """Get price bars for symbol."""
    try:
        async with get_session() as session:
            stmt = (
                select(Bar1m)
                .where(Bar1m.symbol == symbol)
                .order_by(Bar1m.timestamp.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            bars = result.scalars().all()

            # Reverse to chronological order
            return [
                BarResponse(
                    timestamp=bar.timestamp,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                )
                for bar in reversed(bars)
            ]
    except Exception as e:
        logger.error(f"Failed to get bars for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators/{symbol}", response_model=list[IndicatorResponse])
@limiter.limit("60/minute")
async def get_indicators(
    request: Request,
    symbol: str = "",
    timeframe: str = "5m",
    limit: int = 100,
    _api_key: str = Depends(verify_api_key),
):
    """Get technical indicators for symbol."""
    try:
        async with get_session() as session:
            stmt = (
                select(Indicator)
                .where(Indicator.symbol == symbol, Indicator.timeframe == timeframe)
                .order_by(Indicator.timestamp.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            indicators = result.scalars().all()

            # Reverse to chronological order
            return [
                IndicatorResponse(
                    timestamp=ind.timestamp,
                    sma_20=ind.sma_20,
                    ema_20=ind.ema_20,
                    rsi=ind.rsi,
                    atr=ind.atr,
                    macd=ind.macd,
                    macd_signal=ind.macd_signal,
                    macd_histogram=ind.macd_histogram,
                    bb_upper=ind.bb_upper,
                    bb_middle=ind.bb_middle,
                    bb_lower=ind.bb_lower,
                )
                for ind in reversed(indicators)
            ]
    except Exception as e:
        logger.error(f"Failed to get indicators for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
