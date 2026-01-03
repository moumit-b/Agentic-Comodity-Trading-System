#!/usr/bin/env python3
"""
Seed sample data for dashboard testing.
Creates fake signals, decisions, executions, and positions.
"""

import asyncio
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from src.core.config import DatabaseConfig
from src.core.database import get_session, init_db, shutdown_db
from src.models.account import DailyLimit
from src.models.execution import Decision, Execution
from src.models.position import Position
from src.models.signal import Signal


async def seed_sample_data():
    """Create sample data for dashboard testing."""
    print("Seeding sample data for dashboard testing...")

    # Initialize database connection
    print("Initializing database connection...")
    db_config = DatabaseConfig()
    init_db(db_config)

    async with get_session() as session:
        # Clean up existing test data
        print("Cleaning up existing data...")
        from sqlalchemy import delete

        await session.execute(delete(Position))
        await session.execute(delete(Execution))
        await session.execute(delete(Decision))
        await session.execute(delete(Signal))
        await session.execute(delete(DailyLimit))
        await session.commit()

        # Skip bars_1m (partitioned table - would need partitions created)
        print("Skipping 1m bars (partitioned table)...")
        now = datetime.now(UTC)
        symbols = ["USO", "UNG"]

        # Create sample signals
        print("Creating sample signals...")
        strategies = [
            "EMA Crossover",
            "MACD Trend",
            "Bollinger Bands Mean Reversion",
            "RSI Oversold/Overbought",
        ]
        signals = []

        for i in range(20):
            timestamp = now - timedelta(hours=20 - i)
            symbol = random.choice(symbols)
            direction = random.choice(["LONG", "SHORT"])
            strategy = random.choice(strategies)
            base_price = 75.0 if symbol == "USO" else 25.0

            signal = Signal(
                symbol=symbol,
                direction=direction,
                strategy_name=strategy,
                timeframe="1H",
                timestamp=timestamp,
                confidence=Decimal(str(random.uniform(0.6, 0.95))),
                signal_strength=Decimal(str(random.uniform(50, 100))),
                suggested_entry=Decimal(str(base_price)),
                suggested_stop=Decimal(str(base_price * (0.98 if direction == "LONG" else 1.02))),
                suggested_target=Decimal(str(base_price * (1.03 if direction == "LONG" else 0.97))),
                market_regime=random.choice(["TRENDING", "RANGING", "VOLATILE"]),
                horizon=random.choice(["INTRADAY", "SWING"]),
                reasoning=f"{strategy} detected {direction} opportunity based on technical indicators",
            )
            signals.append(signal)

        session.add_all(signals)
        await session.flush()

        # Create sample decisions
        print("Creating sample decisions...")
        decisions = []

        for signal in signals:
            approved = random.random() > 0.3  # 70% approval rate

            decision = Decision(
                signal_id=signal.id,
                timestamp=signal.timestamp + timedelta(seconds=5),
                decision="APPROVE" if approved else "REJECT",
                reason=None
                if approved
                else random.choice(
                    [
                        "Insufficient buying power",
                        "Max positions reached",
                        "Portfolio heat exceeded",
                        "Daily loss limit reached",
                        "Volatility spike detected",
                        "Low confidence score",
                    ]
                ),
                position_size=Decimal(str(random.randint(10, 100))) if approved else None,
                risk_amount=Decimal(str(random.uniform(50, 200))) if approved else None,
                risk_pct=Decimal(str(random.uniform(0.005, 0.02))) if approved else None,
                portfolio_heat_after=Decimal(str(random.uniform(0.1, 0.6))) if approved else None,
                passed_portfolio_heat=approved,
                passed_daily_limits=approved,
                passed_settlement_check=approved,
                passed_time_check=True,
            )
            decisions.append(decision)

        session.add_all(decisions)
        await session.flush()

        # Create sample executions
        print("Creating sample executions...")
        executions = []
        approved_decisions = [d for d in decisions if d.decision == "APPROVE"]

        for decision in approved_decisions[:10]:  # Only first 10 approved
            # Get the signal to know the symbol
            signal = next(s for s in signals if s.id == decision.signal_id)
            status = random.choice(["FILLED", "FILLED", "FILLED", "PENDING", "REJECTED"])

            execution = Execution(
                decision_id=decision.id,
                timestamp=decision.timestamp + timedelta(seconds=10),
                symbol=signal.symbol,
                side=signal.direction,
                qty=decision.position_size,
                order_type="LIMIT",
                status=status,
                filled_price=Decimal(str(float(signal.suggested_entry) + random.uniform(-2, 2)))
                if status == "FILLED"
                else None,
                alpaca_order_id=f"ORDER-{random.randint(1000, 9999)}"
                if status != "PENDING"
                else None,
                requires_confirmation=False,
            )
            executions.append(execution)

        session.add_all(executions)

        # Create sample open positions
        print("Creating sample open positions...")
        positions = []
        filled_executions = [e for e in executions if e.status == "FILLED"]

        for execution in filled_executions[:5]:  # Only keep 5 open
            # Get the signal to know strategy info
            decision = next(d for d in decisions if d.id == execution.decision_id)
            signal = next(s for s in signals if s.id == decision.signal_id)

            entry_price = float(execution.filled_price)

            position = Position(
                symbol=execution.symbol,
                side=execution.side,
                qty=execution.qty,
                entry_price=Decimal(str(entry_price)),
                entry_time=execution.timestamp,
                stop_loss=signal.suggested_stop,
                take_profit=signal.suggested_target,
                highest_price_since_entry=Decimal(str(entry_price * random.uniform(1.0, 1.02))),
                is_open=True,
                risk_amount=decision.risk_amount,
                risk_pct=decision.risk_pct,
                strategy_name=signal.strategy_name,
                timeframe=signal.timeframe,
            )
            positions.append(position)

        session.add_all(positions)

        # Create daily limit record
        print("Creating daily limit record...")
        daily_limit = DailyLimit(
            trade_date=datetime.now(UTC).date(),
            starting_equity=Decimal("10000.00"),
            current_pnl=Decimal(str(random.uniform(-100, 200))),
            trades_executed=len(executions),
            consecutive_losses=random.randint(0, 2),
            profit_target_hit=False,
            loss_limit_hit=False,
        )
        session.add(daily_limit)

        await session.commit()

    print("\n[SUCCESS] Sample data seeded successfully!")
    print(f"  - {len(signals)} signals from 4 strategies")
    print(
        f"  - {len(decisions)} decisions ({sum(1 for d in decisions if d.decision == 'APPROVE')} approved)"
    )
    print(
        f"  - {len(executions)} executions ({sum(1 for e in executions if e.status == 'FILLED')} filled)"
    )
    print(f"  - {len(positions)} open positions")
    print("  - 1 daily limit record")
    print("\n[READY] Dashboard is ready to view!")
    print("  Run: uv run streamlit run dashboard/app.py")
    print("  URL: http://localhost:8501")

    # Close database connection
    await shutdown_db()


if __name__ == "__main__":
    asyncio.run(seed_sample_data())
