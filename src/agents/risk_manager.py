"""Risk Manager Agent - validates trades against risk parameters and circuit breakers."""

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.core.config import TradingConfig
from src.core.database import get_session
from src.models.position import Position
from src.strategies import Signal, SignalDirection

logger = logging.getLogger(__name__)


@dataclass
class RiskDecision:
    """Risk management decision."""

    approved: bool
    position_size: Decimal  # Shares to trade
    risk_amount: Decimal  # Dollar amount at risk
    risk_pct: Decimal  # Percentage of portfolio at risk
    portfolio_heat_after: Decimal  # Portfolio heat after this trade
    reason: str  # Explanation for decision
    passed_checks: dict[str, bool]  # Individual check results


@dataclass
class PortfolioRisk:
    """Current portfolio risk metrics."""

    total_positions: int
    portfolio_value: Decimal
    current_heat: Decimal  # Total risk as % of portfolio
    risk_per_position: dict[str, Decimal]  # Symbol -> risk amount
    max_position_risk: Decimal  # Largest single position risk


class RiskManagerAgent:
    """
    Agent responsible for:
    - Position sizing based on risk parameters
    - Portfolio heat calculation and enforcement
    - Circuit breaker checks
    - Risk/reward validation
    - Daily limit enforcement
    """

    def __init__(self, config: TradingConfig):
        """
        Initialize Risk Manager Agent.

        Args:
            config: Trading configuration with risk parameters
        """
        self.config = config

    async def evaluate_trade(
        self,
        signal: Signal,
        account_balance: Decimal,
        settled_cash: Decimal,
        current_positions: int,
        portfolio_heat: Decimal,
        daily_trades_count: int,
        consecutive_losses: int,
    ) -> RiskDecision:
        """
        Evaluate if a trade should be approved based on risk parameters.

        Args:
            signal: Trading signal to evaluate
            account_balance: Total account balance
            settled_cash: Settled cash available for trading
            current_positions: Number of open positions
            portfolio_heat: Current portfolio risk exposure
            daily_trades_count: Number of trades executed today
            consecutive_losses: Number of consecutive losing trades

        Returns:
            RiskDecision with approval and sizing
        """
        checks: dict[str, bool] = {}

        # === Check 1: Position Limit ===
        checks["position_limit"] = current_positions < self.config.max_positions
        if not checks["position_limit"]:
            return RiskDecision(
                approved=False,
                position_size=Decimal("0"),
                risk_amount=Decimal("0"),
                risk_pct=Decimal("0"),
                portfolio_heat_after=portfolio_heat,
                reason=f"Max positions reached ({current_positions}/{self.config.max_positions})",
                passed_checks=checks,
            )

        # === Check 2: Daily Trade Limit ===
        checks["daily_trade_limit"] = daily_trades_count < self.config.max_trades_per_day
        if not checks["daily_trade_limit"]:
            return RiskDecision(
                approved=False,
                position_size=Decimal("0"),
                risk_amount=Decimal("0"),
                risk_pct=Decimal("0"),
                portfolio_heat_after=portfolio_heat,
                reason=f"Daily trade limit reached ({daily_trades_count}/{self.config.max_trades_per_day})",
                passed_checks=checks,
            )

        # === Check 3: Consecutive Losses ===
        checks["consecutive_losses"] = (
            consecutive_losses < self.config.max_consecutive_losses
        )
        if not checks["consecutive_losses"]:
            return RiskDecision(
                approved=False,
                position_size=Decimal("0"),
                risk_amount=Decimal("0"),
                risk_pct=Decimal("0"),
                portfolio_heat_after=portfolio_heat,
                reason=f"Max consecutive losses reached ({consecutive_losses}/{self.config.max_consecutive_losses})",
                passed_checks=checks,
            )

        # === Check 4: Signal Quality ===
        # Signal must have entry and stop prices
        if signal.suggested_entry is None or signal.suggested_stop is None:
            return RiskDecision(
                approved=False,
                position_size=Decimal("0"),
                risk_amount=Decimal("0"),
                risk_pct=Decimal("0"),
                portfolio_heat_after=portfolio_heat,
                reason="Signal missing entry or stop price",
                passed_checks=checks,
            )

        # === Calculate Position Size ===
        position_size, risk_amount, risk_pct = self._calculate_position_size(
            signal, account_balance
        )

        checks["valid_position_size"] = position_size > 0
        if not checks["valid_position_size"]:
            return RiskDecision(
                approved=False,
                position_size=Decimal("0"),
                risk_amount=Decimal("0"),
                risk_pct=Decimal("0"),
                portfolio_heat_after=portfolio_heat,
                reason="Position size calculation failed or too small",
                passed_checks=checks,
            )

        # === Check 5: Risk Per Trade ===
        checks["risk_per_trade"] = risk_pct <= self.config.max_risk_per_trade_pct
        if not checks["risk_per_trade"]:
            return RiskDecision(
                approved=False,
                position_size=Decimal("0"),
                risk_amount=Decimal("0"),
                risk_pct=Decimal("0"),
                portfolio_heat_after=portfolio_heat,
                reason=f"Risk per trade too high ({risk_pct:.2%} > {self.config.max_risk_per_trade_pct:.2%})",
                passed_checks=checks,
            )

        # === Check 6: Portfolio Heat ===
        portfolio_heat_after = portfolio_heat + risk_pct
        checks["portfolio_heat"] = (
            portfolio_heat_after <= self.config.max_portfolio_heat_pct
        )
        if not checks["portfolio_heat"]:
            return RiskDecision(
                approved=False,
                position_size=position_size,
                risk_amount=risk_amount,
                risk_pct=risk_pct,
                portfolio_heat_after=portfolio_heat_after,
                reason=f"Portfolio heat too high ({portfolio_heat_after:.2%} > {self.config.max_portfolio_heat_pct:.2%})",
                passed_checks=checks,
            )

        # === Check 7: Settled Cash ===
        required_cash = position_size * signal.suggested_entry
        checks["settled_cash"] = settled_cash >= required_cash
        if not checks["settled_cash"]:
            return RiskDecision(
                approved=False,
                position_size=position_size,
                risk_amount=risk_amount,
                risk_pct=risk_pct,
                portfolio_heat_after=portfolio_heat_after,
                reason=f"Insufficient settled cash (need ${required_cash:.2f}, have ${settled_cash:.2f})",
                passed_checks=checks,
            )

        # === All checks passed ===
        return RiskDecision(
            approved=True,
            position_size=position_size,
            risk_amount=risk_amount,
            risk_pct=risk_pct,
            portfolio_heat_after=portfolio_heat_after,
            reason="All risk checks passed",
            passed_checks=checks,
        )

    def _calculate_position_size(
        self, signal: Signal, account_balance: Decimal
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Calculate position size based on risk parameters.

        Formula: position_size = (account_balance * risk_pct) / (entry - stop)

        Args:
            signal: Trading signal with entry and stop prices
            account_balance: Total account balance

        Returns:
            Tuple of (position_size, risk_amount, risk_pct)
        """
        if signal.suggested_entry is None or signal.suggested_stop is None:
            return Decimal("0"), Decimal("0"), Decimal("0")

        entry = signal.suggested_entry
        stop = signal.suggested_stop

        # Calculate risk per share
        risk_per_share = abs(entry - stop)
        if risk_per_share == 0:
            logger.warning("Risk per share is zero, cannot calculate position size")
            return Decimal("0"), Decimal("0"), Decimal("0")

        # Calculate max risk amount
        max_risk_amount = account_balance * self.config.risk_per_trade_pct

        # Calculate position size
        position_size = max_risk_amount / risk_per_share

        # Round down to whole shares
        position_size = Decimal(int(position_size))

        if position_size <= 0:
            return Decimal("0"), Decimal("0"), Decimal("0")

        # Calculate actual risk
        actual_risk_amount = position_size * risk_per_share
        actual_risk_pct = actual_risk_amount / account_balance

        # Apply position value cap (max single position size)
        max_position_value = account_balance * Decimal("0.25")  # 25% of portfolio max
        position_value = position_size * entry
        if position_value > max_position_value:
            position_size = max_position_value / entry
            position_size = Decimal(int(position_size))
            actual_risk_amount = position_size * risk_per_share
            actual_risk_pct = actual_risk_amount / account_balance

        logger.debug(
            f"Position sizing: {position_size} shares @ ${entry:.2f} "
            f"(risk=${actual_risk_amount:.2f}, {actual_risk_pct:.2%})"
        )

        return position_size, actual_risk_amount, actual_risk_pct

    async def calculate_portfolio_heat(self, account_balance: Decimal) -> PortfolioRisk:
        """
        Calculate current portfolio risk exposure.

        Args:
            account_balance: Total account balance

        Returns:
            PortfolioRisk metrics
        """
        try:
            async with get_session() as session:
                from sqlalchemy import select

                # Get all open positions
                stmt = select(Position).where(Position.is_open == True)
                result = await session.execute(stmt)
                positions = list(result.scalars().all())

            if not positions:
                return PortfolioRisk(
                    total_positions=0,
                    portfolio_value=account_balance,
                    current_heat=Decimal("0"),
                    risk_per_position={},
                    max_position_risk=Decimal("0"),
                )

            # Calculate risk for each position
            risk_per_position: dict[str, Decimal] = {}
            total_risk = Decimal("0")

            for pos in positions:
                if pos.risk_amount:
                    risk_amount = pos.risk_amount
                else:
                    # Calculate risk if not stored
                    if pos.stop_loss and pos.entry_price:
                        risk_per_share = abs(pos.entry_price - pos.stop_loss)
                        risk_amount = pos.qty * risk_per_share
                    else:
                        risk_amount = Decimal("0")

                risk_per_position[pos.symbol] = risk_amount
                total_risk += risk_amount

            # Calculate portfolio heat
            current_heat = total_risk / account_balance if account_balance > 0 else Decimal("0")
            max_position_risk = max(risk_per_position.values()) if risk_per_position else Decimal("0")

            logger.debug(
                f"Portfolio heat: {current_heat:.2%} "
                f"({len(positions)} positions, total risk=${total_risk:.2f})"
            )

            return PortfolioRisk(
                total_positions=len(positions),
                portfolio_value=account_balance,
                current_heat=current_heat,
                risk_per_position=risk_per_position,
                max_position_risk=max_position_risk,
            )

        except Exception as e:
            logger.error(f"Failed to calculate portfolio heat: {e}")
            return PortfolioRisk(
                total_positions=0,
                portfolio_value=account_balance,
                current_heat=Decimal("0"),
                risk_per_position={},
                max_position_risk=Decimal("0"),
            )

    async def should_reduce_position_size(
        self, signal: Signal, account_balance: Decimal
    ) -> tuple[bool, Decimal]:
        """
        Determine if position size should be reduced due to risk conditions.

        Args:
            signal: Trading signal
            account_balance: Account balance

        Returns:
            Tuple of (should_reduce: bool, reduction_factor: Decimal)
        """
        portfolio_risk = await self.calculate_portfolio_heat(account_balance)

        # No reduction needed if portfolio heat is low
        if portfolio_risk.current_heat < Decimal("0.03"):  # Less than 3%
            return False, Decimal("1.0")

        # Reduce position size as heat increases
        if portfolio_risk.current_heat >= Decimal("0.04"):  # 4%+
            return True, Decimal("0.5")  # 50% reduction

        return False, Decimal("1.0")

    def validate_risk_reward_ratio(
        self, signal: Signal, min_ratio: Decimal = Decimal("1.5")
    ) -> tuple[bool, Decimal]:
        """
        Validate that risk/reward ratio meets minimum threshold.

        Args:
            signal: Trading signal with entry, stop, and target
            min_ratio: Minimum acceptable R:R ratio

        Returns:
            Tuple of (valid: bool, actual_ratio: Decimal)
        """
        if not all([signal.suggested_entry, signal.suggested_stop, signal.suggested_target]):
            return False, Decimal("0")

        entry = signal.suggested_entry
        stop = signal.suggested_stop
        target = signal.suggested_target

        risk = abs(entry - stop)
        reward = abs(target - entry)

        if risk == 0:
            return False, Decimal("0")

        ratio = reward / risk

        is_valid = ratio >= min_ratio

        logger.debug(
            f"Risk/Reward: {ratio:.2f} (risk=${risk:.2f}, reward=${reward:.2f}) "
            f"{'✓' if is_valid else '✗ below minimum'}"
        )

        return is_valid, ratio
