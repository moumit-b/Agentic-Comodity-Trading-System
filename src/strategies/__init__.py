"""Trading strategy modules."""

from .base import BaseStrategy, IndicatorSet, Signal, SignalDirection, StrategyType, TradingHorizon
from .mean_reversion import BollingerBandsMeanReversion, RSIOversoldOverbought
from .trend_following import EMACrossoverStrategy, MACDTrendStrategy

__all__ = [
    # Base
    "BaseStrategy",
    "IndicatorSet",
    "Signal",
    "SignalDirection",
    "StrategyType",
    "TradingHorizon",
    # Trend Following
    "EMACrossoverStrategy",
    "MACDTrendStrategy",
    # Mean Reversion
    "BollingerBandsMeanReversion",
    "RSIOversoldOverbought",
]
