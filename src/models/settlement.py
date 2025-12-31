"""Settlement tracking ORM model for T+1 compliance."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Settlement(Base):
    """T+1 settlement tracking for cash account compliance."""

    __tablename__ = "settlements"
    __table_args__ = (UniqueConstraint("trade_id", name="uq_settlements_trade_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    settlement_date: Mapped[date] = mapped_column(Date, nullable=False)
    cash_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, comment="Cash tied up in trade"
    )
    is_settled: Mapped[bool] = mapped_column(default=False, nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        status = "SETTLED" if self.is_settled else "PENDING"
        return (
            f"<Settlement({status}, trade_id={self.trade_id}, "
            f"settlement_date={self.settlement_date})>"
        )
