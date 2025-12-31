"""Strategy Pool Agent - manages and executes multiple trading strategies."""

import logging
from typing import Any

import pandas as pd

from src.core.config import MarketRegime
from src.strategies import (
    BaseStrategy,
    BollingerBandsMeanReversion,
    EMACrossoverStrategy,
    IndicatorSet,
    MACDTrendStrategy,
    RSIOversoldOverbought,
    Signal,
)

logger = logging.getLogger(__name__)


class StrategyPoolAgent:
    """
    Agent responsible for:
    - Managing a pool of available trading strategies
    - Executing strategies on market data
    - Filtering and ranking signals by confidence
    - Aggregating signals from multiple strategies
    """

    def __init__(self):
        """Initialize Strategy Pool Agent with default strategies."""
        self._strategies: list[BaseStrategy] = []
        self._load_default_strategies()

    def _load_default_strategies(self) -> None:
        """Load default set of strategies."""
        self._strategies = [
            # Trend-following
            EMACrossoverStrategy(),
            MACDTrendStrategy(),
            # Mean-reversion
            BollingerBandsMeanReversion(),
            RSIOversoldOverbought(),
        ]
        logger.info(f"Loaded {len(self._strategies)} default strategies")

    def add_strategy(self, strategy: BaseStrategy) -> None:
        """
        Add a custom strategy to the pool.

        Args:
            strategy: Strategy instance to add
        """
        self._strategies.append(strategy)
        logger.info(f"Added strategy: {strategy.get_name()}")

    def remove_strategy(self, strategy_name: str) -> bool:
        """
        Remove a strategy from the pool by name.

        Args:
            strategy_name: Name of strategy to remove

        Returns:
            True if strategy was removed, False if not found
        """
        for i, strat in enumerate(self._strategies):
            if strat.get_name() == strategy_name:
                removed = self._strategies.pop(i)
                logger.info(f"Removed strategy: {removed.get_name()}")
                return True
        return False

    def get_strategies(self) -> list[BaseStrategy]:
        """
        Get all strategies in the pool.

        Returns:
            List of strategy instances
        """
        return self._strategies.copy()

    def get_strategy_by_name(self, name: str) -> BaseStrategy | None:
        """
        Get a specific strategy by name.

        Args:
            name: Strategy name

        Returns:
            Strategy instance or None if not found
        """
        for strat in self._strategies:
            if strat.get_name() == name:
                return strat
        return None

    def execute_all_strategies(
        self,
        symbol: str,
        bars: pd.DataFrame,
        indicators: dict[str, IndicatorSet],
        market_regime: MarketRegime,
    ) -> list[Signal]:
        """
        Execute all strategies on the given market data.

        Args:
            symbol: Stock symbol
            bars: Recent OHLCV bars
            indicators: Multi-timeframe indicators
            market_regime: Current market regime

        Returns:
            List of signals generated (may be empty)
        """
        signals: list[Signal] = []

        for strategy in self._strategies:
            try:
                # Check regime compatibility first
                if not strategy.is_regime_compatible(market_regime):
                    logger.debug(
                        f"Skipping {strategy.get_name()} - incompatible with {market_regime.value}"
                    )
                    continue

                # Execute strategy
                signal = strategy.analyze(symbol, bars, indicators, market_regime)

                if signal is not None:
                    signals.append(signal)
                    logger.info(
                        f"Signal generated: {strategy.get_name()} - {signal.direction.value} "
                        f"(strength={signal.signal_strength}, confidence={signal.confidence})"
                    )

            except Exception as e:
                logger.error(f"Error executing {strategy.get_name()}: {e}", exc_info=True)
                continue

        return signals

    def execute_selected_strategies(
        self,
        strategy_names: list[str],
        symbol: str,
        bars: pd.DataFrame,
        indicators: dict[str, IndicatorSet],
        market_regime: MarketRegime,
    ) -> list[Signal]:
        """
        Execute only specified strategies.

        Args:
            strategy_names: List of strategy names to execute
            symbol: Stock symbol
            bars: Recent OHLCV bars
            indicators: Multi-timeframe indicators
            market_regime: Current market regime

        Returns:
            List of signals generated
        """
        signals: list[Signal] = []

        for name in strategy_names:
            strategy = self.get_strategy_by_name(name)
            if strategy is None:
                logger.warning(f"Strategy not found: {name}")
                continue

            try:
                if not strategy.is_regime_compatible(market_regime):
                    logger.debug(f"Skipping {name} - incompatible with {market_regime.value}")
                    continue

                signal = strategy.analyze(symbol, bars, indicators, market_regime)
                if signal is not None:
                    signals.append(signal)

            except Exception as e:
                logger.error(f"Error executing {name}: {e}", exc_info=True)
                continue

        return signals

    def filter_signals(
        self,
        signals: list[Signal],
        min_confidence: float = 0.6,
        min_strength: float = 50.0,
    ) -> list[Signal]:
        """
        Filter signals by confidence and strength thresholds.

        Args:
            signals: List of signals to filter
            min_confidence: Minimum confidence threshold (0.0-1.0)
            min_strength: Minimum signal strength (0-100)

        Returns:
            Filtered list of signals
        """
        filtered = [
            s
            for s in signals
            if float(s.confidence) >= min_confidence
            and float(s.signal_strength) >= min_strength
        ]

        logger.info(
            f"Filtered {len(filtered)}/{len(signals)} signals "
            f"(confidence>={min_confidence}, strength>={min_strength})"
        )

        return filtered

    def rank_signals(self, signals: list[Signal]) -> list[Signal]:
        """
        Rank signals by a composite score (confidence * strength).

        Args:
            signals: List of signals to rank

        Returns:
            Signals sorted by composite score (highest first)
        """
        scored_signals = [
            (s, float(s.confidence) * float(s.signal_strength)) for s in signals
        ]

        # Sort by score descending
        scored_signals.sort(key=lambda x: x[1], reverse=True)

        ranked = [s for s, score in scored_signals]

        if ranked:
            logger.info(
                f"Top signal: {ranked[0].strategy_name} "
                f"(score={float(ranked[0].confidence) * float(ranked[0].signal_strength):.2f})"
            )

        return ranked

    def get_consensus_signal(
        self, signals: list[Signal], min_consensus: int = 2
    ) -> Signal | None:
        """
        Get consensus signal if multiple strategies agree on direction.

        Args:
            signals: List of signals from different strategies
            min_consensus: Minimum number of agreeing strategies

        Returns:
            Highest-confidence signal if consensus reached, None otherwise
        """
        if len(signals) < min_consensus:
            return None

        # Group by direction
        from collections import defaultdict

        by_direction: dict[str, list[Signal]] = defaultdict(list)
        for signal in signals:
            by_direction[signal.direction.value].append(signal)

        # Find direction with most signals
        max_count = 0
        consensus_direction = None
        for direction, sigs in by_direction.items():
            if len(sigs) > max_count:
                max_count = len(sigs)
                consensus_direction = direction

        # Check if consensus reached
        if max_count < min_consensus:
            logger.info(f"No consensus reached (max agreement: {max_count}/{min_consensus})")
            return None

        # Return highest confidence signal from consensus direction
        consensus_signals = by_direction[consensus_direction]
        best_signal = max(consensus_signals, key=lambda s: float(s.confidence))

        logger.info(
            f"Consensus reached: {consensus_direction} "
            f"({max_count} strategies agree, best={best_signal.strategy_name})"
        )

        return best_signal

    def aggregate_signals(
        self,
        signals: list[Signal],
        aggregation_method: str = "best",
    ) -> list[Signal]:
        """
        Aggregate signals using specified method.

        Args:
            signals: List of signals to aggregate
            aggregation_method: Method to use:
                - "best": Return highest-ranked signal only
                - "consensus": Return consensus signal if available
                - "all": Return all signals (no aggregation)
                - "top_n": Return top 3 signals

        Returns:
            Aggregated list of signals
        """
        if not signals:
            return []

        if aggregation_method == "best":
            ranked = self.rank_signals(signals)
            return [ranked[0]] if ranked else []

        elif aggregation_method == "consensus":
            consensus = self.get_consensus_signal(signals, min_consensus=2)
            return [consensus] if consensus else []

        elif aggregation_method == "top_n":
            ranked = self.rank_signals(signals)
            return ranked[:3]

        elif aggregation_method == "all":
            return self.rank_signals(signals)

        else:
            logger.warning(f"Unknown aggregation method: {aggregation_method}, using 'best'")
            ranked = self.rank_signals(signals)
            return [ranked[0]] if ranked else []

    def get_statistics(self) -> dict[str, Any]:
        """
        Get statistics about the strategy pool.

        Returns:
            Dict with pool statistics
        """
        from collections import Counter

        strategy_types = Counter(s.get_type().value for s in self._strategies)
        strategy_horizons = Counter(s.get_horizon().value for s in self._strategies)

        return {
            "total_strategies": len(self._strategies),
            "strategy_names": [s.get_name() for s in self._strategies],
            "by_type": dict(strategy_types),
            "by_horizon": dict(strategy_horizons),
        }
