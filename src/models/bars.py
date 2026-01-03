"""Bar and indicator ORM models."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Bar1m(Base):
    """1-minute OHLCV bars partitioned by month."""

    __tablename__ = "bars_1m"
    __table_args__ = (
        Index("idx_bars_1m_symbol_timestamp", "symbol", "timestamp"),
        Index("idx_bars_1m_timestamp", "timestamp"),
        UniqueConstraint("symbol", "timestamp", name="uq_bars_1m_symbol_timestamp"),
        {
            "postgresql_partition_by": "RANGE (timestamp)",
        },
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    open: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    trade_count: Mapped[int | None] = mapped_column(Integer)

    def __repr__(self) -> str:
        return f"<Bar1m(symbol={self.symbol}, timestamp={self.timestamp}, close={self.close})>"


class BarAggregated(Base):
    """Aggregated bars for 5m, 15m, 1h, 1d timeframes."""

    __tablename__ = "bars_aggregated"
    __table_args__ = (
        Index("idx_bars_agg_symbol_tf_ts", "symbol", "timeframe", "timestamp"),
        UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_bars_agg_symbol_tf_ts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(5), nullable=False)  # '5m', '15m', '1h', '1d'
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    def __repr__(self) -> str:
        return (
            f"<BarAggregated(symbol={self.symbol}, timeframe={self.timeframe}, "
            f"timestamp={self.timestamp}, close={self.close})>"
        )


class Indicator(Base):
    """Technical indicators for multi-timeframe analysis."""

    __tablename__ = "indicators"
    __table_args__ = (
        Index("idx_indicators_symbol_tf_ts", "symbol", "timeframe", "timestamp"),
        UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_indicators_symbol_tf_ts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(5), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Trend indicators
    sma_20: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    ema_20: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    rsi: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    atr: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    # MACD
    macd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    macd_signal: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    macd_histogram: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    # Bollinger Bands
    bb_upper: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    bb_middle: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    bb_lower: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    def __repr__(self) -> str:
        return (
            f"<Indicator(symbol={self.symbol}, timeframe={self.timeframe}, "
            f"timestamp={self.timestamp})>"
        )
