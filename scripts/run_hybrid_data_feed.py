"""
Hybrid Data Feed Coordinator - Professional-Grade Real-Time Data Pipeline.

Architecture:
- Primary: Finnhub WebSocket (real-time, 0-second delay)
- Backup: Alpaca WebSocket (15-min delayed IEX, fallback)
- Historical: Alpaca REST API (14 days for deep indicators)

Features:
- Automatic failover (Finnhub → Alpaca)
- Health monitoring and reconnection
- Rate limiting and error handling
- Database persistence + Redis caching
"""

import asyncio
import logging
import os
import sys
from datetime import UTC, datetime, timedelta

# Install uvloop for performance
try:
    import uvloop

    uvloop.install()
except ImportError:
    pass

# Add current directory to path
sys.path.append(os.getcwd())

from src.agents.finnhub_data import FinnhubDataAgent
from src.agents.market_data import MarketDataAgent
from src.core.config import AlpacaConfig, DatabaseConfig, FinnhubConfig, RedisConfig
from src.core.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("hybrid_data_feed.log")],
)
logger = logging.getLogger(__name__)


class HybridDataCoordinator:
    """
    Coordinates Finnhub (primary) and Alpaca (backup) data feeds.

    Responsibilities:
    - Bootstrap historical data (14 days from Alpaca)
    - Stream real-time data (Finnhub primary, Alpaca fallback)
    - Monitor health and implement automatic failover
    - Persist all data to PostgreSQL + Redis
    """

    def __init__(
        self,
        alpaca_config: AlpacaConfig,
        finnhub_config: FinnhubConfig,
        redis_config: RedisConfig,
        symbols: list[str],
    ):
        """
        Initialize Hybrid Data Coordinator.

        Args:
            alpaca_config: Alpaca API configuration
            finnhub_config: Finnhub API configuration
            redis_config: Redis cache configuration
            symbols: List of symbols to track (e.g., ["USO", "UNG"])
        """
        self.alpaca_config = alpaca_config
        self.finnhub_config = finnhub_config
        self.symbols = symbols

        # Initialize MarketDataAgent (unified processor)
        self.market_data_agent = MarketDataAgent(alpaca_config, redis_config)

        # Initialize Finnhub agent
        self.finnhub_agent: FinnhubDataAgent | None = None

        # Health monitoring
        self._running = False
        self._using_finnhub = False
        self._using_alpaca_fallback = False
        self._last_finnhub_bar: dict[str, datetime] = {}
        self._last_alpaca_bar: dict[str, datetime] = {}

    async def start(self) -> None:
        """
        Start the hybrid data feed.

        Steps:
        1. Connect to MarketDataAgent (Alpaca REST + WebSocket)
        2. Bootstrap 14 days of historical data
        3. Connect to Finnhub WebSocket
        4. Subscribe to real-time feeds
        5. Start health monitoring
        """
        logger.info("=" * 80)
        logger.info("HYBRID DATA FEED - Starting Professional-Grade Pipeline")
        logger.info("=" * 80)

        self._running = True

        try:
            # Step 1: Connect MarketDataAgent
            logger.info("Step 1/5: Connecting to MarketDataAgent (Alpaca)...")
            await self.market_data_agent.connect()

            # Step 2: Bootstrap historical data (14 days)
            logger.info("Step 2/5: Bootstrapping 14 days of historical data...")
            await self._bootstrap_historical_data()

            # Step 3: Initialize Finnhub agent
            if (
                self.finnhub_config.use_as_primary
                and self.finnhub_config.api_key.get_secret_value()
            ):
                logger.info(
                    "Step 3/5: Connecting to Finnhub WebSocket (Primary Real-Time Source)..."
                )
                await self._start_finnhub()
            else:
                logger.warning("Finnhub disabled or no API key - using Alpaca only")

            # Step 4: Subscribe to Alpaca WebSocket (fallback)
            logger.info("Step 4/5: Subscribing to Alpaca WebSocket (Fallback)...")
            await self.market_data_agent.subscribe(self.symbols)

            # Step 5: Start health monitoring
            logger.info("Step 5/5: Starting health monitoring...")
            asyncio.create_task(self._health_monitor())

            logger.info("=" * 80)
            logger.info("HYBRID DATA FEED ACTIVE")
            logger.info(f"Primary Source: {'Finnhub' if self._using_finnhub else 'Alpaca'}")
            logger.info(f"Symbols: {self.symbols}")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Failed to start hybrid data feed: {e}", exc_info=True)
            await self.stop()
            raise

    async def _bootstrap_historical_data(self) -> None:
        """
        Bootstrap 14 days of historical data from Alpaca.

        This provides deep history for:
        - 1h indicators (200-period SMA requires 8.3 days)
        - 4h indicators (50-period requires 8.3 days)
        - Daily analysis (14 bars for short-term trends)
        """
        end = datetime.now(UTC) - timedelta(minutes=20)  # IEX delay
        start = end - timedelta(days=14)

        logger.info(f"Fetching 14 days of history: {start.date()} to {end.date()}")

        for symbol in self.symbols:
            try:
                logger.info(f"Fetching historical data for {symbol}...")

                # Fetch with pagination
                df = await self.market_data_agent.fetch_historical_bars(symbol, start, end)

                if df.empty:
                    logger.warning(f"No historical data for {symbol}")
                    continue

                logger.info(f"Received {len(df)} bars for {symbol}. Processing...")

                # Populate internal buffer
                df_reset = df.reset_index()
                self.market_data_agent._bars_1m[symbol] = df_reset

                # Trigger aggregation (calculates indicators, saves to DB)
                await self.market_data_agent._aggregate_timeframes(symbol)

                logger.info(f"✓ Historical data bootstrapped for {symbol}")

            except Exception as e:
                logger.error(f"Failed to bootstrap {symbol}: {e}", exc_info=True)

        logger.info("Historical data bootstrap complete")

    async def _start_finnhub(self) -> None:
        """Start Finnhub WebSocket connection."""
        try:
            # Create Finnhub agent with callback to MarketDataAgent
            async def on_finnhub_bar(symbol: str, bar_data: dict):
                """Callback when Finnhub completes a 1m bar."""
                self._last_finnhub_bar[symbol] = datetime.now(UTC)
                await self.market_data_agent.process_bar(symbol, bar_data, source="finnhub")

            self.finnhub_agent = FinnhubDataAgent(self.finnhub_config, on_finnhub_bar)

            # Connect
            await self.finnhub_agent.connect()

            # Subscribe to symbols
            await self.finnhub_agent.subscribe(self.symbols)

            # Start WebSocket loop in background
            asyncio.create_task(self._run_finnhub_loop())

            self._using_finnhub = True
            logger.info("✓ Finnhub WebSocket active (real-time data)")

        except Exception as e:
            logger.error(f"Failed to start Finnhub: {e}", exc_info=True)
            logger.warning("Falling back to Alpaca WebSocket only")
            self._using_finnhub = False

    async def _run_finnhub_loop(self) -> None:
        """Run Finnhub WebSocket message loop with auto-reconnect."""
        while self._running:
            try:
                if self.finnhub_agent:
                    await self.finnhub_agent.run()
            except Exception as e:
                logger.error(f"Finnhub WebSocket error: {e}", exc_info=True)

                if self._running:
                    logger.info("Reconnecting Finnhub in 5s...")
                    await asyncio.sleep(5)
                    try:
                        await self.finnhub_agent.connect()
                        await self.finnhub_agent.subscribe(self.symbols)
                    except Exception as reconnect_error:
                        logger.error(f"Finnhub reconnection failed: {reconnect_error}")
                        self._using_finnhub = False
                        break

    async def _health_monitor(self) -> None:
        """
        Monitor data feed health and implement failover logic.

        Checks:
        - Finnhub last bar timestamp (should update every 1-2 minutes)
        - Alpaca fallback availability
        - WebSocket connection status
        """
        logger.info("Health monitor started (checks every 60s)")

        while self._running:
            await asyncio.sleep(60)  # Check every minute

            try:
                now = datetime.now(UTC)

                # Check Finnhub health
                if self._using_finnhub and self.finnhub_agent:
                    health = self.finnhub_agent.get_health_status()

                    if not health["connected"]:
                        logger.warning("Finnhub WebSocket disconnected - attempting reconnect")
                        self._using_finnhub = False

                    # Check for stale data (no bars in 5 minutes)
                    for symbol in self.symbols:
                        last_bar = self._last_finnhub_bar.get(symbol)
                        if last_bar and (now - last_bar).total_seconds() > 300:
                            logger.warning(
                                f"Finnhub stale data for {symbol} "
                                f"(last bar: {(now - last_bar).total_seconds():.0f}s ago)"
                            )

                # Check Alpaca fallback
                for symbol in self.symbols:
                    last_alpaca = self._last_alpaca_bar.get(symbol)
                    if last_alpaca:
                        age = (now - last_alpaca).total_seconds()
                        if age > 600:  # 10 minutes
                            logger.warning(f"Alpaca fallback stale for {symbol} ({age:.0f}s)")

                # Report status
                primary_source = (
                    "Finnhub (real-time)" if self._using_finnhub else "Alpaca (15m delay)"
                )
                logger.info(f"Health Check: Active source = {primary_source}")

            except Exception as e:
                logger.error(f"Health monitor error: {e}", exc_info=True)

    async def stop(self) -> None:
        """Stop all data feeds gracefully."""
        logger.info("Stopping Hybrid Data Feed...")

        self._running = False

        # Disconnect Finnhub
        if self.finnhub_agent:
            try:
                await self.finnhub_agent.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting Finnhub: {e}")

        # Disconnect MarketDataAgent (Alpaca)
        try:
            await self.market_data_agent.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting MarketDataAgent: {e}")

        logger.info("Hybrid Data Feed stopped")


async def main():
    """Main entry point for hybrid data feed."""
    # Load configurations
    alpaca_config = AlpacaConfig()
    finnhub_config = FinnhubConfig()
    redis_config = RedisConfig()
    db_config = DatabaseConfig()

    # Initialize database
    init_db(db_config)

    # Define symbols
    symbols = ["USO", "UNG"]

    # Create coordinator
    coordinator = HybridDataCoordinator(
        alpaca_config=alpaca_config,
        finnhub_config=finnhub_config,
        redis_config=redis_config,
        symbols=symbols,
    )

    try:
        # Start hybrid feed
        await coordinator.start()

        # Keep running
        logger.info("Press Ctrl+C to stop...")
        while True:
            await asyncio.sleep(60)

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await coordinator.stop()


if __name__ == "__main__":
    asyncio.run(main())
