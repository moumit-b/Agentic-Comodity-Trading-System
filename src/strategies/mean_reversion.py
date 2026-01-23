"""Mean-reversion trading strategies."""

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


class BollingerBandsMeanReversion(BaseStrategy):
    """
    Bollinger Bands mean-reversion strategy.

    Entry Signals:
    - LONG: Price touches or breaks below lower BB + RSI < 30 (oversold)
    - SHORT: Price touches or breaks above upper BB + RSI > 70 (overbought)

    Best in: RANGING markets
    Horizon: INTRADAY (quick reversions)
    """

    def __init__(self, min_confidence: Decimal = Decimal("0.65")):
        """Initialize Bollinger Bands mean-reversion strategy."""
        super().__init__(min_confidence)

    def get_name(self) -> str:
        """Get strategy name."""
        return "BollingerBands_MeanReversion"

    def get_type(self) -> StrategyType:
        """Get strategy type."""
        return StrategyType.MEAN_REVERSION

    def get_horizon(self) -> TradingHorizon:
        """Get trading horizon."""
        return TradingHorizon.INTRADAY

    def is_regime_compatible(self, regime: MarketRegime) -> bool:
        """Mean reversion works best in RANGING markets."""
        return regime in [MarketRegime.RANGING, MarketRegime.UNKNOWN]

    def analyze(
        self,
        symbol: str,
        bars: pd.DataFrame,
        indicators: dict[str, IndicatorSet],
        market_regime: MarketRegime,
    ) -> Signal | None:
        """Analyze for Bollinger Bands mean-reversion signals."""
        if bars.empty or len(bars) < 20:
            return None

        # Use 15m timeframe
        primary_tf = "15m"
        if primary_tf not in indicators:
            return None

        primary_ind = indicators[primary_tf]
        if not all(
            [
                primary_ind.bb_upper is not None,
                primary_ind.bb_middle is not None,
                primary_ind.bb_lower is not None,
                primary_ind.rsi is not None,
                primary_ind.atr is not None,
            ]
        ):
            return None

        current_price = Decimal(str(bars["close"].iloc[-1]))
        bb_upper = Decimal(str(primary_ind.bb_upper))
        bb_middle = Decimal(str(primary_ind.bb_middle))
        bb_lower = Decimal(str(primary_ind.bb_lower))
        rsi = primary_ind.rsi
        atr = Decimal(str(primary_ind.atr))

        # Determine signal direction
        direction = None
        signal_strength_base = 0.0

        # LONG: Price near/below lower BB + RSI oversold
        price_to_lower = (float(current_price) - float(bb_lower)) / float(bb_lower)
        if price_to_lower <= 0.02 and rsi < 35:  # Within 2% of lower BB
            direction = SignalDirection.LONG
            # Strength based on how oversold and how close to BB
            rsi_strength = max(0, 35 - rsi) * 2  # 0-70 points
            bb_strength = max(0, 0.02 - price_to_lower) * 1000  # 0-20 points
            signal_strength_base = min(rsi_strength + bb_strength, 85)

        # SHORT: Price near/above upper BB + RSI overbought
        price_to_upper = (float(bb_upper) - float(current_price)) / float(bb_upper)
        if price_to_upper <= 0.02 and rsi > 65:  # Within 2% of upper BB
            direction = SignalDirection.SHORT
            rsi_strength = max(0, rsi - 65) * 2  # 0-70 points
            bb_strength = max(0, 0.02 - price_to_upper) * 1000  # 0-20 points
            signal_strength_base = min(rsi_strength + bb_strength, 85)

        if direction is None:
            return None

        # Confirmations
        confirmations = []

        # Check if price is reverting (momentum slowing)
        if len(bars) >= 3:
            recent_closes = [float(bars["close"].iloc[i]) for i in range(-3, 0)]
            if direction == SignalDirection.LONG:
                # Price falling but rate of fall slowing
                changes = [recent_closes[i] - recent_closes[i - 1] for i in range(1, 3)]
                confirmations.append(changes[-1] > changes[-2])  # Slowing decline
            else:
                # Price rising but rate of rise slowing
                changes = [recent_closes[i] - recent_closes[i - 1] for i in range(1, 3)]
                confirmations.append(changes[-1] < changes[-2])  # Slowing rise

        # Multi-timeframe: 5m should show extreme too
        if "5m" in indicators:
            ind_5m = indicators["5m"]
            if ind_5m.rsi:
                if direction == SignalDirection.LONG:
                    confirmations.append(ind_5m.rsi < 40)
                else:
                    confirmations.append(ind_5m.rsi > 60)

        # Volume should be above average (panic/euphoria)
        volume_confirmation = False
        if len(bars) >= 20:
            avg_volume = bars["volume"].tail(20).mean()
            recent_volume = bars["volume"].iloc[-1]
            volume_confirmation = recent_volume > avg_volume * 1.2

        # Calculate signal strength
        signal_strength = self.calculate_signal_strength(signal_strength_base, confirmations)

        # Calculate confidence
        regime_compatible = self.is_regime_compatible(market_regime)
        multi_tf_agreement = "5m" in indicators and len([c for c in confirmations if c]) >= 1
        confidence = self.calculate_confidence(
            signal_strength, regime_compatible, volume_confirmation, multi_tf_agreement
        )

        if confidence < self.min_confidence:
            return None

        # Calculate levels - target is middle BB, stop beyond the band
        suggested_entry = current_price
        if direction == SignalDirection.LONG:
            suggested_stop = bb_lower - (atr * Decimal("1.0"))
            suggested_target = bb_middle
        else:
            suggested_stop = bb_upper + (atr * Decimal("1.0"))
            suggested_target = bb_middle

        reasoning = (
            f"Price({current_price:.2f}) near BB "
            f"{'Lower' if direction == SignalDirection.LONG else 'Upper'}"
            f"({bb_lower if direction == SignalDirection.LONG else bb_upper:.2f}), "
            f"RSI({rsi:.1f}) {'oversold' if direction == SignalDirection.LONG else 'overbought'}, "
            f"Target: Middle BB({bb_middle:.2f})"
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


class RSIOversoldOverbought(BaseStrategy):
    """
    Simple RSI oversold/overbought mean-reversion strategy.

    Entry Signals:
    - LONG: RSI < 25 (deeply oversold)
    - SHORT: RSI > 75 (deeply overbought)

    Best in: RANGING markets
    Horizon: INTRADAY
    """

    def __init__(self, min_confidence: Decimal = Decimal("0.60")):
        """Initialize RSI oversold/overbought strategy."""
        super().__init__(min_confidence)

    def get_name(self) -> str:
        """Get strategy name."""
        return "RSI_OversoldOverbought"

    def get_type(self) -> StrategyType:
        """Get strategy type."""
        return StrategyType.MEAN_REVERSION

    def get_horizon(self) -> TradingHorizon:
        """Get trading horizon."""
        return TradingHorizon.INTRADAY

    def is_regime_compatible(self, regime: MarketRegime) -> bool:
        """RSI mean reversion works in RANGING markets."""
        return regime in [MarketRegime.RANGING, MarketRegime.UNKNOWN]

    def analyze(
        self,
        symbol: str,
        bars: pd.DataFrame,
        indicators: dict[str, IndicatorSet],
        market_regime: MarketRegime,
    ) -> Signal | None:
        """Analyze for RSI oversold/overbought signals."""
        if bars.empty or len(bars) < 14:
            return None

        # Use 5m for quick intraday reversions
        primary_tf = "5m"
        if primary_tf not in indicators:
            return None

        primary_ind = indicators[primary_tf]
        if not all([primary_ind.rsi is not None, primary_ind.atr is not None]):
            return None

        current_price = Decimal(str(bars["close"].iloc[-1]))
        rsi = primary_ind.rsi
        atr = Decimal(str(primary_ind.atr))

        # Determine signal direction
        direction = None
        signal_strength_base = 0.0

        # LONG: Deeply oversold (Testing: Relaxed to < 70)
        if rsi < 70:
            direction = SignalDirection.LONG
            signal_strength_base = (70 - rsi) * 1.5  # Adjusted scoring

        # SHORT: Deeply overbought
        elif rsi > 75:
            direction = SignalDirection.SHORT
            signal_strength_base = (rsi - 75) * 3  # 0-75 points

        if direction is None:
            return None

        # Confirmations
        confirmations = []

        # 15m RSI should also show extreme
        if "15m" in indicators:
            ind_15m = indicators["15m"]
            if ind_15m.rsi:
                if direction == SignalDirection.LONG:
                    confirmations.append(ind_15m.rsi < 35)
                else:
                    confirmations.append(ind_15m.rsi > 65)

        # Price near SMA (mean reversion target)
        if primary_ind.sma_20:
            sma_distance = abs(float(current_price) - primary_ind.sma_20) / primary_ind.sma_20
            confirmations.append(sma_distance > 0.01)  # At least 1% from mean

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
        multi_tf_agreement = "15m" in indicators
        confidence = self.calculate_confidence(
            signal_strength, regime_compatible, volume_confirmation, multi_tf_agreement
        )

        if confidence < self.min_confidence:
            return None

        # Calculate levels
        suggested_entry = current_price
        suggested_stop = self.calculate_stop_loss(suggested_entry, direction, atr, Decimal("2.0"))
        suggested_target = self.calculate_take_profit(
            suggested_entry, suggested_stop, direction, Decimal("1.5")
        )

        reasoning = f"RSI({rsi:.1f}) {'deeply oversold' if direction == SignalDirection.LONG else 'deeply overbought'}"

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
