"""Coordinator Agent - orchestrates the entire trading workflow."""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.agents.execution_agent import ExecutionAgent, ExecutionDecision
from src.agents.risk_manager import RiskManagerAgent
from src.agents.settlement_tracker import SettlementTrackerAgent
from src.agents.strategy_pool import StrategyPoolAgent
from src.agents.strategy_selector import StrategySelectorAgent
from src.core.config import TradingConfig
from src.services.alpaca_api import AlpacaService
from src.services.circuit_breakers import CircuitBreakerService
from src.services.discord_notifier import DiscordNotifier
from src.strategies import Signal

logger = logging.getLogger(__name__)


@dataclass
class TradeDecision:
    """Complete trade decision with all agent outputs."""

    approved: bool
    signal: Signal | None
    rejection_reason: str
    execution_result: dict | None
    risk_decision: dict | None
    breaker_status: dict | None
    settlement_status: dict | None


class CoordinatorAgent:
    """
    Master coordinator that orchestrates the entire trading workflow.

    Workflow:
    1. Market regime detection → Strategy selection
    2. Strategy execution → Signal generation
    3. Signal filtering and ranking
    4. Risk validation
    5. Settlement check (T+1 compliance)
    6. Circuit breaker check
    7. Execution (if approved)
    8. Notifications
    """

    def __init__(
        self,
        config: TradingConfig,
        strategy_selector: StrategySelectorAgent,
        strategy_pool: StrategyPoolAgent,
        risk_manager: RiskManagerAgent,
        settlement_tracker: SettlementTrackerAgent,
        circuit_breakers: CircuitBreakerService,
        execution_agent: ExecutionAgent,
        notifier: DiscordNotifier | None = None,
    ):
        """
        Initialize Coordinator Agent.

        Args:
            config: Trading configuration
            strategy_selector: Strategy selection agent
            strategy_pool: Strategy pool agent
            risk_manager: Risk management agent
            settlement_tracker: Settlement tracking agent
            circuit_breakers: Circuit breaker service
            execution_agent: Execution agent
            notifier: Discord notifier (optional)
        """
        self.config = config
        self.strategy_selector = strategy_selector
        self.strategy_pool = strategy_pool
        self.risk_manager = risk_manager
        self.settlement_tracker = settlement_tracker
        self.circuit_breakers = circuit_breakers
        self.execution_agent = execution_agent
        self.notifier = notifier

        logger.info("Coordinator Agent initialized")

    async def run_trading_cycle(
        self,
        market_data: dict,
        account_balance: Decimal,
        current_positions: int,
        daily_trades_count: int,
        consecutive_losses: int,
    ) -> TradeDecision:
        """
        Run complete trading cycle.

        Args:
            market_data: Market data (bars, indicators, etc.)
            account_balance: Current account balance
            current_positions: Number of open positions
            daily_trades_count: Trades executed today
            consecutive_losses: Consecutive losing trades

        Returns:
            TradeDecision with approval status and details
        """
        logger.info("=" * 60)
        logger.info("Starting trading cycle")
        logger.info("=" * 60)

        # === STEP 1: Check Circuit Breakers ===
        portfolio_risk = await self.risk_manager.calculate_portfolio_heat(account_balance)

        breaker_status = await self.circuit_breakers.check_all_breakers(
            daily_pnl_pct=Decimal("0.0"),  # TODO: Calculate from account
            consecutive_losses=consecutive_losses,
            portfolio_heat=portfolio_risk.current_heat,
        )

        if breaker_status.is_tripped:
            logger.warning(f"Circuit breakers tripped: {breaker_status.reasons}")
            if self.notifier:
                for breaker_type, reason in zip(
                    breaker_status.active_breakers, breaker_status.reasons
                ):
                    await self.notifier.notify_circuit_breaker(
                        breaker_type=breaker_type.value,
                        reason=reason,
                        active_count=len(breaker_status.active_breakers),
                    )

            return TradeDecision(
                approved=False,
                signal=None,
                rejection_reason=f"Circuit breaker: {', '.join(breaker_status.reasons)}",
                execution_result=None,
                risk_decision=None,
                breaker_status={
                    "is_tripped": breaker_status.is_tripped,
                    "active_breakers": [b.value for b in breaker_status.active_breakers],
                    "reasons": breaker_status.reasons,
                },
                settlement_status=None,
            )

        logger.info("✓ Circuit breakers clear")

        # === STEP 2: Strategy Selection & Signal Generation ===
        # This would normally use real market data
        # For now, we'll check if any strategies should run
        logger.info("Checking strategy selection...")

        # TODO: Implement actual strategy execution with market data
        # signals = await self.strategy_pool.execute_all_strategies(...)

        # For now, return no signal (would be generated in real implementation)
        logger.info("No signals generated in this cycle")

        return TradeDecision(
            approved=False,
            signal=None,
            rejection_reason="No signals generated",
            execution_result=None,
            risk_decision=None,
            breaker_status=None,
            settlement_status=None,
        )

    async def evaluate_signal(
        self,
        signal: Signal,
        account_balance: Decimal,
        current_positions: int,
        daily_trades_count: int,
        consecutive_losses: int,
    ) -> TradeDecision:
        """
        Evaluate a trading signal through complete validation pipeline.

        Args:
            signal: Trading signal to evaluate
            account_balance: Current account balance
            current_positions: Number of open positions
            daily_trades_count: Trades executed today
            consecutive_losses: Consecutive losing trades

        Returns:
            TradeDecision with approval status
        """
        logger.info(f"Evaluating signal: {signal.direction.value} {signal.symbol}")

        # === STEP 1: Circuit Breaker Check ===
        portfolio_risk = await self.risk_manager.calculate_portfolio_heat(account_balance)

        breaker_status = await self.circuit_breakers.check_all_breakers(
            daily_pnl_pct=Decimal("0.0"),  # TODO: Get from account
            consecutive_losses=consecutive_losses,
            portfolio_heat=portfolio_risk.current_heat,
        )

        if breaker_status.is_tripped:
            logger.warning(f"Signal rejected by circuit breakers: {breaker_status.reasons}")
            return TradeDecision(
                approved=False,
                signal=signal,
                rejection_reason=f"Circuit breaker: {', '.join(breaker_status.reasons)}",
                execution_result=None,
                risk_decision=None,
                breaker_status={
                    "is_tripped": True,
                    "reasons": breaker_status.reasons,
                },
                settlement_status=None,
            )

        # === STEP 2: Settlement Check ===
        settlement_status = await self.settlement_tracker.get_settlement_status(
            total_cash=account_balance
        )

        logger.info(
            f"Settlement: ${settlement_status.total_settled:.2f} settled, "
            f"${settlement_status.total_pending:.2f} pending"
        )

        # === STEP 3: Risk Validation ===
        risk_decision = await self.risk_manager.evaluate_trade(
            signal=signal,
            account_balance=account_balance,
            settled_cash=settlement_status.available_to_trade,
            current_positions=current_positions,
            portfolio_heat=portfolio_risk.current_heat,
            daily_trades_count=daily_trades_count,
            consecutive_losses=consecutive_losses,
        )

        if not risk_decision.approved:
            logger.warning(f"Signal rejected by risk manager: {risk_decision.reason}")

            # Notify about rejection
            if self.notifier:
                failed_checks = [
                    check for check, passed in risk_decision.passed_checks.items()
                    if not passed
                ]
                await self.notifier.notify_risk_rejection(
                    symbol=signal.symbol,
                    reason=risk_decision.reason,
                    failed_checks=failed_checks,
                )

            return TradeDecision(
                approved=False,
                signal=signal,
                rejection_reason=f"Risk check failed: {risk_decision.reason}",
                execution_result=None,
                risk_decision={
                    "approved": False,
                    "reason": risk_decision.reason,
                    "passed_checks": risk_decision.passed_checks,
                },
                breaker_status=None,
                settlement_status={
                    "total_settled": str(settlement_status.total_settled),
                    "available": str(settlement_status.available_to_trade),
                },
            )

        logger.info(
            f"✓ Risk approved: {risk_decision.position_size} shares, "
            f"${risk_decision.risk_amount:.2f} at risk ({risk_decision.risk_pct:.2%})"
        )

        # === STEP 4: Execute Trade ===
        execution_result = await self.execution_agent.execute_signal(
            signal=signal,
            position_size=risk_decision.position_size,
            account_balance=account_balance,
        )

        logger.info(f"Execution: {execution_result.decision.value} - {execution_result.message}")

        # === STEP 5: Send Notifications ===
        if self.notifier:
            # Notify signal generation
            await self.notifier.notify_signal_generated(
                symbol=signal.symbol,
                direction=signal.direction.value,
                strategy=signal.strategy_name,
                confidence=signal.confidence,
                entry=signal.suggested_entry,
                stop=signal.suggested_stop,
                target=signal.suggested_target,
            )

            # Notify execution if approved
            if execution_result.decision == ExecutionDecision.EXECUTE:
                await self.notifier.notify_trade_execution(
                    symbol=signal.symbol,
                    side=signal.direction.value,
                    qty=risk_decision.position_size,
                    price=signal.suggested_entry,
                    order_id=execution_result.order_id,
                    is_paper=execution_result.metadata.get("is_paper", False),
                )
            elif execution_result.requires_confirmation:
                await self.notifier.notify_confirmation_required(
                    symbol=signal.symbol,
                    direction=signal.direction.value,
                    qty=risk_decision.position_size,
                    entry=signal.suggested_entry,
                    stop=signal.suggested_stop,
                    target=signal.suggested_target,
                    order_id=execution_result.order_id,
                )

        # === Return Decision ===
        return TradeDecision(
            approved=execution_result.decision in [
                ExecutionDecision.EXECUTE,
                ExecutionDecision.REQUEST_CONFIRMATION,
            ],
            signal=signal,
            rejection_reason="" if execution_result.decision == ExecutionDecision.EXECUTE else execution_result.message,
            execution_result={
                "decision": execution_result.decision.value,
                "order_id": execution_result.order_id,
                "message": execution_result.message,
                "requires_confirmation": execution_result.requires_confirmation,
            },
            risk_decision={
                "approved": True,
                "position_size": str(risk_decision.position_size),
                "risk_amount": str(risk_decision.risk_amount),
                "risk_pct": str(risk_decision.risk_pct),
            },
            breaker_status={"is_tripped": False},
            settlement_status={
                "total_settled": str(settlement_status.total_settled),
                "available": str(settlement_status.available_to_trade),
            },
        )

    async def shutdown(self):
        """Graceful shutdown - close all positions if configured."""
        logger.info("Coordinator shutdown initiated")
        # TODO: Implement graceful shutdown
        # - Cancel pending orders
        # - Close positions if end-of-day
        # - Send summary notification
        logger.info("Coordinator shutdown complete")
