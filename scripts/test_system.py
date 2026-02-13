"""Comprehensive system testing script for data feed and signal generation."""

import asyncio
import logging
import sys
from datetime import UTC, datetime, timedelta

sys.path.append(".")

from sqlalchemy import text

from src.agents.market_data import MarketDataAgent
from src.core.config import AlpacaConfig, DatabaseConfig, RedisConfig
from src.core.database import get_session, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_data():
    """Check existing data in database."""
    logger.info("=" * 80)
    logger.info("TEST 1: Database Data Check")
    logger.info("=" * 80)

    async with get_session() as session:
        # Check bars_1m
        result = await session.execute(
            text(
                """
            SELECT symbol, COUNT(*) as count,
                   MIN(timestamp) as earliest,
                   MAX(timestamp) as latest
            FROM bars_1m
            GROUP BY symbol
        """
            )
        )
        rows = result.fetchall()

        if not rows:
            logger.warning("No data in bars_1m table")
        else:
            for row in rows:
                logger.info(
                    f"{row.symbol}: {row.count} bars, "
                    f"Range: {row.earliest} to {row.latest}"
                )

        # Check indicators
        result = await session.execute(
            text(
                """
            SELECT symbol, timeframe, COUNT(*) as count,
                   MAX(timestamp) as latest
            FROM indicators
            GROUP BY symbol, timeframe
            ORDER BY symbol, timeframe
        """
            )
        )
        rows = result.fetchall()

        if not rows:
            logger.warning("No indicators calculated")
        else:
            logger.info("\nIndicators:")
            for row in rows:
                logger.info(f"  {row.symbol} {row.timeframe}: {row.count} records, latest: {row.latest}")


async def test_historical_fetch():
    """Test 14-day historical data fetch."""
    logger.info("=" * 80)
    logger.info("TEST 2: Historical Data Fetch (14 days)")
    logger.info("=" * 80)

    alpaca_config = AlpacaConfig()
    redis_config = RedisConfig()

    agent = MarketDataAgent(alpaca_config, redis_config)

    # Mock Redis (avoid connection issues)
    class MockRedis:
        def connect(self):
            pass

        def disconnect(self):
            pass

        def cache_bars_1m(self, *args):
            pass

        def cache_bars_aggregated(self, *args):
            pass

        def cache_indicators(self, *args):
            pass

        def cache_regime(self, *args):
            pass

    agent.redis_cache = MockRedis()

    await agent.connect()

    # Fetch 14 days for USO (test symbol)
    end = datetime.now(UTC) - timedelta(minutes=20)
    start = end - timedelta(days=14)

    logger.info(f"Fetching USO data: {start.date()} to {end.date()}")

    df = await agent.fetch_historical_bars("USO", start, end)

    logger.info(f"Fetched {len(df)} bars for USO")
    logger.info(f"Date range: {df.index.min()} to {df.index.max()}")
    logger.info(f"Columns: {df.columns.tolist()}")
    logger.info(f"Sample data:\n{df.head()}")

    await agent.disconnect()

    return df


async def test_indicator_calculation():
    """Test indicator calculation with deep history."""
    logger.info("=" * 80)
    logger.info("TEST 3: Indicator Calculation")
    logger.info("=" * 80)

    async with get_session() as session:
        # Get latest indicators for USO
        result = await session.execute(
            text(
                """
            SELECT timeframe, timestamp, rsi, sma_20, ema_20, macd, atr
            FROM indicators
            WHERE symbol = 'USO' AND timestamp >= NOW() - INTERVAL '1 day'
            ORDER BY timeframe, timestamp DESC
            LIMIT 20
        """
            )
        )
        rows = result.fetchall()

        if not rows:
            logger.warning("No recent indicators found")
        else:
            logger.info("Recent indicators for USO:")
            for row in rows:
                logger.info(
                    f"  {row.timeframe} @ {row.timestamp}: "
                    f"RSI={row.rsi:.2f if row.rsi else 'N/A'}, "
                    f"SMA20={row.sma_20:.2f if row.sma_20 else 'N/A'}, "
                    f"MACD={row.macd:.2f if row.macd else 'N/A'}"
                )


async def test_signal_generation():
    """Test signal generation logic."""
    logger.info("=" * 80)
    logger.info("TEST 4: Signal Generation")
    logger.info("=" * 80)

    async with get_session() as session:
        # Check for recent RSI oversold/overbought conditions
        result = await session.execute(
            text(
                """
            SELECT symbol, timeframe, timestamp, rsi, close
            FROM indicators i
            JOIN bars_1m b ON i.symbol = b.symbol
                AND DATE_TRUNC('minute', i.timestamp) = DATE_TRUNC('minute', b.timestamp)
            WHERE i.rsi IS NOT NULL
              AND i.timestamp >= NOW() - INTERVAL '1 hour'
              AND (i.rsi < 30 OR i.rsi > 70)
            ORDER BY i.timestamp DESC
            LIMIT 10
        """
            )
        )
        rows = result.fetchall()

        if not rows:
            logger.info("No RSI signals in the past hour (no oversold/overbought)")
        else:
            logger.info("RSI Signals detected:")
            for row in rows:
                signal_type = "OVERSOLD (BUY)" if row.rsi < 30 else "OVERBOUGHT (SELL)"
                logger.info(
                    f"  {row.symbol} {row.timeframe} @ {row.timestamp}: "
                    f"RSI={row.rsi:.2f} → {signal_type}"
                )


async def main():
    """Run all tests."""
    logger.info("Starting comprehensive system tests...")

    # Initialize database
    db_config = DatabaseConfig()
    init_db(db_config)

    try:
        # Test 1: Database data check
        await test_database_data()

        # Test 2: Historical fetch (14 days)
        df = await test_historical_fetch()

        # Test 3: Indicator calculation
        await test_indicator_calculation()

        # Test 4: Signal generation
        await test_signal_generation()

        logger.info("=" * 80)
        logger.info("ALL TESTS COMPLETE")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
