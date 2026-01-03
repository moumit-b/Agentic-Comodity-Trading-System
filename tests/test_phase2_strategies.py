"""Integration tests for Phase 2: Strategy Framework."""

from datetime import datetime
from decimal import Decimal

import pytest

from src.agents import StrategyPoolAgent, StrategySelectionContext, StrategySelectorAgent
from src.core.config import MarketRegime
from src.strategies import (
    EMACrossoverStrategy,
    Signal,
    SignalDirection,
    StrategyType,
    TradingHorizon,
)


class TestStrategyBase:
    """Test base strategy functionality."""

    def test_ema_crossover_instantiation(self):
        """Test EMA crossover strategy can be instantiated."""
        strategy = EMACrossoverStrategy()
        assert strategy.get_name() == "EMA_Crossover"
        assert strategy.get_type() == StrategyType.TREND_FOLLOWING
        assert strategy.get_horizon() == TradingHorizon.BOTH

    def test_signal_validation(self):
        """Test Signal dataclass validates inputs."""
        # Valid signal
        signal = Signal(
            symbol="USO",
            direction=SignalDirection.LONG,
            strategy_name="test",
            timeframe="5m",
            signal_strength=Decimal("75"),
            confidence=Decimal("0.8"),
            timestamp=datetime.now(),
        )
        assert signal.signal_strength == Decimal("75")
        assert signal.confidence == Decimal("0.8")

        # Invalid signal strength (>100)
        with pytest.raises(ValueError):
            Signal(
                symbol="USO",
                direction=SignalDirection.LONG,
                strategy_name="test",
                timeframe="5m",
                signal_strength=Decimal("150"),  # Invalid
                confidence=Decimal("0.8"),
                timestamp=datetime.now(),
            )

        # Invalid confidence (>1.0)
        with pytest.raises(ValueError):
            Signal(
                symbol="USO",
                direction=SignalDirection.LONG,
                strategy_name="test",
                timeframe="5m",
                signal_strength=Decimal("75"),
                confidence=Decimal("1.5"),  # Invalid
                timestamp=datetime.now(),
            )


class TestStrategyPool:
    """Test Strategy Pool Agent."""

    def test_pool_initialization(self):
        """Test strategy pool initializes with default strategies."""
        pool = StrategyPoolAgent()
        stats = pool.get_statistics()

        assert stats["total_strategies"] == 4
        assert stats["by_type"]["TREND_FOLLOWING"] == 2
        assert stats["by_type"]["MEAN_REVERSION"] == 2

    def test_add_remove_strategy(self):
        """Test adding and removing strategies."""
        pool = StrategyPoolAgent()
        initial_count = len(pool.get_strategies())

        # Add custom strategy
        custom = EMACrossoverStrategy()
        pool.add_strategy(custom)
        assert len(pool.get_strategies()) == initial_count + 1

        # Remove strategy
        pool.remove_strategy("EMA_Crossover")
        # Should still have 1 EMA_Crossover (the one we added)
        assert pool.get_strategy_by_name("EMA_Crossover") is not None

    def test_filter_signals(self):
        """Test signal filtering."""
        pool = StrategyPoolAgent()

        # Create test signals
        signals = [
            Signal(
                symbol="USO",
                direction=SignalDirection.LONG,
                strategy_name="test1",
                timeframe="5m",
                signal_strength=Decimal("80"),
                confidence=Decimal("0.7"),
                timestamp=datetime.now(),
            ),
            Signal(
                symbol="USO",
                direction=SignalDirection.LONG,
                strategy_name="test2",
                timeframe="5m",
                signal_strength=Decimal("40"),  # Below threshold
                confidence=Decimal("0.5"),  # Below threshold
                timestamp=datetime.now(),
            ),
        ]

        filtered = pool.filter_signals(signals, min_confidence=0.6, min_strength=50.0)
        assert len(filtered) == 1
        assert filtered[0].strategy_name == "test1"

    def test_rank_signals(self):
        """Test signal ranking."""
        pool = StrategyPoolAgent()

        signals = [
            Signal(
                symbol="USO",
                direction=SignalDirection.LONG,
                strategy_name="low",
                timeframe="5m",
                signal_strength=Decimal("50"),
                confidence=Decimal("0.6"),
                timestamp=datetime.now(),
            ),
            Signal(
                symbol="USO",
                direction=SignalDirection.LONG,
                strategy_name="high",
                timeframe="5m",
                signal_strength=Decimal("80"),
                confidence=Decimal("0.9"),
                timestamp=datetime.now(),
            ),
        ]

        ranked = pool.rank_signals(signals)
        assert len(ranked) == 2
        assert ranked[0].strategy_name == "high"  # Higher score
        assert ranked[1].strategy_name == "low"

    def test_consensus_signal(self):
        """Test consensus signal detection."""
        pool = StrategyPoolAgent()

        # All agree on LONG
        signals = [
            Signal(
                symbol="USO",
                direction=SignalDirection.LONG,
                strategy_name="s1",
                timeframe="5m",
                signal_strength=Decimal("70"),
                confidence=Decimal("0.7"),
                timestamp=datetime.now(),
            ),
            Signal(
                symbol="USO",
                direction=SignalDirection.LONG,
                strategy_name="s2",
                timeframe="5m",
                signal_strength=Decimal("60"),
                confidence=Decimal("0.8"),  # Higher confidence
                timestamp=datetime.now(),
            ),
        ]

        consensus = pool.get_consensus_signal(signals, min_consensus=2)
        assert consensus is not None
        assert consensus.direction == SignalDirection.LONG
        assert consensus.strategy_name == "s2"  # Higher confidence


class TestStrategySelector:
    """Test Strategy Selector Agent."""

    def test_selector_initialization(self):
        """Test strategy selector initializes correctly."""
        selector = StrategySelectorAgent()
        assert selector.max_positions == 2
        assert selector.max_portfolio_heat == Decimal("0.05")

    def test_select_strategies_trending(self):
        """Test strategy selection in TRENDING market."""
        selector = StrategySelectorAgent()
        context = StrategySelectionContext(
            symbol="USO",
            market_regime=MarketRegime.TRENDING,
            time_until_close_minutes=180,
            current_positions=0,
            portfolio_heat=Decimal("0.01"),
            daily_pnl_pct=Decimal("0.0"),
            volatility=Decimal("0.02"),
        )

        decision = selector.select_strategies(context)
        assert decision.should_trade is True
        assert "EMA_Crossover" in decision.selected_strategy_names
        assert "MACD_Trend" in decision.selected_strategy_names

    def test_select_strategies_ranging(self):
        """Test strategy selection in RANGING market."""
        selector = StrategySelectorAgent()
        context = StrategySelectionContext(
            symbol="USO",
            market_regime=MarketRegime.RANGING,
            time_until_close_minutes=180,
            current_positions=0,
            portfolio_heat=Decimal("0.01"),
            daily_pnl_pct=Decimal("0.0"),
            volatility=Decimal("0.02"),
        )

        decision = selector.select_strategies(context)
        assert decision.should_trade is True
        assert "BollingerBands_MeanReversion" in decision.selected_strategy_names
        assert "RSI_OversoldOverbought" in decision.selected_strategy_names

    def test_block_trading_max_positions(self):
        """Test trading blocked when max positions reached."""
        selector = StrategySelectorAgent(max_positions=2)
        context = StrategySelectionContext(
            symbol="USO",
            market_regime=MarketRegime.TRENDING,
            time_until_close_minutes=180,
            current_positions=2,  # At max
            portfolio_heat=Decimal("0.01"),
            daily_pnl_pct=Decimal("0.0"),
            volatility=Decimal("0.02"),
        )

        decision = selector.select_strategies(context)
        assert decision.should_trade is False
        assert "Max positions" in decision.reasoning

    def test_block_trading_high_heat(self):
        """Test trading blocked when portfolio heat too high."""
        selector = StrategySelectorAgent(max_portfolio_heat=Decimal("0.05"))
        context = StrategySelectionContext(
            symbol="USO",
            market_regime=MarketRegime.TRENDING,
            time_until_close_minutes=180,
            current_positions=0,
            portfolio_heat=Decimal("0.06"),  # Above max
            daily_pnl_pct=Decimal("0.0"),
            volatility=Decimal("0.02"),
        )

        decision = selector.select_strategies(context)
        assert decision.should_trade is False
        assert "Portfolio heat" in decision.reasoning

    def test_block_trading_near_close(self):
        """Test trading blocked when too close to market close."""
        selector = StrategySelectorAgent(no_new_trades_after_minutes=30)
        context = StrategySelectionContext(
            symbol="USO",
            market_regime=MarketRegime.TRENDING,
            time_until_close_minutes=20,  # Less than threshold
            current_positions=0,
            portfolio_heat=Decimal("0.01"),
            daily_pnl_pct=Decimal("0.0"),
            volatility=Decimal("0.02"),
        )

        decision = selector.select_strategies(context)
        assert decision.should_trade is False
        assert "close to market close" in decision.reasoning

    def test_force_intraday_near_close(self):
        """Test horizon forced to INTRADAY near market close."""
        selector = StrategySelectorAgent()
        context = StrategySelectionContext(
            symbol="USO",
            market_regime=MarketRegime.TRENDING,
            time_until_close_minutes=45,  # Less than 1 hour
            current_positions=0,
            portfolio_heat=Decimal("0.01"),
            daily_pnl_pct=Decimal("0.0"),
            volatility=Decimal("0.02"),
        )

        decision = selector.select_strategies(context)
        assert decision.preferred_horizon == TradingHorizon.INTRADAY

    def test_exit_intraday_positions(self):
        """Test intraday position exit logic."""
        selector = StrategySelectorAgent(intraday_exit_minutes=5)

        # Should exit
        should_exit, reason = selector.should_exit_intraday_positions(3)
        assert should_exit is True
        assert "closing" in reason.lower()

        # Should not exit
        should_exit, reason = selector.should_exit_intraday_positions(10)
        assert should_exit is False


class TestIntegration:
    """Test full integration of Phase 2 components."""

    def test_full_workflow(self):
        """Test complete strategy workflow: selector -> pool -> signals."""
        # Initialize agents
        selector = StrategySelectorAgent()
        pool = StrategyPoolAgent()

        # Create context
        context = StrategySelectionContext(
            symbol="USO",
            market_regime=MarketRegime.TRENDING,
            time_until_close_minutes=120,
            current_positions=0,
            portfolio_heat=Decimal("0.02"),
            daily_pnl_pct=Decimal("0.01"),
            volatility=Decimal("0.025"),
        )

        # Select strategies
        decision = selector.select_strategies(context)
        assert decision.should_trade is True

        # Verify selected strategies exist in pool
        for strategy_name in decision.selected_strategy_names:
            strategy = pool.get_strategy_by_name(strategy_name)
            assert strategy is not None
            assert strategy.is_regime_compatible(context.market_regime)
