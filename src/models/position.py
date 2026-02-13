"""Position ORM model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Position(Base):
    """Active and historical positions."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # LONG, SHORT
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    entry_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    trailing_stop_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    highest_price_since_entry: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    exit_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    exit_reason: Mapped[str | None] = mapped_column(String(50))
    is_open: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Risk tracking
    risk_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), comment="Dollar amount at risk"
    )
    risk_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), comment="Percentage of portfolio at risk"
    )

    # Strategy info
    strategy_name: Mapped[str | None] = mapped_column(String(50))
    timeframe: Mapped[str | None] = mapped_column(String(5))

    def __repr__(self) -> str:
        status = "OPEN" if self.is_open else "CLOSED"
        return (
            f"<Position({status}, symbol={self.symbol}, side={self.side}, "
            f"qty={self.qty}, entry={self.entry_price})>"
        )
