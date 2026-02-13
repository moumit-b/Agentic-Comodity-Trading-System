"""Integration tests for Phase 5: Coordinator Agent."""

from datetime import datetime
from decimal import Decimal

import pytest

from src.agents import (
    CoordinatorAgent,
    ExecutionAgent,
    RiskManagerAgent,
    SettlementTrackerAgent,
    StrategyPoolAgent,
    StrategySelectorAgent,
)
from src.core.config import AutomationMode, TradingConfig
from src.services import CircuitBreakerService
from src.strategies import Signal, SignalDirection


class TestCoordinator:
    """Test Coordinator Agent."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return TradingConfig(
            max_positions=5,
            max_trades_per_day=10,
        )

    @pytest.fixture
    def coordinator(self, config):
        """Create coordinator with all dependencies."""
        strategy_selector = StrategySelectorAgent(config)
        strategy_pool = StrategyPoolAgent()
        risk_manager = RiskManagerAgent(config)
        settlement_tracker = SettlementTrackerAgent()
        circuit_breakers = CircuitBreakerService()
        execution_agent = ExecutionAgent(config, mode=AutomationMode.PAPER_AUTO)

        return CoordinatorAgent(
            config=config,
            strategy_selector=strategy_selector,
            strategy_pool=strategy_pool,
            risk_manager=risk_manager,
            settlement_tracker=settlement_tracker,
            circuit_breakers=circuit_breakers,
            execution_agent=execution_agent,
            notifier=None,  # No Discord in tests
        )

    @pytest.fixture
    def valid_signal(self):
        """Create valid signal."""
        return Signal(
            symbol="USO",
            direction=SignalDirection.LONG,
            strategy_name="test_strategy",
            timeframe="5m",
            signal_strength=Decimal("80"),
            confidence=Decimal("0.85"),
            timestamp=datetime.now(),
            suggested_entry=Decimal("100.00"),
            suggested_stop=Decimal("98.00"),
            suggested_target=Decimal("105.00"),
        )

    @pytest.mark.asyncio
    async def test_coordinator_initialization(self, coordinator):
        """Test coordinator initializes with all dependencies."""
        assert coordinator.strategy_selector is not None
        assert coordinator.strategy_pool is not None
        assert coordinator.risk_manager is not None
        assert coordinator.settlement_tracker is not None
        assert coordinator.circuit_breakers is not None
        assert coordinator.execution_agent is not None

    @pytest.mark.asyncio
    async def test_evaluate_signal_approved(self, coordinator, valid_signal):
        """Test signal evaluation that gets approved."""
        decision = await coordinator.evaluate_signal(
            signal=valid_signal,
            account_balance=Decimal("10000"),
            current_positions=0,
            daily_trades_count=0,
            consecutive_losses=0,
        )

        assert decision.approved is True
        assert decision.signal == valid_signal
        assert decision.rejection_reason == ""
        assert decision.execution_result is not None
        assert decision.risk_decision is not None
        assert decision.risk_decision["approved"] is True

    @pytest.mark.asyncio
    async def test_evaluate_signal_rejected_by_risk(self, coordinator, valid_signal):
        """Test signal rejected by risk manager."""
        decision = await coordinator.evaluate_signal(
            signal=valid_signal,
            account_balance=Decimal("10000"),
            current_positions=5,  # At max positions
            daily_trades_count=0,
            consecutive_losses=0,
        )

        assert decision.approved is False
        assert decision.signal == valid_signal
        assert "Risk check failed" in decision.rejection_reason
        assert decision.risk_decision is not None
        assert decision.risk_decision["approved"] is False

    @pytest.mark.asyncio
    async def test_evaluate_signal_rejected_by_circuit_breaker(self, coordinator, valid_signal):
        """Test signal rejected by circuit breaker."""
        decision = await coordinator.evaluate_signal(
            signal=valid_signal,
            account_balance=Decimal("10000"),
            current_positions=0,
            daily_trades_count=0,
            consecutive_losses=3,  # Will trip circuit breaker
        )

        assert decision.approved is False
        assert "Circuit breaker" in decision.rejection_reason
        assert decision.breaker_status is not None
        assert decision.breaker_status["is_tripped"] is True

    @pytest.mark.asyncio
    async def test_run_trading_cycle_with_circuit_breaker(self, coordinator):
        """Test trading cycle stops at circuit breaker."""
        decision = await coordinator.run_trading_cycle(
            market_data={},
            account_balance=Decimal("10000"),
            current_positions=0,
            daily_trades_count=0,
            consecutive_losses=3,  # Trip breaker
            daily_pnl_pct=Decimal("0.0"),
        )

        assert decision.approved is False
        assert "Circuit breaker" in decision.rejection_reason

    @pytest.mark.asyncio
    async def test_run_trading_cycle_no_signals(self, coordinator):
        """Test trading cycle with no signals generated."""
        decision = await coordinator.run_trading_cycle(
            market_data={},
            account_balance=Decimal("10000"),
            current_positions=0,
            daily_trades_count=0,
            consecutive_losses=0,
            daily_pnl_pct=Decimal("0.0"),
        )

        # Should pass circuit breakers but have no signals/data
        assert decision.approved is False
        assert decision.rejection_reason != ""


class TestCoordinatorIntegration:
    """Test full coordinator workflow integration."""

    @pytest.fixture
    def full_coordinator(self):
        """Create fully configured coordinator."""
        config = TradingConfig()
        strategy_selector = StrategySelectorAgent(config)
        strategy_pool = StrategyPoolAgent()
        risk_manager = RiskManagerAgent(config)
        settlement_tracker = SettlementTrackerAgent()
        circuit_breakers = CircuitBreakerService()
        execution_agent = ExecutionAgent(config, mode=AutomationMode.PAPER_AUTO)

        return CoordinatorAgent(
            config=config,
            strategy_selector=strategy_selector,
            strategy_pool=strategy_pool,
            risk_manager=risk_manager,
            settlement_tracker=settlement_tracker,
            circuit_breakers=circuit_breakers,
            execution_agent=execution_agent,
            notifier=None,
        )

    @pytest.mark.asyncio
    async def test_complete_workflow_approval(self, full_coordinator):
        """Test complete workflow from signal to execution."""
        signal = Signal(
            symbol="USO",
            direction=SignalDirection.LONG,
            strategy_name="ema_crossover",
            timeframe="5m",
            signal_strength=Decimal("85"),
            confidence=Decimal("0.9"),
            timestamp=datetime.now(),
            suggested_entry=Decimal("100.00"),
            suggested_stop=Decimal("98.00"),
            suggested_target=Decimal("105.00"),
        )

        # Evaluate signal through complete pipeline
        decision = await full_coordinator.evaluate_signal(
            signal=signal,
            account_balance=Decimal("50000"),
            current_positions=0,
            daily_trades_count=0,
            consecutive_losses=0,
        )

        # Verify complete approval path
        assert decision.approved is True
        assert decision.signal is not None
        assert decision.execution_result is not None
        assert decision.risk_decision["approved"] is True
        assert decision.breaker_status["is_tripped"] is False

        # Verify position sizing was calculated
        assert "position_size" in decision.risk_decision
        position_size = Decimal(decision.risk_decision["position_size"])
        assert position_size > 0

        # Verify execution happened
        assert decision.execution_result["decision"] == "EXECUTE"
        assert decision.execution_result["order_id"] is not None

    @pytest.mark.asyncio
    async def test_complete_workflow_rejection_cascade(self, full_coordinator):
        """Test rejection cascades properly through pipeline."""
        signal = Signal(
            symbol="USO",
            direction=SignalDirection.LONG,
            strategy_name="test",
            timeframe="5m",
            signal_strength=Decimal("75"),
            confidence=Decimal("0.8"),
            timestamp=datetime.now(),
            suggested_entry=Decimal("100.00"),
            suggested_stop=Decimal("98.00"),
            suggested_target=Decimal("105.00"),
        )

        # Evaluate with conditions that will fail
        decision = await full_coordinator.evaluate_signal(
            signal=signal,
            account_balance=Decimal("100"),  # Very low balance
            current_positions=0,
            daily_trades_count=0,
            consecutive_losses=0,
        )

        # Should be rejected by risk manager (insufficient funds)
        assert decision.approved is False
        assert "Risk check failed" in decision.rejection_reason
        assert decision.execution_result is None  # Never reached execution

    @pytest.mark.asyncio
    async def test_shutdown(self, full_coordinator):
        """Test graceful shutdown."""
        await full_coordinator.shutdown()
        # Should complete without errors
