"""System configuration ORM model."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ConfigOverride(Base):
    """Runtime configuration overrides (dashboard adjustments)."""

    __tablename__ = "config_overrides"
    __table_args__ = (UniqueConstraint("key", name="uq_config_overrides_key"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="NOW()"
    )
    updated_by: Mapped[str | None] = mapped_column(
        String(50), comment="User or system that made the change"
    )

    def __repr__(self) -> str:
        return f"<ConfigOverride(key={self.key}, value={self.value})>"
