"""Learning Observer Agent - implements Recursive Learning Model for continuous improvement."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.learning import LearningLog, StrategyOverride
from src.services.discord_notifier import DiscordNotifier
from src.services.llm_service import LLMService
from src.strategies import Signal

logger = logging.getLogger(__name__)


class LearningObserver:
    """
    Recursive Learning Model implementation.

    Three phases:
    1. PREDICT: Log prediction when signal is generated
    2. OBSERVE: Check actual outcome after horizon
    3. REFLECT: Analyze with LLM and suggest adjustments
    """

    def __init__(
        self,
        llm_service: LLMService,
        prediction_horizon_minutes: int = 60,
        reflection_batch_size: int = 5,
        discord_notifier: DiscordNotifier | None = None,
    ):
        """
        Initialize Learning Observer.

        Args:
            llm_service: LLM service for reflection
            prediction_horizon_minutes: Time horizon for predictions
            reflection_batch_size: Max predictions to reflect on per batch
            discord_notifier: Optional Discord notifier for adjustment alerts
        """
        self.llm = llm_service
        self.prediction_horizon_minutes = prediction_horizon_minutes
        self.reflection_batch_size = reflection_batch_size
        self.discord = discord_notifier

    # ===== PHASE 1: PREDICT =====

    async def log_prediction(
        self,
        signal: Signal,
        session: AsyncSession,
        signal_id: int | None = None,
        rsi: float | None = None,
        atr: float | None = None,
        sentiment_score: Decimal | None = None,
        context_tag: str | None = None,
    ) -> LearningLog:
        """
        Log a prediction when a signal is generated.

        Args:
            signal: The trading signal
            session: Database session
            signal_id: Optional FK to signals table
            rsi: RSI at signal time
            atr: ATR at signal time
            sentiment_score: From ContextAgent
            context_tag: From ContextAgent

        Returns:
            Created LearningLog entry
        """
        target = signal.suggested_target or signal.suggested_entry

        # Determine predicted outcome based on direction
        predicted_outcome = (
            f"{signal.direction.value} to ${target:.2f} within {self.prediction_horizon_minutes}min"
        )

        log = LearningLog(
            signal_id=signal_id,
            symbol=signal.symbol,
            direction=signal.direction.value,
            strategy_name=signal.strategy_name,
            predicted_at=datetime.now(),
            predicted_outcome=predicted_outcome,
            predicted_target=target,
            prediction_horizon_mins=self.prediction_horizon_minutes,
            entry_price=signal.suggested_entry,
            market_regime=signal.market_regime.value if signal.market_regime else None,
            rsi_at_signal=Decimal(str(rsi)) if rsi else None,
            atr_at_signal=Decimal(str(atr)) if atr else None,
            sentiment_score=sentiment_score,
            context_tag=context_tag,
        )

        session.add(log)
        await session.flush()

        logger.info(
            f"Logged prediction #{log.id}: {signal.strategy_name} {signal.direction.value} {signal.symbol}"
        )
        return log

    # ===== PHASE 2: OBSERVE =====

    async def check_pending_observations(
        self,
        session: AsyncSession,
        current_prices: dict[str, Decimal],
    ) -> list[LearningLog]:
        """
        Check predictions that are past their horizon and record outcomes.

        Args:
            session: Database session
            current_prices: Dict of symbol -> current price

        Returns:
            List of updated LearningLog entries
        """
        # Find predictions past their horizon that haven't been observed
        cutoff = datetime.now() - timedelta(minutes=self.prediction_horizon_minutes)

        query = (
            select(LearningLog)
            .where(LearningLog.observed_at.is_(None))
            .where(LearningLog.predicted_at < cutoff)
            .limit(50)  # Process in batches
        )

        result = await session.execute(query)
        pending = result.scalars().all()

        updated = []
        for log in pending:
            if log.symbol not in current_prices:
                continue

            current_price = current_prices[log.symbol]

            # Determine if prediction was correct
            if log.direction == "LONG":
                correct = current_price >= log.predicted_target
            else:  # SHORT
                correct = current_price <= log.predicted_target

            # Calculate actual outcome
            if log.direction == "LONG":
                pnl_pct = ((current_price - log.entry_price) / log.entry_price) * 100
            else:
                pnl_pct = ((log.entry_price - current_price) / log.entry_price) * 100

            log.observed_at = datetime.now()
            log.actual_price = current_price
            log.actual_outcome = f"Price moved to ${current_price:.2f} ({pnl_pct:+.2f}%)"
            log.prediction_correct = correct

            updated.append(log)
            logger.info(f"Observed #{log.id}: correct={correct}, price=${current_price:.2f}")

        return updated

    # ===== PHASE 3: REFLECT =====

    async def run_reflection_batch(
        self,
        session: AsyncSession,
    ) -> list[LearningLog]:
        """
        Run LLM reflection on observed predictions that haven't been reflected.

        Returns:
            List of reflected LearningLog entries
        """
        if not self.llm.is_enabled:
            return []

        # Find observed but not reflected
        query = (
            select(LearningLog)
            .where(LearningLog.observed_at.is_not(None))
            .where(LearningLog.reflected_at.is_(None))
            .order_by(LearningLog.observed_at.asc())
            .limit(self.reflection_batch_size)
        )

        result = await session.execute(query)
        pending = result.scalars().all()

        reflected = []
        for log in pending:
            try:
                # Get historical accuracy for this strategy
                historical = await self._get_strategy_accuracy(log.strategy_name, session)

                # Generate reflection via LLM
                reflection_result = await self.llm.generate_reflection(
                    prediction={
                        "symbol": log.symbol,
                        "direction": log.direction,
                        "strategy": log.strategy_name,
                        "target": float(log.predicted_target),
                        "entry": float(log.entry_price),
                    },
                    actual_outcome={
                        "exit_price": float(log.actual_price),
                        "correct": log.prediction_correct,
                        "pnl_pct": float(
                            (log.actual_price - log.entry_price) / log.entry_price * 100
                        )
                        if log.direction == "LONG"
                        else float((log.entry_price - log.actual_price) / log.entry_price * 100),
                    },
                    historical_accuracy=historical,
                )

                log.reflected_at = datetime.now()
                log.reflection_response = reflection_result.get("reflection", "")
                log.suggested_adjustment = reflection_result.get("suggested_adjustment", {})

                reflected.append(log)
                logger.info(f"Reflected #{log.id}: {log.reflection_response[:100]}...")

                # Auto-apply adjustment if magnitude is significant
                if log.suggested_adjustment.get("parameter") != "none":
                    await self.apply_suggested_adjustment(log, session, override_duration_hours=24)

            except Exception as e:
                logger.error(f"Failed to reflect on #{log.id}: {e}")

        return reflected

    async def _get_strategy_accuracy(
        self,
        strategy_name: str,
        session: AsyncSession,
    ) -> dict:
        """Get historical accuracy metrics for a strategy."""
        # Count wins/losses in last 30 days
        cutoff = datetime.now() - timedelta(days=30)

        query = (
            select(
                func.count(LearningLog.id).label("total"),
                func.sum(func.cast(LearningLog.prediction_correct, func.INTEGER)).label("wins"),
            )
            .where(LearningLog.strategy_name == strategy_name)
            .where(LearningLog.observed_at.is_not(None))
            .where(LearningLog.observed_at >= cutoff)
        )

        result = await session.execute(query)
        row = result.first()

        total = row.total or 0
        wins = row.wins or 0

        return {
            "win_rate": (wins / total * 100) if total > 0 else None,
            "total_predictions": total,
            "avg_win": "N/A",  # Would need P&L tracking
            "avg_loss": "N/A",
        }

    # ===== STRATEGY OVERRIDES =====

    async def apply_suggested_adjustment(
        self,
        learning_log: LearningLog,
        session: AsyncSession,
        override_duration_hours: int = 24,
    ) -> StrategyOverride | None:
        """
        Apply a suggested adjustment as a strategy override (AUTO-APPLY MODE).

        Args:
            learning_log: The LearningLog with suggested_adjustment
            session: Database session
            override_duration_hours: How long override should last

        Returns:
            Created StrategyOverride or None
        """
        adj = learning_log.suggested_adjustment
        if not adj or adj.get("parameter") == "none":
            return None

        # Safety check: Don't auto-apply if magnitude is too large
        magnitude = adj.get("magnitude", "none").lower()
        if magnitude in ["large", "extreme"]:
            logger.warning(
                f"Skipping auto-apply for {learning_log.strategy_name}: magnitude too large ({magnitude})"
            )
            return None

        override = StrategyOverride(
            strategy_name=learning_log.strategy_name,
            parameter_name=adj.get("parameter"),
            override_value=adj.get("direction", "none"),
            reason=adj.get("reason"),
            applied_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=override_duration_hours),
            learning_log_id=learning_log.id,
        )

        session.add(override)
        await session.flush()

        # Mark adjustment as applied
        learning_log.adjustment_applied = True

        logger.warning(
            f"🤖 RLM AUTO-APPLIED: {override.strategy_name}.{override.parameter_name} = {override.override_value} "
            f"(expires in {override_duration_hours}h)"
        )

        # Send Discord notification
        if self.discord:
            try:
                await self.discord.send_message(
                    message=(
                        f"🤖 **RLM Auto-Adjustment Applied**\n"
                        f"Strategy: `{override.strategy_name}`\n"
                        f"Parameter: `{override.parameter_name}`\n"
                        f"Direction: `{override.override_value}`\n"
                        f"Reason: {override.reason}\n"
                        f"Expires: {override.expires_at.strftime('%Y-%m-%d %H:%M')}\n"
                        f"Learning Log: #{learning_log.id}"
                    ),
                    title="RLM Adjustment",
                )
            except Exception as e:
                logger.error(f"Failed to send Discord notification: {e}")

        return override

    async def get_active_overrides(
        self,
        strategy_name: str,
        session: AsyncSession,
    ) -> list[StrategyOverride]:
        """Get all active overrides for a strategy."""
        query = (
            select(StrategyOverride)
            .where(StrategyOverride.strategy_name == strategy_name)
            .where(StrategyOverride.reverted_at.is_(None))
            .where(StrategyOverride.expires_at > datetime.now())
        )

        result = await session.execute(query)
        return list(result.scalars().all())
