"""Account and daily limit ORM models."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class AccountSnapshot(Base):
    """Account balance snapshots over time."""

    __tablename__ = "account_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    total_cash: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    settled_cash: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    buying_power: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_equity: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    portfolio_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    def __repr__(self) -> str:
        return f"<AccountSnapshot(timestamp={self.timestamp}, equity={self.total_equity})>"


class DailyLimit(Base):
    """Daily trading limits and counters."""

    __tablename__ = "daily_limits"
    __table_args__ = (UniqueConstraint("trade_date", name="uq_daily_limits_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    starting_equity: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    current_pnl: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.0")
    )
    trades_executed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consecutive_losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    profit_target_hit: Mapped[bool] = mapped_column(default=False, nullable=False)
    loss_limit_hit: Mapped[bool] = mapped_column(default=False, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<DailyLimit(date={self.trade_date}, pnl={self.current_pnl}, "
            f"trades={self.trades_executed})>"
        )
