"""Trend-following trading strategies."""

from datetime import datetime
from decimal import Decimal

import pandas as pd

from src.core.config import MarketRegime
from src.strategies.base import (
    BaseStrategy,
    IndicatorSet,
    Signal,
    SignalDirection,
    StrategyType,
    TradingHorizon,
)


class EMACrossoverStrategy(BaseStrategy):
    """
    EMA Crossover trend-following strategy.

    Entry Signals:
    - LONG: Fast EMA crosses above slow EMA + RSI > 50
    - SHORT: Fast EMA crosses below slow EMA + RSI < 50

    Best in: TRENDING markets
    Horizon: BOTH (intraday or swing based on trend strength)
    """

    def __init__(self, min_confidence: Decimal = Decimal("0.65")):
        """Initialize EMA crossover strategy."""
        super().__init__(min_confidence)

    def get_name(self) -> str:
        """Get strategy name."""
        return "EMA_Crossover"

    def get_type(self) -> StrategyType:
        """Get strategy type."""
        return StrategyType.TREND_FOLLOWING

    def get_horizon(self) -> TradingHorizon:
        """Get trading horizon."""
        return TradingHorizon.BOTH

    def is_regime_compatible(self, regime: MarketRegime) -> bool:
        """EMA crossover works best in TRENDING markets."""
        return regime in [MarketRegime.TRENDING, MarketRegime.UNKNOWN]

    def analyze(
        self,
        symbol: str,
        bars: pd.DataFrame,
        indicators: dict[str, IndicatorSet],
        market_regime: MarketRegime,
    ) -> Signal | None:
        """Analyze for EMA crossover signals."""
        if bars.empty or len(bars) < 20:
            return None

        # Use 15m timeframe as primary
        primary_tf = "15m"
        if primary_tf not in indicators:
            return None

        primary_ind = indicators[primary_tf]
        if not primary_ind.is_complete:
            return None

        current_price = Decimal(str(bars["close"].iloc[-1]))
        ema_20 = primary_ind.ema_20
        sma_20 = primary_ind.sma_20
        rsi = primary_ind.rsi
        atr = Decimal(str(primary_ind.atr)) if primary_ind.atr else Decimal("0")

        if not all([ema_20, sma_20, rsi, atr > 0]):
            return None

        # Check for crossover (using SMA and EMA as fast/slow)
        direction = None
        signal_strength_base = 0.0

        # LONG: EMA > SMA (uptrend) + RSI > 50
        if ema_20 > sma_20 and rsi > 50:
            direction = SignalDirection.LONG
            # Strength based on distance and RSI
            ema_distance = ((ema_20 - sma_20) / sma_20) * 100
            signal_strength_base = min(ema_distance * 200 + (rsi - 50), 85)

        # SHORT: EMA < SMA (downtrend) + RSI < 50
        elif ema_20 < sma_20 and rsi < 50:
            direction = SignalDirection.SHORT
            ema_distance = ((sma_20 - ema_20) / sma_20) * 100
            signal_strength_base = min(ema_distance * 200 + (50 - rsi), 85)

        if direction is None:
            return None

        # Calculate confirmations
        confirmations = []

        # Multi-timeframe confirmation
        if "1h" in indicators:
            ind_1h = indicators["1h"]
            if ind_1h.ema_20 and ind_1h.sma_20:
                if direction == SignalDirection.LONG:
                    confirmations.append(ind_1h.ema_20 > ind_1h.sma_20)
                else:
                    confirmations.append(ind_1h.ema_20 < ind_1h.sma_20)

        # MACD confirmation
        if primary_ind.macd and primary_ind.macd_signal:
            if direction == SignalDirection.LONG:
                confirmations.append(primary_ind.macd > primary_ind.macd_signal)
            else:
                confirmations.append(primary_ind.macd < primary_ind.macd_signal)

        # Volume confirmation (simple: check if recent volume is above average)
        volume_confirmation = False
        if len(bars) >= 20:
            avg_volume = bars["volume"].tail(20).mean()
            recent_volume = bars["volume"].iloc[-1]
            volume_confirmation = recent_volume > avg_volume * 1.1

        # Calculate final signal strength
        signal_strength = self.calculate_signal_strength(signal_strength_base, confirmations)

        # Calculate confidence
        regime_compatible = self.is_regime_compatible(market_regime)
        multi_tf_agreement = len([c for c in confirmations if c]) >= 1
        confidence = self.calculate_confidence(
            signal_strength, regime_compatible, volume_confirmation, multi_tf_agreement
        )

        # Filter by minimum confidence
        if confidence < self.min_confidence:
            return None

        # Calculate entry, stop, and target
        suggested_entry = current_price
        suggested_stop = self.calculate_stop_loss(suggested_entry, direction, atr, Decimal("2.0"))
        suggested_target = self.calculate_take_profit(
            suggested_entry, suggested_stop, direction, Decimal("2.5")
        )

        # Determine horizon based on trend strength
        horizon = TradingHorizon.SWING if signal_strength > 70 else TradingHorizon.INTRADAY

        # Build reasoning
        reasoning = (
            f"EMA({ema_20:.2f}) {'>' if direction == SignalDirection.LONG else '<'} "
            f"SMA({sma_20:.2f}), RSI({rsi:.1f}), "
            f"MACD {'bullish' if (primary_ind.macd or 0) > (primary_ind.macd_signal or 0) else 'bearish'}, "
            f"Confirmations: {len([c for c in confirmations if c])}/{len(confirmations)}"
        )

        return Signal(
            symbol=symbol,
            direction=direction,
            strategy_name=self.get_name(),
            timeframe=primary_tf,
            signal_strength=signal_strength,
            confidence=confidence,
            timestamp=datetime.now(),
            suggested_entry=suggested_entry,
            suggested_stop=suggested_stop,
            suggested_target=suggested_target,
            market_regime=market_regime,
            horizon=horizon,
            reasoning=reasoning,
        )


class MACDTrendStrategy(BaseStrategy):
    """
    MACD-based trend-following strategy.

    Entry Signals:
    - LONG: MACD crosses above signal line + MACD histogram > 0 + price > EMA20
    - SHORT: MACD crosses below signal line + MACD histogram < 0 + price < EMA20

    Best in: TRENDING markets
    Horizon: INTRADAY
    """

    def __init__(self, min_confidence: Decimal = Decimal("0.60")):
        """Initialize MACD trend strategy."""
        super().__init__(min_confidence)

    def get_name(self) -> str:
        """Get strategy name."""
        return "MACD_Trend"

    def get_type(self) -> StrategyType:
        """Get strategy type."""
        return StrategyType.TREND_FOLLOWING

    def get_horizon(self) -> TradingHorizon:
        """Get trading horizon."""
        return TradingHorizon.INTRADAY

    def is_regime_compatible(self, regime: MarketRegime) -> bool:
        """MACD trend works in TRENDING markets."""
        return regime in [MarketRegime.TRENDING, MarketRegime.UNKNOWN]

    def analyze(
        self,
        symbol: str,
        bars: pd.DataFrame,
        indicators: dict[str, IndicatorSet],
        market_regime: MarketRegime,
    ) -> Signal | None:
        """Analyze for MACD trend signals."""
        if bars.empty or len(bars) < 26:  # MACD needs 26 periods
            return None

        # Use 5m timeframe for intraday precision
        primary_tf = "5m"
        if primary_tf not in indicators:
            return None

        primary_ind = indicators[primary_tf]
        if not all(
            [
                primary_ind.macd is not None,
                primary_ind.macd_signal is not None,
                primary_ind.macd_histogram is not None,
                primary_ind.ema_20 is not None,
                primary_ind.atr is not None,
            ]
        ):
            return None

        current_price = Decimal(str(bars["close"].iloc[-1]))
        macd = primary_ind.macd
        macd_signal = primary_ind.macd_signal
        macd_hist = primary_ind.macd_histogram
        ema_20 = primary_ind.ema_20
        atr = Decimal(str(primary_ind.atr))

        # Determine signal direction
        direction = None
        signal_strength_base = 0.0

        # LONG: MACD > signal + histogram > 0 + price > EMA
        if macd > macd_signal and macd_hist > 0 and current_price > Decimal(str(ema_20)):
            direction = SignalDirection.LONG
            # Strength based on MACD histogram and distance from EMA
            hist_strength = min(abs(macd_hist) * 10, 50)
            ema_strength = min(((float(current_price) - ema_20) / ema_20) * 100, 30)
            signal_strength_base = hist_strength + ema_strength

        # SHORT: MACD < signal + histogram < 0 + price < EMA
        elif macd < macd_signal and macd_hist < 0 and current_price < Decimal(str(ema_20)):
            direction = SignalDirection.SHORT
            hist_strength = min(abs(macd_hist) * 10, 50)
            ema_strength = min(((ema_20 - float(current_price)) / ema_20) * 100, 30)
            signal_strength_base = hist_strength + ema_strength

        if direction is None:
            return None

        # Confirmations
        confirmations = []

        # RSI confirmation
        if primary_ind.rsi:
            if direction == SignalDirection.LONG:
                confirmations.append(30 < primary_ind.rsi < 70)  # Not overbought
            else:
                confirmations.append(30 < primary_ind.rsi < 70)  # Not oversold

        # 15m timeframe confirmation
        if "15m" in indicators:
            ind_15m = indicators["15m"]
            if ind_15m.macd and ind_15m.macd_signal:
                if direction == SignalDirection.LONG:
                    confirmations.append(ind_15m.macd > ind_15m.macd_signal)
                else:
                    confirmations.append(ind_15m.macd < ind_15m.macd_signal)

        # Volume
        volume_confirmation = False
        if len(bars) >= 10:
            avg_volume = bars["volume"].tail(10).mean()
            recent_volume = bars["volume"].iloc[-1]
            volume_confirmation = recent_volume > avg_volume

        # Calculate signal strength
        signal_strength = self.calculate_signal_strength(signal_strength_base, confirmations)

        # Calculate confidence
        regime_compatible = self.is_regime_compatible(market_regime)
        multi_tf_agreement = "15m" in indicators and len(confirmations) > 0
        confidence = self.calculate_confidence(
            signal_strength, regime_compatible, volume_confirmation, multi_tf_agreement
        )

        if confidence < self.min_confidence:
            return None

        # Calculate levels
        suggested_entry = current_price
        suggested_stop = self.calculate_stop_loss(suggested_entry, direction, atr, Decimal("1.5"))
        suggested_target = self.calculate_take_profit(
            suggested_entry, suggested_stop, direction, Decimal("2.0")
        )

        reasoning = (
            f"MACD({macd:.4f}) {'>' if direction == SignalDirection.LONG else '<'} "
            f"Signal({macd_signal:.4f}), Histogram({macd_hist:.4f}), "
            f"Price {'>' if direction == SignalDirection.LONG else '<'} EMA({ema_20:.2f})"
        )

        return Signal(
            symbol=symbol,
            direction=direction,
            strategy_name=self.get_name(),
            timeframe=primary_tf,
            signal_strength=signal_strength,
            confidence=confidence,
            timestamp=datetime.now(),
            suggested_entry=suggested_entry,
            suggested_stop=suggested_stop,
            suggested_target=suggested_target,
            market_regime=market_regime,
            horizon=TradingHorizon.INTRADAY,
            reasoning=reasoning,
        )
