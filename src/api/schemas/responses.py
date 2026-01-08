"""Pydantic response models for API endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class AccountResponse(BaseModel):
    """Account status response."""

    balance: Decimal = Field(..., description="Account equity")
    buying_power: Decimal = Field(..., description="Available buying power")
    cash: Decimal = Field(..., description="Cash balance")
    portfolio_value: Decimal = Field(..., description="Portfolio value")
    market_open: bool = Field(..., description="Market open status")
    timestamp: datetime = Field(..., description="Response timestamp")


class PositionResponse(BaseModel):
    """Position response."""

    id: int
    symbol: str
    side: str
    qty: int
    entry_price: Decimal
    current_price: Decimal
    stop_loss: Decimal | None
    take_profit: Decimal | None
    unrealized_pnl: Decimal
    unrealized_pnl_pct: Decimal
    opened_at: datetime


class SignalResponse(BaseModel):
    """Signal response."""

    id: int
    timestamp: datetime
    symbol: str
    direction: str
    strategy_name: str
    timeframe: str
    confidence: float
    signal_strength: float
    suggested_entry: Decimal
    suggested_stop: Decimal
    suggested_target: Decimal
    decision: str | None = None  # APPROVED/REJECTED/PENDING


class DecisionResponse(BaseModel):
    """Decision response."""

    id: int
    timestamp: datetime
    signal_id: int
    approved: bool
    rejection_reason: str | None
    position_size: int | None
    risk_amount: Decimal | None
    risk_pct: Decimal | None


class ExecutionResponse(BaseModel):
    """Execution response."""

    id: int
    timestamp: datetime
    symbol: str
    side: str
    qty: int
    filled_price: Decimal | None
    status: str
    requires_confirmation: bool
    alpaca_order_id: str | None


class CircuitBreakerResponse(BaseModel):
    """Circuit breaker response."""

    breaker_type: str
    is_active: bool
    triggered_at: datetime | None
    cleared_at: datetime | None
    reason: str | None


class RiskMetricsResponse(BaseModel):
    """Risk metrics response."""

    portfolio_heat_pct: float
    daily_pnl_pct: float
    current_rsi: float
    daily_target_pct: float
    daily_limit_pct: float
    consecutive_losses: int
    max_consecutive_losses: int


class BarResponse(BaseModel):
    """Price bar response."""

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class IndicatorResponse(BaseModel):
    """Technical indicator response."""

    timestamp: datetime
    sma_20: float | None
    ema_20: float | None
    rsi: float | None
    atr: float | None
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    bb_upper: float | None
    bb_middle: float | None
    bb_lower: float | None


class ConfigurationResponse(BaseModel):
    """Configuration response."""

    automation_mode: str
    max_positions: int
    max_trades_per_day: int
    risk_per_trade_pct: float
    daily_profit_target_pct: float
    daily_loss_limit_pct: float
    max_portfolio_heat_pct: float
    max_consecutive_losses: int
    symbols: list[str]


class WebSocketMessage(BaseModel):
    """WebSocket message format."""

    type: str = Field(..., description="Message type")
    data: dict[str, Any] = Field(..., description="Message payload")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
