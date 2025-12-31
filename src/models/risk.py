"""Circuit breaker ORM model."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class CircuitBreaker(Base):
    """Circuit breaker trigger log."""

    __tablename__ = "circuit_breakers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="NOW()"
    )
    breaker_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="DAILY_LOSS, DAILY_PROFIT, CONSECUTIVE_LOSSES, PORTFOLIO_HEAT, etc.",
    )
    reason: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        status = "ACTIVE" if self.is_active else "CLEARED"
        return f"<CircuitBreaker({status}, type={self.breaker_type}, time={self.timestamp})>"
