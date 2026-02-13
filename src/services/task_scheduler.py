"""Professional-grade async task scheduler for RLM background tasks."""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from decimal import Decimal
from typing import TYPE_CHECKING

from src.core.database import get_session

if TYPE_CHECKING:
    from src.agents.context_agent import ContextAgent
    from src.agents.learning_observer import LearningObserver

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    Async task scheduler for Recursive Learning Model background tasks.

    Tasks:
    - Observation loop: Check predictions every 5 minutes
    - Reflection loop: Run LLM reflection every 15 minutes
    - News refresh: Update context analysis every 30 minutes
    """

    def __init__(
        self,
        learning_observer: "LearningObserver | None" = None,
        context_agent: "ContextAgent | None" = None,
        get_current_prices: Callable[[], Coroutine[None, None, dict[str, Decimal]]] | None = None,
        symbols: list[str] | None = None,
    ):
        """
        Initialize task scheduler.

        Args:
            learning_observer: Learning observer agent
            context_agent: Context agent
            get_current_prices: Async function that returns current prices
            symbols: List of symbols to monitor
        """
        self.learning_observer = learning_observer
        self.context_agent = context_agent
        self.get_current_prices = get_current_prices
        self.symbols = symbols or ["USO", "UNG"]
        self.tasks: dict[str, asyncio.Task] = {}
        self._running = False

    async def start(self) -> None:
        """Start all background tasks."""
        if self._running:
            logger.warning("Task scheduler already running")
            return

        self._running = True
        logger.info("Starting RLM task scheduler...")

        # Start observation loop (every 5 min)
        if self.learning_observer:
            self.tasks["observation_loop"] = asyncio.create_task(
                self._run_observation_loop()
            )
            logger.info("Started observation loop (5 min interval)")

        # Start reflection loop (every 15 min)
        if self.learning_observer:
            self.tasks["reflection_loop"] = asyncio.create_task(
                self._run_reflection_loop()
            )
            logger.info("Started reflection loop (15 min interval)")

        # Start news refresh loop (every 30 min)
        if self.context_agent:
            self.tasks["news_refresh"] = asyncio.create_task(
                self._run_news_refresh_loop()
            )
            logger.info("Started news refresh loop (30 min interval)")

        logger.info(f"Task scheduler started with {len(self.tasks)} active tasks")

    async def stop(self) -> None:
        """Stop all background tasks."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping task scheduler...")

        # Cancel all tasks
        for task_name, task in self.tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug(f"Task {task_name} cancelled")

        self.tasks.clear()
        logger.info("Task scheduler stopped")

    async def _run_observation_loop(self) -> None:
        """Check predictions every 5 minutes."""
        while self._running:
            try:
                # Get current prices
                current_prices = {}
                if self.get_current_prices:
                    current_prices = await self.get_current_prices()
                else:
                    # Fallback: use placeholder prices
                    logger.warning("No price getter configured, skipping observation")

                if current_prices:
                    async with get_session() as session:
                        updated = await self.learning_observer.check_pending_observations(
                            session=session,
                            current_prices=current_prices,
                        )
                        if updated:
                            logger.info(f"Observed {len(updated)} predictions")

            except Exception as e:
                logger.error(f"Error in observation loop: {e}", exc_info=True)

            # Wait 5 minutes
            await asyncio.sleep(300)

    async def _run_reflection_loop(self) -> None:
        """Run LLM reflection every 15 minutes."""
        # Initial delay to stagger from observation loop
        await asyncio.sleep(60)

        while self._running:
            try:
                async with get_session() as session:
                    reflected = await self.learning_observer.run_reflection_batch(
                        session=session
                    )
                    if reflected:
                        logger.info(f"Reflected on {len(reflected)} predictions")

            except Exception as e:
                logger.error(f"Error in reflection loop: {e}", exc_info=True)

            # Wait 15 minutes
            await asyncio.sleep(900)

    async def _run_news_refresh_loop(self) -> None:
        """Refresh news context every 30 minutes."""
        # Initial delay to stagger from other loops
        await asyncio.sleep(120)

        while self._running:
            try:
                # Build market metrics for each symbol
                current_prices = {}
                if self.get_current_prices:
                    current_prices = await self.get_current_prices()

                market_metrics_by_symbol = {}
                for symbol in self.symbols:
                    market_metrics_by_symbol[symbol] = {
                        "price": float(current_prices.get(symbol, Decimal("0"))),
                        "daily_change_pct": 0.0,  # TODO: Calculate from bars
                        "volume_ratio": 1.0,  # TODO: Calculate from bars
                        "rsi": None,
                    }

                refreshed = await self.context_agent.refresh_all_symbols(
                    symbols=self.symbols,
                    market_metrics_by_symbol=market_metrics_by_symbol,
                )

                if refreshed > 0:
                    logger.info(f"Refreshed context for {refreshed} symbols")

            except Exception as e:
                logger.error(f"Error in news refresh loop: {e}", exc_info=True)

            # Wait 30 minutes
            await asyncio.sleep(1800)

    @property
    def is_running(self) -> bool:
        """Check if scheduler is currently running."""
        return self._running

    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "running": self._running,
            "active_tasks": len(self.tasks),
            "tasks": {
                name: "running" if not task.done() else "completed"
                for name, task in self.tasks.items()
            },
        }
