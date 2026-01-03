"""Circuit breaker service for safety stops and trading halts."""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from src.core.database import get_session
from src.models.risk import CircuitBreaker

logger = logging.getLogger(__name__)


class CircuitBreakerType(str, Enum):
    """Types of circuit breakers."""

    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    DAILY_PROFIT_TARGET = "DAILY_PROFIT_TARGET"
    CONSECUTIVE_LOSSES = "CONSECUTIVE_LOSSES"
    PORTFOLIO_HEAT = "PORTFOLIO_HEAT"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    STALE_DATA = "STALE_DATA"
    MANUAL_KILL_SWITCH = "MANUAL_KILL_SWITCH"


@dataclass
class CircuitBreakerStatus:
    """Circuit breaker status."""

    is_tripped: bool
    active_breakers: list[CircuitBreakerType]
    reasons: list[str]
    can_trade: bool


class CircuitBreakerService:
    """
    Service for managing 7-layer safety circuit breakers.

    Breakers:
    1. Daily loss limit
    2. Daily profit target (stop on green)
    3. Consecutive losses
    4. Portfolio heat
    5. Volatility spike
    6. Stale data detection
    7. Manual kill switch
    """

    def __init__(
        self,
        daily_loss_limit_pct: Decimal = Decimal("0.03"),
        daily_profit_target_pct: Decimal = Decimal("0.02"),
        max_consecutive_losses: int = 3,
        max_portfolio_heat_pct: Decimal = Decimal("0.05"),
        max_volatility_spike_pct: Decimal = Decimal("0.05"),
        stale_data_threshold_minutes: int = 10,
    ):
        """
        Initialize Circuit Breaker Service.

        Args:
            daily_loss_limit_pct: Daily loss limit (e.g., 0.03 = 3%)
            daily_profit_target_pct: Daily profit target (e.g., 0.02 = 2%)
            max_consecutive_losses: Max consecutive losing trades
            max_portfolio_heat_pct: Max total portfolio risk
            max_volatility_spike_pct: Max sudden volatility increase
            stale_data_threshold_minutes: Max age of data before considered stale
        """
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.daily_profit_target_pct = daily_profit_target_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.max_portfolio_heat_pct = max_portfolio_heat_pct
        self.max_volatility_spike_pct = max_volatility_spike_pct
        self.stale_data_threshold_minutes = stale_data_threshold_minutes

    async def check_all_breakers(
        self,
        daily_pnl_pct: Decimal,
        consecutive_losses: int,
        portfolio_heat: Decimal,
        current_volatility: Decimal | None = None,
        baseline_volatility: Decimal | None = None,
        last_data_update: datetime | None = None,
    ) -> CircuitBreakerStatus:
        """
        Check all circuit breakers and return status.

        Args:
            daily_pnl_pct: Daily P&L as percentage
            consecutive_losses: Number of consecutive losses
            portfolio_heat: Current portfolio risk exposure
            current_volatility: Current market volatility (optional)
            baseline_volatility: Baseline volatility for comparison (optional)
            last_data_update: Timestamp of last data update (optional)

        Returns:
            CircuitBreakerStatus
        """
        active_breakers: list[CircuitBreakerType] = []
        reasons: list[str] = []

        # === 1. Daily Loss Limit ===
        if daily_pnl_pct <= -self.daily_loss_limit_pct:
            active_breakers.append(CircuitBreakerType.DAILY_LOSS_LIMIT)
            reasons.append(
                f"Daily loss limit hit ({daily_pnl_pct:.2%} <= -{self.daily_loss_limit_pct:.2%})"
            )
            await self._trip_breaker(CircuitBreakerType.DAILY_LOSS_LIMIT, reasons[-1])

        # === 2. Daily Profit Target ===
        if daily_pnl_pct >= self.daily_profit_target_pct:
            active_breakers.append(CircuitBreakerType.DAILY_PROFIT_TARGET)
            reasons.append(
                f"Daily profit target hit ({daily_pnl_pct:.2%} >= {self.daily_profit_target_pct:.2%})"
            )
            await self._trip_breaker(CircuitBreakerType.DAILY_PROFIT_TARGET, reasons[-1])

        # === 3. Consecutive Losses ===
        if consecutive_losses >= self.max_consecutive_losses:
            active_breakers.append(CircuitBreakerType.CONSECUTIVE_LOSSES)
            reasons.append(
                f"Max consecutive losses ({consecutive_losses} >= {self.max_consecutive_losses})"
            )
            await self._trip_breaker(CircuitBreakerType.CONSECUTIVE_LOSSES, reasons[-1])

        # === 4. Portfolio Heat ===
        if portfolio_heat >= self.max_portfolio_heat_pct:
            active_breakers.append(CircuitBreakerType.PORTFOLIO_HEAT)
            reasons.append(
                f"Portfolio heat too high ({portfolio_heat:.2%} >= {self.max_portfolio_heat_pct:.2%})"
            )
            await self._trip_breaker(CircuitBreakerType.PORTFOLIO_HEAT, reasons[-1])

        # === 5. Volatility Spike ===
        if (
            current_volatility is not None
            and baseline_volatility is not None
            and baseline_volatility > 0
        ):
            volatility_increase = (current_volatility - baseline_volatility) / baseline_volatility
            if volatility_increase >= self.max_volatility_spike_pct:
                active_breakers.append(CircuitBreakerType.VOLATILITY_SPIKE)
                reasons.append(f"Volatility spike ({volatility_increase:.2%} increase)")
                await self._trip_breaker(CircuitBreakerType.VOLATILITY_SPIKE, reasons[-1])

        # === 6. Stale Data ===
        if last_data_update is not None:
            age_minutes = (datetime.now() - last_data_update).total_seconds() / 60
            if age_minutes > self.stale_data_threshold_minutes:
                active_breakers.append(CircuitBreakerType.STALE_DATA)
                reasons.append(
                    f"Stale data ({age_minutes:.1f} min old, threshold={self.stale_data_threshold_minutes} min)"
                )
                await self._trip_breaker(CircuitBreakerType.STALE_DATA, reasons[-1])

        # === 7. Manual Kill Switch ===
        if await self._is_kill_switch_active():
            active_breakers.append(CircuitBreakerType.MANUAL_KILL_SWITCH)
            reasons.append("Manual kill switch activated")

        # Determine if trading can proceed
        is_tripped = len(active_breakers) > 0
        can_trade = not is_tripped

        if is_tripped:
            logger.warning(f"Circuit breakers tripped: {[b.value for b in active_breakers]}")
        else:
            logger.debug("All circuit breakers clear")

        return CircuitBreakerStatus(
            is_tripped=is_tripped,
            active_breakers=active_breakers,
            reasons=reasons,
            can_trade=can_trade,
        )

    async def _trip_breaker(self, breaker_type: CircuitBreakerType, reason: str) -> None:
        """
        Record a circuit breaker trip in the database.

        Args:
            breaker_type: Type of breaker
            reason: Reason for trip
        """
        try:
            async with get_session() as session:
                breaker = CircuitBreaker(
                    breaker_type=breaker_type.value,
                    reason=reason,
                    is_active=True,
                )
                session.add(breaker)
            logger.warning(f"Circuit breaker tripped: {breaker_type.value} - {reason}")
        except Exception as e:
            logger.error(f"Failed to record circuit breaker trip: {e}")

    async def activate_kill_switch(self, reason: str = "Manual activation") -> None:
        """
        Activate the manual kill switch.

        Args:
            reason: Reason for activation
        """
        await self._trip_breaker(CircuitBreakerType.MANUAL_KILL_SWITCH, reason)
        logger.critical(f"KILL SWITCH ACTIVATED: {reason}")

    async def _is_kill_switch_active(self) -> bool:
        """
        Check if manual kill switch is currently active.

        Returns:
            True if kill switch is active
        """
        try:
            async with get_session() as session:
                from sqlalchemy import select

                stmt = select(CircuitBreaker).where(
                    CircuitBreaker.breaker_type == CircuitBreakerType.MANUAL_KILL_SWITCH.value,
                    CircuitBreaker.is_active == True,
                )
                result = await session.execute(stmt)
                active_switch = result.scalar_one_or_none()

            return active_switch is not None
        except Exception as e:
            logger.error(f"Failed to check kill switch status: {e}")
            # Fail safe: assume active if check fails
            return True

    async def clear_kill_switch(self) -> bool:
        """
        Deactivate the manual kill switch.

        Returns:
            True if cleared successfully
        """
        try:
            async with get_session() as session:
                from sqlalchemy import update

                stmt = (
                    update(CircuitBreaker)
                    .where(
                        CircuitBreaker.breaker_type == CircuitBreakerType.MANUAL_KILL_SWITCH.value,
                        CircuitBreaker.is_active == True,
                    )
                    .values(is_active=False, cleared_at=datetime.now())
                )
                result = await session.execute(stmt)

            if result.rowcount > 0:
                logger.info("Kill switch cleared")
                return True
            else:
                logger.warning("No active kill switch to clear")
                return False
        except Exception as e:
            logger.error(f"Failed to clear kill switch: {e}")
            return False

    async def clear_daily_breakers(self) -> int:
        """
        Clear daily circuit breakers (called at start of new trading day).

        Returns:
            Number of breakers cleared
        """
        daily_breakers = [
            CircuitBreakerType.DAILY_LOSS_LIMIT.value,
            CircuitBreakerType.DAILY_PROFIT_TARGET.value,
            CircuitBreakerType.CONSECUTIVE_LOSSES.value,
        ]

        try:
            async with get_session() as session:
                from sqlalchemy import update

                stmt = (
                    update(CircuitBreaker)
                    .where(
                        CircuitBreaker.breaker_type.in_(daily_breakers),
                        CircuitBreaker.is_active == True,
                    )
                    .values(is_active=False, cleared_at=datetime.now())
                )
                result = await session.execute(stmt)

            cleared_count = result.rowcount
            if cleared_count > 0:
                logger.info(f"Cleared {cleared_count} daily circuit breakers")
            return cleared_count
        except Exception as e:
            logger.error(f"Failed to clear daily breakers: {e}")
            return 0

    async def get_active_breakers(self) -> list[CircuitBreaker]:
        """
        Get all currently active circuit breakers.

        Returns:
            List of active CircuitBreaker records
        """
        try:
            async with get_session() as session:
                from sqlalchemy import select

                stmt = select(CircuitBreaker).where(CircuitBreaker.is_active == True)
                result = await session.execute(stmt)
                breakers = list(result.scalars().all())

            return breakers
        except Exception as e:
            logger.error(f"Failed to get active breakers: {e}")
            return []

    async def get_breaker_history(self, days: int = 7) -> list[CircuitBreaker]:
        """
        Get circuit breaker history for last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of CircuitBreaker records
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)

        try:
            async with get_session() as session:
                from sqlalchemy import select

                stmt = (
                    select(CircuitBreaker)
                    .where(CircuitBreaker.timestamp >= cutoff)
                    .order_by(CircuitBreaker.timestamp.desc())
                )
                result = await session.execute(stmt)
                breakers = list(result.scalars().all())

            logger.info(f"Retrieved {len(breakers)} breaker events from last {days} days")
            return breakers
        except Exception as e:
            logger.error(f"Failed to get breaker history: {e}")
            return []
