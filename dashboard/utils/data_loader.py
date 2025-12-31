"""Data loading utilities for dashboard."""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import select

from src.core.database import get_session
from src.models.account import AccountSnapshot, DailyLimit
from src.models.bars import Bar1m, BarAggregated, Indicator
from src.models.execution import Decision, Execution
from src.models.position import Position
from src.models.risk import CircuitBreaker
from src.models.settlement import Settlement
from src.models.signal import Signal
from src.services.alpaca_api import AlpacaService

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create new loop for nested async
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


@st.cache_data(ttl=5)
def load_account_status() -> dict[str, Any]:
    """Load current account status from Alpaca."""
    try:
        alpaca = AlpacaService()
        account = run_async(alpaca.get_account())

        return {
            "balance": Decimal(str(account.equity)),
            "buying_power": Decimal(str(account.buying_power)),
            "cash": Decimal(str(account.cash)),
            "portfolio_value": Decimal(str(account.portfolio_value)),
            "market_open": alpaca.is_market_open(),
            "timestamp": datetime.now(),
        }
    except Exception as e:
        logger.error(f"Failed to load account status: {e}")
        return {
            "balance": Decimal("0"),
            "buying_power": Decimal("0"),
            "cash": Decimal("0"),
            "portfolio_value": Decimal("0"),
            "market_open": False,
            "timestamp": datetime.now(),
        }


@st.cache_data(ttl=5)
def load_positions() -> pd.DataFrame:
    """Load open positions."""

    async def _load():
        async with get_session() as session:
            stmt = select(Position).where(Position.status == "OPEN")
            result = await session.execute(stmt)
            positions = result.scalars().all()

            if not positions:
                return pd.DataFrame()

            data = []
            for pos in positions:
                data.append(
                    {
                        "id": pos.id,
                        "symbol": pos.symbol,
                        "side": pos.side,
                        "qty": pos.qty,
                        "entry_price": pos.entry_price,
                        "current_price": pos.current_price or pos.entry_price,
                        "stop_loss": pos.stop_loss,
                        "take_profit": pos.take_profit,
                        "unrealized_pnl": pos.unrealized_pnl or Decimal("0"),
                        "unrealized_pnl_pct": pos.unrealized_pnl_pct or Decimal("0"),
                        "opened_at": pos.opened_at,
                    }
                )

            return pd.DataFrame(data)

    try:
        return run_async(_load())
    except Exception as e:
        logger.error(f"Failed to load positions: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=5)
def load_signals(limit: int = 50) -> pd.DataFrame:
    """Load recent signals."""

    async def _load():
        async with get_session() as session:
            stmt = select(Signal).order_by(Signal.timestamp.desc()).limit(limit)
            result = await session.execute(stmt)
            signals = result.scalars().all()

            if not signals:
                return pd.DataFrame()

            data = []
            for sig in signals:
                data.append(
                    {
                        "id": sig.id,
                        "timestamp": sig.timestamp,
                        "symbol": sig.symbol,
                        "direction": sig.direction.value,
                        "strategy_name": sig.strategy_name,
                        "timeframe": sig.timeframe,
                        "confidence": sig.confidence,
                        "signal_strength": sig.signal_strength,
                        "suggested_entry": sig.suggested_entry,
                        "suggested_stop": sig.suggested_stop,
                        "suggested_target": sig.suggested_target,
                    }
                )

            return pd.DataFrame(data)

    try:
        return run_async(_load())
    except Exception as e:
        logger.error(f"Failed to load signals: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=5)
def load_decisions(limit: int = 100) -> pd.DataFrame:
    """Load recent decisions."""

    async def _load():
        async with get_session() as session:
            stmt = select(Decision).order_by(Decision.timestamp.desc()).limit(limit)
            result = await session.execute(stmt)
            decisions = result.scalars().all()

            if not decisions:
                return pd.DataFrame()

            data = []
            for dec in decisions:
                data.append(
                    {
                        "id": dec.id,
                        "timestamp": dec.timestamp,
                        "symbol": dec.symbol,
                        "approved": dec.approved,
                        "rejection_reason": dec.rejection_reason or "",
                        "position_size": dec.position_size,
                        "risk_amount": dec.risk_amount,
                        "risk_pct": dec.risk_pct,
                    }
                )

            return pd.DataFrame(data)

    try:
        return run_async(_load())
    except Exception as e:
        logger.error(f"Failed to load decisions: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=5)
def load_executions(limit: int = 50) -> pd.DataFrame:
    """Load recent executions."""

    async def _load():
        async with get_session() as session:
            stmt = select(Execution).order_by(Execution.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            executions = result.scalars().all()

            if not executions:
                return pd.DataFrame()

            data = []
            for ex in executions:
                data.append(
                    {
                        "id": ex.id,
                        "created_at": ex.created_at,
                        "symbol": ex.symbol,
                        "side": ex.side,
                        "qty": ex.qty,
                        "filled_price": ex.filled_price,
                        "status": ex.status,
                        "requires_confirmation": ex.requires_confirmation,
                        "alpaca_order_id": ex.alpaca_order_id,
                    }
                )

            return pd.DataFrame(data)

    try:
        return run_async(_load())
    except Exception as e:
        logger.error(f"Failed to load executions: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=5)
def load_pending_confirmations() -> pd.DataFrame:
    """Load executions pending confirmation."""

    async def _load():
        async with get_session() as session:
            stmt = select(Execution).where(
                Execution.requires_confirmation == True, Execution.status == "PENDING"
            )
            result = await session.execute(stmt)
            executions = result.scalars().all()

            if not executions:
                return pd.DataFrame()

            data = []
            for ex in executions:
                data.append(
                    {
                        "id": ex.id,
                        "created_at": ex.created_at,
                        "symbol": ex.symbol,
                        "side": ex.side,
                        "qty": ex.qty,
                        "confirmation_sent_at": ex.confirmation_sent_at,
                    }
                )

            return pd.DataFrame(data)

    try:
        return run_async(_load())
    except Exception as e:
        logger.error(f"Failed to load pending confirmations: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=5)
def load_circuit_breakers() -> pd.DataFrame:
    """Load circuit breaker status."""

    async def _load():
        async with get_session() as session:
            stmt = select(CircuitBreaker).order_by(CircuitBreaker.triggered_at.desc())
            result = await session.execute(stmt)
            breakers = result.scalars().all()

            if not breakers:
                return pd.DataFrame()

            data = []
            for br in breakers:
                data.append(
                    {
                        "id": br.id,
                        "breaker_type": br.breaker_type,
                        "triggered_at": br.triggered_at,
                        "cleared_at": br.cleared_at,
                        "reason": br.reason,
                        "is_active": br.cleared_at is None,
                    }
                )

            return pd.DataFrame(data)

    try:
        return run_async(_load())
    except Exception as e:
        logger.error(f"Failed to load circuit breakers: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=5)
def load_settlement_calendar() -> pd.DataFrame:
    """Load settlement calendar for next 7 days."""

    async def _load():
        async with get_session() as session:
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=7)

            stmt = select(Settlement).where(
                Settlement.settlement_date >= start_date, Settlement.settlement_date <= end_date
            )
            result = await session.execute(stmt)
            settlements = result.scalars().all()

            if not settlements:
                return pd.DataFrame()

            data = []
            for s in settlements:
                data.append(
                    {
                        "id": s.id,
                        "trade_date": s.trade_date,
                        "settlement_date": s.settlement_date,
                        "symbol": s.symbol,
                        "qty": s.qty,
                        "proceeds": s.proceeds,
                        "settled": s.settled,
                    }
                )

            return pd.DataFrame(data)

    try:
        return run_async(_load())
    except Exception as e:
        logger.error(f"Failed to load settlement calendar: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=5)
def load_daily_performance() -> pd.DataFrame:
    """Load daily performance metrics."""

    async def _load():
        async with get_session() as session:
            stmt = select(DailyLimit).order_by(DailyLimit.date.desc()).limit(30)
            result = await session.execute(stmt)
            daily_limits = result.scalars().all()

            if not daily_limits:
                return pd.DataFrame()

            data = []
            for dl in daily_limits:
                data.append(
                    {
                        "date": dl.date,
                        "trades_count": dl.trades_count,
                        "daily_pnl": dl.daily_pnl,
                        "consecutive_losses": dl.consecutive_losses,
                    }
                )

            return pd.DataFrame(data)

    try:
        return run_async(_load())
    except Exception as e:
        logger.error(f"Failed to load daily performance: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=5)
def load_bars_1m(symbol: str, limit: int = 390) -> pd.DataFrame:
    """Load 1-minute bars for symbol (default: 1 trading day)."""

    async def _load():
        async with get_session() as session:
            stmt = (
                select(Bar1m)
                .where(Bar1m.symbol == symbol)
                .order_by(Bar1m.timestamp.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            bars = result.scalars().all()

            if not bars:
                return pd.DataFrame()

            data = []
            for bar in bars:
                data.append(
                    {
                        "timestamp": bar.timestamp,
                        "open": bar.open,
                        "high": bar.high,
                        "low": bar.low,
                        "close": bar.close,
                        "volume": bar.volume,
                    }
                )

            df = pd.DataFrame(data)
            # Reverse to chronological order
            return df.sort_values("timestamp").reset_index(drop=True)

    try:
        return run_async(_load())
    except Exception as e:
        logger.error(f"Failed to load 1m bars for {symbol}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=5)
def load_indicators(symbol: str, timeframe: str = "5m") -> pd.DataFrame:
    """Load technical indicators for symbol."""

    async def _load():
        async with get_session() as session:
            stmt = (
                select(Indicator)
                .where(Indicator.symbol == symbol, Indicator.timeframe == timeframe)
                .order_by(Indicator.timestamp.desc())
                .limit(100)
            )
            result = await session.execute(stmt)
            indicators = result.scalars().all()

            if not indicators:
                return pd.DataFrame()

            data = []
            for ind in indicators:
                data.append(
                    {
                        "timestamp": ind.timestamp,
                        "ema_8": ind.ema_8,
                        "ema_21": ind.ema_21,
                        "rsi": ind.rsi,
                        "macd": ind.macd,
                        "macd_signal": ind.macd_signal,
                        "macd_hist": ind.macd_hist,
                        "bb_upper": ind.bb_upper,
                        "bb_middle": ind.bb_middle,
                        "bb_lower": ind.bb_lower,
                        "vwap": ind.vwap,
                    }
                )

            df = pd.DataFrame(data)
            return df.sort_values("timestamp").reset_index(drop=True)

    try:
        return run_async(_load())
    except Exception as e:
        logger.error(f"Failed to load indicators for {symbol}: {e}")
        return pd.DataFrame()
