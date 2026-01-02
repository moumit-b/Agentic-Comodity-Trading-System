"""initial_schema

Revision ID: 76b9c07cfd6d
Revises:
Create Date: 2025-12-31 01:50:22.021110

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "76b9c07cfd6d"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all trading system tables."""

    # ===== 1. Bars (1-minute, partitioned by month) =====
    # NOTE: Partitioned tables require partition key in primary key
    op.create_table(
        "bars_1m",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("high", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("low", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("close", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("vwap", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("trade_count", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id", "timestamp"),  # Include partition key
        sa.UniqueConstraint("symbol", "timestamp", name="uq_bars_1m_symbol_timestamp"),
        postgresql_partition_by="RANGE (timestamp)",
    )
    op.create_index("idx_bars_1m_symbol_timestamp", "bars_1m", ["symbol", "timestamp"])
    op.create_index("idx_bars_1m_timestamp", "bars_1m", ["timestamp"])

    # ===== 2. Aggregated Bars (5m, 15m, 1h, 1d) =====
    op.create_table(
        "bars_aggregated",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("timeframe", sa.String(length=5), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("high", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("low", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("close", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("vwap", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_bars_agg_symbol_tf_ts"),
    )
    op.create_index(
        "idx_bars_agg_symbol_tf_ts", "bars_aggregated", ["symbol", "timeframe", "timestamp"]
    )

    # ===== 3. Indicators =====
    op.create_table(
        "indicators",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("timeframe", sa.String(length=5), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sma_20", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("ema_20", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("rsi", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("atr", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("macd", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("macd_signal", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("macd_histogram", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("bb_upper", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("bb_middle", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("bb_lower", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_indicators_symbol_tf_ts"),
    )
    op.create_index(
        "idx_indicators_symbol_tf_ts", "indicators", ["symbol", "timeframe", "timestamp"]
    )

    # ===== 4. Account Snapshots =====
    op.create_table(
        "account_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column("total_cash", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("settled_cash", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("buying_power", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("total_equity", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("portfolio_value", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ===== 5. Daily Limits =====
    op.create_table(
        "daily_limits",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("starting_equity", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column(
            "current_pnl", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0.0"
        ),
        sa.Column("trades_executed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consecutive_losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("profit_target_hit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("loss_limit_hit", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", name="uq_daily_limits_date"),
    )

    # ===== 6. Settlements (T+1 Tracking) =====
    op.create_table(
        "settlements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_id", sa.String(length=50), nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("settlement_date", sa.Date(), nullable=False),
        sa.Column("cash_amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("is_settled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_id", name="uq_settlements_trade_id"),
    )

    # ===== 7. Positions =====
    op.create_table(
        "positions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("qty", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("entry_price", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column(
            "entry_time",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("stop_loss", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("take_profit", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("trailing_stop_pct", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("highest_price_since_entry", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("exit_price", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("exit_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("exit_reason", sa.String(length=50), nullable=True),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("risk_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("risk_pct", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("strategy_name", sa.String(length=50), nullable=True),
        sa.Column("timeframe", sa.String(length=5), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ===== 8. Signals =====
    op.create_table(
        "signals",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("strategy_name", sa.String(length=50), nullable=False),
        sa.Column("timeframe", sa.String(length=5), nullable=False),
        sa.Column("signal_strength", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("suggested_entry", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("suggested_stop", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("suggested_target", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("market_regime", sa.String(length=20), nullable=True),
        sa.Column("horizon", sa.String(length=10), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ===== 9. Decisions =====
    op.create_table(
        "decisions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("signal_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("position_size", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("risk_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("risk_pct", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("portfolio_heat_after", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("passed_portfolio_heat", sa.Boolean(), nullable=True),
        sa.Column("passed_daily_limits", sa.Boolean(), nullable=True),
        sa.Column("passed_settlement_check", sa.Boolean(), nullable=True),
        sa.Column("passed_time_check", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ===== 10. Executions =====
    op.create_table(
        "executions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("decision_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("qty", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("filled_price", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("order_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("alpaca_order_id", sa.String(length=50), nullable=True),
        sa.Column("requires_confirmation", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("confirmation_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.String(length=20), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ===== 11. Circuit Breakers =====
    op.create_table(
        "circuit_breakers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column("breaker_type", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ===== 12. Config Overrides =====
    op.create_table(
        "config_overrides",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_by", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_config_overrides_key"),
    )


def downgrade() -> None:
    """Drop all trading system tables."""
    op.drop_table("config_overrides")
    op.drop_table("circuit_breakers")
    op.drop_table("executions")
    op.drop_table("decisions")
    op.drop_table("signals")
    op.drop_table("positions")
    op.drop_table("settlements")
    op.drop_table("daily_limits")
    op.drop_table("account_snapshots")
    op.drop_table("indicators")
    op.drop_table("bars_aggregated")
    op.drop_table("bars_1m")
