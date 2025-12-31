"""Integration tests for Phase 3: Risk & Settlement."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from src.agents import RiskDecision, RiskManagerAgent, SettlementTrackerAgent
from src.core.config import TradingConfig
from src.services import CircuitBreakerService, CircuitBreakerType
from src.strategies import Signal, SignalDirection, TradingHorizon


class TestRiskManager:
    """Test Risk Manager Agent."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return TradingConfig(
            risk_per_trade_pct=Decimal("0.01"),
            max_risk_per_trade_pct=Decimal("0.02"),
            max_portfolio_heat_pct=Decimal("0.05"),
            max_positions=2,
            max_trades_per_day=10,
            max_consecutive_losses=3,
        )

    @pytest.fixture
    def risk_manager(self, config):
        """Create risk manager instance."""
        return RiskManagerAgent(config)

    @pytest.fixture
    def valid_signal(self):
        """Create valid test signal."""
        return Signal(
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

    @pytest.mark.asyncio
    async def test_position_sizing(self, risk_manager, valid_signal):
        """Test position size calculation."""
        account_balance = Decimal("10000")
        position_size, risk_amount, risk_pct = risk_manager._calculate_position_size(
            valid_signal, account_balance
        )

        # Risk per share = 100 - 98 = 2
        # Max risk = 10000 * 0.01 = 100
        # Position size = 100 / 2 = 50 shares
        # BUT: 25% portfolio cap = 2500, so max position = 2500/100 = 25 shares
        assert position_size == Decimal("25")
        assert risk_amount == Decimal("50")  # 25 shares * $2 risk per share
        assert risk_pct == Decimal("0.005")  # $50 / $10000

    @pytest.mark.asyncio
    async def test_approve_valid_trade(self, risk_manager, valid_signal):
        """Test trade approval for valid conditions."""
        decision = await risk_manager.evaluate_trade(
            signal=valid_signal,
            account_balance=Decimal("10000"),
            settled_cash=Decimal("10000"),
            current_positions=0,
            portfolio_heat=Decimal("0.0"),
            daily_trades_count=0,
            consecutive_losses=0,
        )

        assert decision.approved is True
        assert decision.position_size > 0
        assert decision.risk_pct <= Decimal("0.02")
        assert all(decision.passed_checks.values())

    @pytest.mark.asyncio
    async def test_reject_max_positions(self, risk_manager, valid_signal):
        """Test rejection when max positions reached."""
        decision = await risk_manager.evaluate_trade(
            signal=valid_signal,
            account_balance=Decimal("10000"),
            settled_cash=Decimal("10000"),
            current_positions=2,  # At max
            portfolio_heat=Decimal("0.0"),
            daily_trades_count=0,
            consecutive_losses=0,
        )

        assert decision.approved is False
        assert "Max positions" in decision.reason
        assert decision.passed_checks["position_limit"] is False

    @pytest.mark.asyncio
    async def test_reject_high_portfolio_heat(self, risk_manager, valid_signal):
        """Test rejection when portfolio heat too high."""
        decision = await risk_manager.evaluate_trade(
            signal=valid_signal,
            account_balance=Decimal("10000"),
            settled_cash=Decimal("10000"),
            current_positions=0,
            portfolio_heat=Decimal("0.05"),  # At max
            daily_trades_count=0,
            consecutive_losses=0,
        )

        assert decision.approved is False
        assert "Portfolio heat" in decision.reason
        assert decision.passed_checks["portfolio_heat"] is False

    @pytest.mark.asyncio
    async def test_reject_insufficient_cash(self, risk_manager, valid_signal):
        """Test rejection when insufficient settled cash."""
        decision = await risk_manager.evaluate_trade(
            signal=valid_signal,
            account_balance=Decimal("10000"),
            settled_cash=Decimal("100"),  # Not enough
            current_positions=0,
            portfolio_heat=Decimal("0.0"),
            daily_trades_count=0,
            consecutive_losses=0,
        )

        assert decision.approved is False
        assert "settled cash" in decision.reason
        assert decision.passed_checks["settled_cash"] is False

    @pytest.mark.asyncio
    async def test_reject_consecutive_losses(self, risk_manager, valid_signal):
        """Test rejection after max consecutive losses."""
        decision = await risk_manager.evaluate_trade(
            signal=valid_signal,
            account_balance=Decimal("10000"),
            settled_cash=Decimal("10000"),
            current_positions=0,
            portfolio_heat=Decimal("0.0"),
            daily_trades_count=0,
            consecutive_losses=3,  # At max
        )

        assert decision.approved is False
        assert "consecutive losses" in decision.reason
        assert decision.passed_checks["consecutive_losses"] is False

    def test_risk_reward_validation(self, risk_manager, valid_signal):
        """Test risk/reward ratio validation."""
        # Valid signal: risk=2, reward=5, ratio=2.5
        is_valid, ratio = risk_manager.validate_risk_reward_ratio(
            valid_signal, min_ratio=Decimal("1.5")
        )
        assert is_valid is True
        assert ratio == Decimal("2.5")

        # Test with higher threshold
        is_valid, ratio = risk_manager.validate_risk_reward_ratio(
            valid_signal, min_ratio=Decimal("3.0")
        )
        assert is_valid is False
        assert ratio == Decimal("2.5")


class TestSettlementTracker:
    """Test Settlement Tracker Agent."""

    @pytest.fixture
    def tracker(self):
        """Create settlement tracker instance."""
        return SettlementTrackerAgent()

    @pytest.mark.asyncio
    async def test_record_settlement(self, tracker):
        """Test recording a new settlement."""
        trade_date = date.today()
        settlement = await tracker.record_trade_settlement(
            trade_id="TEST001",
            symbol="USO",
            cash_amount=Decimal("5000"),
            trade_date=trade_date,
        )

        assert settlement.trade_id == "TEST001"
        assert settlement.symbol == "USO"
        assert settlement.cash_amount == Decimal("5000")
        assert settlement.settlement_date == trade_date + timedelta(days=1)
        assert settlement.is_settled is False

    @pytest.mark.asyncio
    async def test_get_settlement_status_no_pending(self, tracker):
        """Test settlement status with no pending settlements."""
        status = await tracker.get_settlement_status(
            total_cash=Decimal("10000"),
            current_date=date.today(),
        )

        assert status.total_settled == Decimal("10000")
        assert status.total_pending == Decimal("0")
        assert status.available_to_trade == Decimal("10000")
        assert len(status.pending_settlements) == 0

    @pytest.mark.asyncio
    async def test_can_trade_amount(self, tracker):
        """Test checking if sufficient settled cash available."""
        # Enough cash
        can_trade, reason = await tracker.can_trade_amount(
            required_cash=Decimal("5000"),
            total_cash=Decimal("10000"),
        )
        assert can_trade is True
        assert reason == ""


class TestCircuitBreakers:
    """Test Circuit Breaker Service."""

    @pytest.fixture
    def breaker_service(self):
        """Create circuit breaker service."""
        return CircuitBreakerService(
            daily_loss_limit_pct=Decimal("0.03"),
            daily_profit_target_pct=Decimal("0.02"),
            max_consecutive_losses=3,
            max_portfolio_heat_pct=Decimal("0.05"),
        )

    @pytest.mark.asyncio
    async def test_no_breakers_tripped(self, breaker_service):
        """Test when all breakers are clear."""
        status = await breaker_service.check_all_breakers(
            daily_pnl_pct=Decimal("0.01"),
            consecutive_losses=0,
            portfolio_heat=Decimal("0.02"),
        )

        assert status.is_tripped is False
        assert len(status.active_breakers) == 0
        assert status.can_trade is True

    @pytest.mark.asyncio
    async def test_daily_loss_limit_breaker(self, breaker_service):
        """Test daily loss limit breaker."""
        status = await breaker_service.check_all_breakers(
            daily_pnl_pct=Decimal("-0.04"),  # Below -3%
            consecutive_losses=0,
            portfolio_heat=Decimal("0.02"),
        )

        assert status.is_tripped is True
        assert CircuitBreakerType.DAILY_LOSS_LIMIT in status.active_breakers
        assert status.can_trade is False
        assert "Daily loss limit" in status.reasons[0]

    @pytest.mark.asyncio
    async def test_daily_profit_target_breaker(self, breaker_service):
        """Test daily profit target breaker (stop on green)."""
        status = await breaker_service.check_all_breakers(
            daily_pnl_pct=Decimal("0.025"),  # Above 2%
            consecutive_losses=0,
            portfolio_heat=Decimal("0.02"),
        )

        assert status.is_tripped is True
        assert CircuitBreakerType.DAILY_PROFIT_TARGET in status.active_breakers
        assert status.can_trade is False
        assert "profit target" in status.reasons[0]

    @pytest.mark.asyncio
    async def test_consecutive_losses_breaker(self, breaker_service):
        """Test consecutive losses breaker."""
        status = await breaker_service.check_all_breakers(
            daily_pnl_pct=Decimal("0.0"),
            consecutive_losses=3,  # At max
            portfolio_heat=Decimal("0.02"),
        )

        assert status.is_tripped is True
        assert CircuitBreakerType.CONSECUTIVE_LOSSES in status.active_breakers
        assert status.can_trade is False

    @pytest.mark.asyncio
    async def test_portfolio_heat_breaker(self, breaker_service):
        """Test portfolio heat breaker."""
        status = await breaker_service.check_all_breakers(
            daily_pnl_pct=Decimal("0.0"),
            consecutive_losses=0,
            portfolio_heat=Decimal("0.06"),  # Above 5%
        )

        assert status.is_tripped is True
        assert CircuitBreakerType.PORTFOLIO_HEAT in status.active_breakers
        assert status.can_trade is False

    @pytest.mark.asyncio
    async def test_volatility_spike_breaker(self, breaker_service):
        """Test volatility spike breaker."""
        status = await breaker_service.check_all_breakers(
            daily_pnl_pct=Decimal("0.0"),
            consecutive_losses=0,
            portfolio_heat=Decimal("0.02"),
            current_volatility=Decimal("0.08"),
            baseline_volatility=Decimal("0.02"),  # 300% increase
        )

        assert status.is_tripped is True
        assert CircuitBreakerType.VOLATILITY_SPIKE in status.active_breakers
        assert status.can_trade is False

    @pytest.mark.asyncio
    async def test_stale_data_breaker(self, breaker_service):
        """Test stale data breaker."""
        old_update = datetime.now() - timedelta(minutes=15)  # 15 min old

        status = await breaker_service.check_all_breakers(
            daily_pnl_pct=Decimal("0.0"),
            consecutive_losses=0,
            portfolio_heat=Decimal("0.02"),
            last_data_update=old_update,
        )

        assert status.is_tripped is True
        assert CircuitBreakerType.STALE_DATA in status.active_breakers
        assert status.can_trade is False

    @pytest.mark.asyncio
    async def test_multiple_breakers(self, breaker_service):
        """Test multiple breakers tripping simultaneously."""
        status = await breaker_service.check_all_breakers(
            daily_pnl_pct=Decimal("-0.04"),  # Loss limit
            consecutive_losses=3,  # Consecutive losses
            portfolio_heat=Decimal("0.06"),  # Portfolio heat
        )

        assert status.is_tripped is True
        assert len(status.active_breakers) == 3
        assert status.can_trade is False

    @pytest.mark.asyncio
    async def test_kill_switch(self, breaker_service):
        """Test manual kill switch."""
        # Activate kill switch
        await breaker_service.activate_kill_switch("Test activation")

        # Check if active
        status = await breaker_service.check_all_breakers(
            daily_pnl_pct=Decimal("0.0"),
            consecutive_losses=0,
            portfolio_heat=Decimal("0.02"),
        )

        assert status.is_tripped is True
        assert CircuitBreakerType.MANUAL_KILL_SWITCH in status.active_breakers

        # Clear kill switch
        cleared = await breaker_service.clear_kill_switch()
        assert cleared is True

        # Check if cleared
        status = await breaker_service.check_all_breakers(
            daily_pnl_pct=Decimal("0.0"),
            consecutive_losses=0,
            portfolio_heat=Decimal("0.02"),
        )

        assert status.is_tripped is False


class TestIntegration:
    """Test integration of Phase 3 components."""

    @pytest.mark.asyncio
    async def test_full_risk_workflow(self):
        """Test complete risk validation workflow."""
        config = TradingConfig()
        risk_manager = RiskManagerAgent(config)
        tracker = SettlementTrackerAgent()
        breaker_service = CircuitBreakerService()

        # Create signal
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

        # Check circuit breakers
        breaker_status = await breaker_service.check_all_breakers(
            daily_pnl_pct=Decimal("0.01"),
            consecutive_losses=0,
            portfolio_heat=Decimal("0.02"),
        )
        assert breaker_status.can_trade is True

        # Check settlement status
        settlement_status = await tracker.get_settlement_status(total_cash=Decimal("10000"))
        assert settlement_status.available_to_trade > 0

        # Evaluate trade with risk manager
        risk_decision = await risk_manager.evaluate_trade(
            signal=signal,
            account_balance=Decimal("10000"),
            settled_cash=settlement_status.available_to_trade,
            current_positions=0,
            portfolio_heat=Decimal("0.0"),
            daily_trades_count=0,
            consecutive_losses=0,
        )

        assert risk_decision.approved is True
        assert risk_decision.position_size > 0

    @pytest.mark.asyncio
    async def test_risk_rejection_cascade(self):
        """Test that risk checks cascade properly."""
        config = TradingConfig(max_positions=1)
        risk_manager = RiskManagerAgent(config)

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

        # Should reject when max positions reached
        decision = await risk_manager.evaluate_trade(
            signal=signal,
            account_balance=Decimal("10000"),
            settled_cash=Decimal("10000"),
            current_positions=1,  # At max
            portfolio_heat=Decimal("0.0"),
            daily_trades_count=0,
            consecutive_losses=0,
        )

        assert decision.approved is False
        assert "Max positions" in decision.reason
