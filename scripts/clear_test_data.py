"""Clear test/seeded data from the database."""

import asyncio

from sqlalchemy import delete

from src.core.config import DatabaseConfig
from src.core.database import get_session, init_db
from src.models.account import AccountSnapshot, DailyLimit
from src.models.bars import Bar1m, BarAggregated, Indicator
from src.models.execution import Decision, Execution
from src.models.position import Position
from src.models.risk import CircuitBreaker
from src.models.settlement import Settlement
from src.models.signal import Signal


async def clear_all_data():
    """Clear all data from the database tables."""
    print("Clearing all test/seeded data from database...")

    async with get_session() as session:
        # Delete in order to respect foreign key constraints
        tables_to_clear = [
            ("Circuit Breakers", CircuitBreaker),
            ("Account Snapshots", AccountSnapshot),
            ("Daily Limits", DailyLimit),
            ("Settlements", Settlement),
            ("Executions", Execution),
            ("Decisions", Decision),
            ("Signals", Signal),
            ("Positions", Position),
            ("Indicators", Indicator),
            ("Aggregated Bars", BarAggregated),
            ("1-Minute Bars", Bar1m),
        ]

        for table_name, model in tables_to_clear:
            result = await session.execute(delete(model))
            count = result.rowcount
            print(f"  - Deleted {count} records from {table_name}")

        await session.commit()

    print("\nDatabase cleared successfully!")
    print("The dashboard will now show only real data from Alpaca and live trading.")


if __name__ == "__main__":
    # Initialize database
    config = DatabaseConfig()
    init_db(config)

    # Run the cleanup
    asyncio.run(clear_all_data())
