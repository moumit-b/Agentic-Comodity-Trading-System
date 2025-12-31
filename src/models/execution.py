"""Execution and decision ORM models."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Decision(Base):
    """Risk management decisions on signals."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    signal_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("signals.id", ondelete="SET NULL")
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="NOW()"
    )
    decision: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # APPROVE, REJECT, HOLD
    reason: Mapped[str | None] = mapped_column(Text)

    # Risk parameters calculated
    position_size: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    risk_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    risk_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    portfolio_heat_after: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), comment="Portfolio heat if this trade is taken"
    )

    # Safety checks
    passed_portfolio_heat: Mapped[bool | None] = mapped_column()
    passed_daily_limits: Mapped[bool | None] = mapped_column()
    passed_settlement_check: Mapped[bool | None] = mapped_column()
    passed_time_check: Mapped[bool | None] = mapped_column()

    def __repr__(self) -> str:
        return (
            f"<Decision(signal_id={self.signal_id}, decision={self.decision}, "
            f"size={self.position_size})>"
        )


class Execution(Base):
    """Trade execution records."""

    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    decision_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("decisions.id", ondelete="SET NULL")
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="NOW()"
    )

    # Execution details
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # LONG, SHORT
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    filled_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    order_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # MARKET, LIMIT, BRACKET
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # PENDING, FILLED, REJECTED
    alpaca_order_id: Mapped[str | None] = mapped_column(String(50))

    # Confirmation tracking
    requires_confirmation: Mapped[bool] = mapped_column(default=False, nullable=False)
    confirmation_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_by: Mapped[str | None] = mapped_column(
        String(20), comment="DISCORD, DASHBOARD, AUTO"
    )

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return (
            f"<Execution(symbol={self.symbol}, side={self.side}, qty={self.qty}, "
            f"status={self.status})>"
        )
