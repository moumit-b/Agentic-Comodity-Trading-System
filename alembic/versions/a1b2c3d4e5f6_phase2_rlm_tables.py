"""phase2_rlm_tables

Revision ID: a1b2c3d4e5f6
Revises: 76b9c07cfd6d
Create Date: 2026-01-27 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "76b9c07cfd6d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Phase 2 Recursive Learning Model tables."""

    # ===== 1. Extend existing Signals Table =====
    # Add execution tracking columns to existing signals table
    op.add_column("signals", sa.Column("executed", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("signals", sa.Column("execution_id", sa.BigInteger(), nullable=True))

    # Add foreign key to executions
    op.create_foreign_key(
        "fk_signals_execution_id",
        "signals",
        "executions",
        ["execution_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add indices for Phase 2 queries
    op.create_index("idx_signals_symbol_timestamp", "signals", ["symbol", "timestamp"])
    op.create_index("idx_signals_strategy_timestamp", "signals", ["strategy_name", "timestamp"])
    op.create_index("idx_signals_executed", "signals", ["executed"])

    # ===== 2. Learning Logs Table (RLM predictions and reflections) =====
    op.create_table(
        "learning_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("signal_id", sa.BigInteger(), nullable=True),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("strategy_name", sa.String(length=100), nullable=False),
        # Prediction
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("predicted_outcome", sa.Text(), nullable=False),
        sa.Column("predicted_target", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("prediction_horizon_mins", sa.Integer(), nullable=False),
        sa.Column("entry_price", sa.Numeric(precision=10, scale=2), nullable=False),
        # Observation
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("actual_outcome", sa.Text(), nullable=True),
        sa.Column("prediction_correct", sa.Boolean(), nullable=True),
        # Reflection
        sa.Column("reflected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reflection_prompt", sa.Text(), nullable=True),
        sa.Column("reflection_response", sa.Text(), nullable=True),
        sa.Column("suggested_adjustment", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("adjustment_applied", sa.Boolean(), nullable=False, server_default="false"),
        # Context
        sa.Column("market_regime", sa.String(length=20), nullable=True),
        sa.Column("rsi_at_signal", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("atr_at_signal", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("sentiment_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("context_tag", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.id"],
            name="fk_learning_logs_signal_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("idx_learning_logs_predicted_at", "learning_logs", ["predicted_at"])
    op.create_index("idx_learning_logs_observed_at", "learning_logs", ["observed_at"])
    op.create_index("idx_learning_logs_strategy", "learning_logs", ["strategy_name"])
    op.create_index("idx_learning_logs_symbol", "learning_logs", ["symbol"])
    op.create_index(
        "idx_learning_logs_pending_observation",
        "learning_logs",
        ["predicted_at", "prediction_horizon_mins"],
        postgresql_where=sa.text("observed_at IS NULL"),
    )

    # ===== 3. Strategy Overrides Table (RLM dynamic adjustments) =====
    op.create_table(
        "strategy_overrides",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("strategy_name", sa.String(length=100), nullable=False),
        sa.Column("parameter_name", sa.String(length=100), nullable=False),
        sa.Column("original_value", sa.String(length=100), nullable=True),
        sa.Column("override_value", sa.String(length=100), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("learning_log_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "strategy_name",
            "parameter_name",
            name="uq_strategy_overrides_strategy_parameter",
        ),
        sa.ForeignKeyConstraint(
            ["learning_log_id"],
            ["learning_logs.id"],
            name="fk_strategy_overrides_learning_log_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("idx_strategy_overrides_expires_at", "strategy_overrides", ["expires_at"])
    op.create_index(
        "idx_strategy_overrides_active",
        "strategy_overrides",
        ["strategy_name", "parameter_name", "expires_at"],
        postgresql_where=sa.text("reverted_at IS NULL"),
    )

    # ===== 4. Context Analysis Table (Cache LLM context analysis) =====
    op.create_table(
        "context_analysis",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sentiment_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("regime_tag", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("news_headlines", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("eia_events", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("market_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("llm_prompt", sa.Text(), nullable=True),
        sa.Column("llm_response", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_context_analysis_symbol_analyzed_at", "context_analysis", ["symbol", "analyzed_at"])
    # Note: Removed expires_at > NOW() from WHERE clause as NOW() is not immutable in PostgreSQL
    # Application will filter by expires_at programmatically
    op.create_index(
        "idx_context_analysis_active",
        "context_analysis",
        ["symbol", "expires_at"],
    )


def downgrade() -> None:
    """Drop Phase 2 tables and revert signals table changes."""
    # Drop new tables
    op.drop_table("context_analysis")
    op.drop_table("strategy_overrides")
    op.drop_table("learning_logs")

    # Revert signals table changes
    op.drop_index("idx_signals_executed", table_name="signals")
    op.drop_index("idx_signals_strategy_timestamp", table_name="signals")
    op.drop_index("idx_signals_symbol_timestamp", table_name="signals")
    op.drop_constraint("fk_signals_execution_id", "signals", type_="foreignkey")
    op.drop_column("signals", "execution_id")
    op.drop_column("signals", "executed")
