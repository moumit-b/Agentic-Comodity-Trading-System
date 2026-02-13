"""Unified continuous trading loop with Phase 2 agentic orchestration.

Runs:
1. Trading cycle every ~60 seconds
2. Background RLM tasks (observation, reflection, news refresh)
"""

import asyncio
import logging
import os
import sys
import time

# Install uvloop for 10-30% faster asyncio performance
try:
    import uvloop
    uvloop.install()
except ImportError:
    pass  # Fall back to default asyncio event loop

# Add current directory to path
sys.path.append(os.getcwd())

from scripts.run_trading_cycle import run_manual_cycle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("continuous_loop.log"),
    ],
)
logger = logging.getLogger(__name__)


async def _init_task_scheduler():
    """Initialize and start background RLM task scheduler."""
    try:
        from src.agents.context_agent import ContextAgent
        from src.agents.learning_observer import LearningObserver
        from src.core.config import GeminiConfig, GroqConfig, TradingConfig
        from src.services.llm_service import LLMService
        from src.services.task_scheduler import TaskScheduler

        config = TradingConfig()
        gemini_config = GeminiConfig()
        groq_config = GroqConfig()

        if not (groq_config.api_key.get_secret_value() or gemini_config.api_key.get_secret_value()):
            logger.info("No LLM API keys - TaskScheduler disabled")
            return None

        llm_service = LLMService(gemini_config=gemini_config, groq_config=groq_config)

        if not llm_service.is_enabled:
            logger.info("LLM providers unavailable - TaskScheduler disabled")
            return None

        context_agent = ContextAgent(
            llm_service=llm_service,
            cache_ttl_minutes=config.context_cache_ttl_minutes,
        )
        learning_observer = LearningObserver(llm_service=llm_service)

        async def get_current_prices():
            """Fetch current prices from database (latest bar close)."""
            from decimal import Decimal

            from sqlalchemy import select

            from src.core.database import get_session
            from src.models.bars import Bar1m

            prices = {}
            try:
                async with get_session() as session:
                    for symbol in config.symbols:
                        stmt = (
                            select(Bar1m.close)
                            .where(Bar1m.symbol == symbol)
                            .order_by(Bar1m.timestamp.desc())
                            .limit(1)
                        )
                        result = await session.execute(stmt)
                        price = result.scalar_one_or_none()
                        if price is not None:
                            prices[symbol] = Decimal(str(price))
            except Exception as e:
                logger.error(f"Failed to fetch current prices: {e}")
            return prices

        scheduler = TaskScheduler(
            learning_observer=learning_observer,
            context_agent=context_agent,
            get_current_prices=get_current_prices,
            symbols=config.symbols,
        )
        await scheduler.start()
        logger.info("Background RLM TaskScheduler started")
        return scheduler

    except Exception as e:
        logger.error(f"Failed to initialize TaskScheduler: {e}", exc_info=True)
        return None


async def main():
    logger.info("=" * 70)
    logger.info("Starting Phase 2 Agentic Trading System")
    logger.info("=" * 70)

    # Start background RLM tasks
    scheduler = await _init_task_scheduler()

    cycle_count = 0

    try:
        while True:
            cycle_count += 1
            start_time = time.time()
            logger.info(f"=== Starting Cycle #{cycle_count} ===")

            try:
                logger.info(">>> Running Trading Logic...")
                await run_manual_cycle()
            except Exception as e:
                logger.error(f"Cycle failed: {e}", exc_info=True)

            duration = time.time() - start_time
            logger.info(f"=== Cycle #{cycle_count} Completed in {duration:.2f}s ===")

            # Log scheduler status periodically
            if scheduler and cycle_count % 10 == 0:
                status = scheduler.get_status()
                logger.info(f"TaskScheduler status: {status}")

            # Sleep for remainder of minute
            sleep_time = max(10, 60 - duration)
            logger.info(f"Sleeping for {sleep_time:.2f}s...")
            await asyncio.sleep(sleep_time)

    finally:
        if scheduler:
            await scheduler.stop()
            logger.info("TaskScheduler stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Loop stopped by user.")
