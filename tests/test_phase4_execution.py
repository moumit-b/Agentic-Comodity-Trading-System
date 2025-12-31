"""Integration tests for Phase 4: Execution & Notifications."""

from datetime import datetime
from decimal import Decimal

import pytest

from src.agents import ExecutionAgent, ExecutionDecision
from src.core.config import AutomationMode, TradingConfig
from src.services import DiscordNotifier
from src.strategies import Signal, SignalDirection


class TestExecutionAgent:
    """Test Execution Agent."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return TradingConfig()

    @pytest.fixture
    def signal(self):
        """Create test signal."""
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
    async def test_advisory_mode(self, config, signal):
        """Test ADVISORY mode - no execution."""
        agent = ExecutionAgent(config, mode=AutomationMode.ADVISORY)

        result = await agent.execute_signal(
            signal=signal,
            position_size=Decimal("50"),
            account_balance=Decimal("10000"),
        )

        assert result.decision == ExecutionDecision.ADVISORY_ONLY
        assert result.order_id is None
        assert result.requires_confirmation is False
        assert "ADVISORY" in result.message

    @pytest.mark.asyncio
    async def test_paper_auto_mode(self, config, signal):
        """Test PAPER_AUTO mode - automatic paper execution."""
        agent = ExecutionAgent(config, mode=AutomationMode.PAPER_AUTO)

        result = await agent.execute_signal(
            signal=signal,
            position_size=Decimal("50"),
            account_balance=Decimal("10000"),
        )

        assert result.decision == ExecutionDecision.EXECUTE
        assert result.order_id is not None
        assert result.requires_confirmation is False
        assert "PAPER" in result.message
        assert result.metadata["is_paper"] is True

    @pytest.mark.asyncio
    async def test_live_confirm_mode(self, config, signal):
        """Test LIVE_CONFIRM mode - requires confirmation."""
        agent = ExecutionAgent(config, mode=AutomationMode.LIVE_CONFIRM)

        result = await agent.execute_signal(
            signal=signal,
            position_size=Decimal("50"),
            account_balance=Decimal("10000"),
        )

        assert result.decision == ExecutionDecision.REQUEST_CONFIRMATION
        assert result.order_id is not None
        assert result.requires_confirmation is True
        assert "LIVE-CONFIRM" in result.message

    @pytest.mark.asyncio
    async def test_live_auto_mode(self, config, signal):
        """Test LIVE_AUTO mode - automatic live execution."""
        agent = ExecutionAgent(config, mode=AutomationMode.LIVE_AUTO)

        result = await agent.execute_signal(
            signal=signal,
            position_size=Decimal("50"),
            account_balance=Decimal("10000"),
        )

        assert result.decision == ExecutionDecision.EXECUTE
        assert result.order_id is not None
        assert result.requires_confirmation is False
        assert "LIVE-AUTO" in result.message
        assert result.metadata["is_live"] is True

    @pytest.mark.asyncio
    async def test_get_pending_confirmations(self, config, signal):
        """Test getting pending confirmations."""
        agent = ExecutionAgent(config, mode=AutomationMode.LIVE_CONFIRM)

        # Create pending execution
        result = await agent.execute_signal(
            signal=signal,
            position_size=Decimal("50"),
            account_balance=Decimal("10000"),
        )

        # Get pending confirmations
        pending = await agent.get_pending_confirmations()
        assert len(pending) > 0
        assert pending[0].status == "PENDING"
        assert pending[0].requires_confirmation is True

    @pytest.mark.asyncio
    async def test_confirm_execution(self, config, signal):
        """Test confirming a pending execution."""
        agent = ExecutionAgent(config, mode=AutomationMode.LIVE_CONFIRM)

        # Create pending execution
        result = await agent.execute_signal(
            signal=signal,
            position_size=Decimal("50"),
            account_balance=Decimal("10000"),
        )

        # Confirm it
        exec_id = int(result.order_id)
        confirmed = await agent.confirm_execution(exec_id, confirmed=True, confirmed_by="TEST")

        assert confirmed is True

        # Verify status updated
        pending = await agent.get_pending_confirmations()
        # Should be empty now
        assert not any(p.id == exec_id for p in pending)

    @pytest.mark.asyncio
    async def test_reject_execution(self, config, signal):
        """Test rejecting a pending execution."""
        agent = ExecutionAgent(config, mode=AutomationMode.LIVE_CONFIRM)

        # Create pending execution
        result = await agent.execute_signal(
            signal=signal,
            position_size=Decimal("50"),
            account_balance=Decimal("10000"),
        )

        # Reject it
        exec_id = int(result.order_id)
        rejected = await agent.confirm_execution(exec_id, confirmed=False, confirmed_by="TEST")

        assert rejected is True


class TestDiscordNotifier:
    """Test Discord Notifier."""

    def test_notifier_disabled_when_no_webhook(self):
        """Test that notifier is disabled without webhook URL."""
        notifier = DiscordNotifier(webhook_url=None)
        assert notifier.enabled is False

    def test_notifier_enabled_with_webhook(self):
        """Test that notifier is enabled with webhook URL."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/test")
        assert notifier.enabled is True

    @pytest.mark.asyncio
    async def test_send_alert_when_disabled(self):
        """Test that alerts are skipped when disabled."""
        notifier = DiscordNotifier(webhook_url=None)

        from src.services import AlertLevel, TradeAlert

        alert = TradeAlert(
            level=AlertLevel.INFO,
            title="Test",
            description="Test alert",
            fields={},
            color=0x3498DB,
        )

        result = await notifier.send_alert(alert)
        assert result is False  # Should skip when disabled


class TestIntegration:
    """Test integration of Phase 4 components."""

    @pytest.mark.asyncio
    async def test_full_execution_workflow(self):
        """Test complete execution workflow."""
        config = TradingConfig()
        agent = ExecutionAgent(config, mode=AutomationMode.PAPER_AUTO)

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

        # Execute in paper mode
        result = await agent.execute_signal(
            signal=signal,
            position_size=Decimal("50"),
            account_balance=Decimal("10000"),
        )

        assert result.decision == ExecutionDecision.EXECUTE
        assert result.order_id is not None
        assert "PAPER" in result.message

    @pytest.mark.asyncio
    async def test_confirmation_workflow(self):
        """Test confirmation workflow."""
        config = TradingConfig()
        agent = ExecutionAgent(config, mode=AutomationMode.LIVE_CONFIRM)

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

        # 1. Create execution requiring confirmation
        result = await agent.execute_signal(
            signal=signal,
            position_size=Decimal("50"),
            account_balance=Decimal("10000"),
        )

        assert result.requires_confirmation is True
        exec_id = int(result.order_id)

        # 2. Get pending confirmations
        pending = await agent.get_pending_confirmations()
        assert len(pending) > 0

        # 3. Confirm execution
        confirmed = await agent.confirm_execution(exec_id, confirmed=True)
        assert confirmed is True

        # 4. Verify no longer pending
        pending_after = await agent.get_pending_confirmations()
        assert not any(p.id == exec_id for p in pending_after)
