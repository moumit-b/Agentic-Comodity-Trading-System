import asyncio
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import text

from src.core.config import DatabaseConfig
from src.core.database import get_session, init_db
from src.models.bars import Bar1m


async def seed_market_data():
    """Seed 1-minute bar data for testing."""
    print("Seeding market data...")

    db_config = DatabaseConfig()
    init_db(db_config)

    async with get_session() as session:
        # Create partitions for Dec 2025 and Jan 2026
        # The prompt says today is Jan 12, 2026, so we need these months.
        print("Creating partitions...")
        await session.execute(text("CREATE TABLE IF NOT EXISTS bars_1m_2025_12 PARTITION OF bars_1m FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');"))
        await session.execute(text("CREATE TABLE IF NOT EXISTS bars_1m_2026_01 PARTITION OF bars_1m FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');"))
        await session.commit()

        symbols = [("USO", 75.0), ("UNG", 25.0)]
        end_time = datetime.now(UTC)
        # Generate 30 days of data
        start_time = end_time - timedelta(days=30)

        total_bars = 0

        for symbol, start_price in symbols:
            print(f"Generating data for {symbol}...")
            current_price = start_price
            current_time = start_time

            bars_batch = []

            while current_time < end_time:
                # Skip weekends
                if current_time.weekday() >= 5:
                    current_time += timedelta(days=1)
                    current_time = current_time.replace(hour=9, minute=30)
                    continue

                # Trading hours 9:30 - 16:00 ET (approx 13:30 - 20:00 UTC)
                # We'll just generate 24h for simplicity or stick to market hours?
                # Let's stick to 24/7 for crypto-like or just standard hours for stocks.
                # To be safe and simple: just generate continuous data every minute.

                # Random walk
                change_pct = random.uniform(-0.001, 0.001) # +/- 0.1% per minute
                current_price *= (1 + change_pct)

                high = current_price * (1 + random.uniform(0, 0.0005))
                low = current_price * (1 - random.uniform(0, 0.0005))
                close = current_price
                open_p = (high + low) / 2 # Approx

                volume = int(random.uniform(1000, 50000))

                bar = Bar1m(
                    symbol=symbol,
                    timestamp=current_time,
                    open=Decimal(f"{open_p:.4f}"),
                    high=Decimal(f"{high:.4f}"),
                    low=Decimal(f"{low:.4f}"),
                    close=Decimal(f"{close:.4f}"),
                    volume=volume,
                    vwap=Decimal(f"{current_price:.4f}"),
                    trade_count=random.randint(10, 100)
                )
                bars_batch.append(bar)

                if len(bars_batch) >= 1000:
                    session.add_all(bars_batch)
                    await session.flush()
                    total_bars += len(bars_batch)
                    bars_batch = []
                    print(f"  Generated {total_bars} bars...", end='\r')

                current_time += timedelta(minutes=1)

            if bars_batch:
                session.add_all(bars_batch)
                await session.flush()
                total_bars += len(bars_batch)

        await session.commit()
        print(f"\n[SUCCESS] Seeded {total_bars} bars total.")

if __name__ == "__main__":
    asyncio.run(seed_market_data())
