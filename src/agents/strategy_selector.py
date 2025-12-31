"""Strategy Selector Agent - selects appropriate strategies based on market conditions."""

import logging
from datetime import datetime, time
from decimal import Decimal

import pandas as pd

from src.core.config import MarketRegime
from src.strategies import IndicatorSet, StrategyType, TradingHorizon

logger = logging.getLogger(__name__)


class StrategySelectionContext:
    """Context data for strategy selection decisions."""

    def __init__(
        self,
        symbol: str,
        market_regime: MarketRegime,
        time_until_close_minutes: int,
        current_positions: int,
        portfolio_heat: Decimal,
        daily_pnl_pct: Decimal,
        volatility: Decimal,
    ):
        """
        Initialize strategy selection context.

        Args:
            symbol: Stock symbol
            market_regime: Current market regime
            time_until_close_minutes: Minutes until market close
            current_positions: Number of open positions
            portfolio_heat: Current portfolio risk exposure (0.0-1.0)
            daily_pnl_pct: Daily P&L percentage
            volatility: Current market volatility (ATR/price)
        """
        self.symbol = symbol
        self.market_regime = market_regime
        self.time_until_close_minutes = time_until_close_minutes
        self.current_positions = current_positions
        self.portfolio_heat = portfolio_heat
        self.daily_pnl_pct = daily_pnl_pct
        self.volatility = volatility


class StrategySelectionDecision:
    """Decision on which strategies to use and how."""

    def __init__(
        self,
        selected_strategy_names: list[str],
        preferred_horizon: TradingHorizon,
        reasoning: str,
        should_trade: bool = True,
    ):
        """
        Initialize strategy selection decision.

        Args:
            selected_strategy_names: Names of strategies to use
            preferred_horizon: Preferred trading horizon
            reasoning: Explanation for the decision
            should_trade: Whether trading should proceed at all
        """
        self.selected_strategy_names = selected_strategy_names
        self.preferred_horizon = preferred_horizon
        self.reasoning = reasoning
        self.should_trade = should_trade


class StrategySelectorAgent:
    """
    Agent responsible for:
    - Detecting market regime (TRENDING, RANGING, VOLATILE)
    - Selecting appropriate strategies for current conditions
    - Determining preferred trading horizon (INTRADAY, SWING)
    - Making go/no-go trading decisions based on context
    """

    def __init__(
        self,
        max_positions: int = 2,
        max_portfolio_heat: Decimal = Decimal("0.05"),
        no_new_trades_after_minutes: int = 30,  # 30 min before close
        intraday_exit_minutes: int = 5,  # 5 min before close
    ):
        """
        Initialize Strategy Selector Agent.

        Args:
            max_positions: Maximum number of concurrent positions
            max_portfolio_heat: Maximum portfolio risk exposure
            no_new_trades_after_minutes: Stop new trades X minutes before close
            intraday_exit_minutes: Exit intraday positions X minutes before close
        """
        self.max_positions = max_positions
        self.max_portfolio_heat = max_portfolio_heat
        self.no_new_trades_after_minutes = no_new_trades_after_minutes
        self.intraday_exit_minutes = intraday_exit_minutes

    def detect_market_regime(
        self, bars: pd.DataFrame, indicators: dict[str, IndicatorSet]
    ) -> MarketRegime:
        """
        Detect current market regime based on price action and indicators.

        Args:
            bars: Recent OHLCV bars
            indicators: Multi-timeframe indicators

        Returns:
            Market regime (TRENDING, RANGING, VOLATILE, UNKNOWN)
        """
        if bars.empty or len(bars) < 50:
            return MarketRegime.UNKNOWN

        # Use 1h timeframe for regime detection
        if "1h" not in indicators:
            return MarketRegime.UNKNOWN

        ind_1h = indicators["1h"]
        if not ind_1h.is_complete:
            return MarketRegime.UNKNOWN

        current_price = bars["close"].iloc[-1]
        sma_20 = ind_1h.sma_20
        ema_20 = ind_1h.ema_20
        atr = ind_1h.atr
        bb_upper = ind_1h.bb_upper
        bb_lower = ind_1h.bb_lower

        # Calculate metrics
        volatility_pct = (atr / current_price) * 100 if atr and current_price else 0
        distance_from_sma = abs(current_price - sma_20) / sma_20 if sma_20 else 0

        # VOLATILE: High ATR relative to price (>3%)
        if volatility_pct > 3.0:
            logger.info(f"Regime detected: VOLATILE (volatility={volatility_pct:.2f}%)")
            return MarketRegime.VOLATILE

        # TRENDING: Price significantly away from SMA (>2%) + consistent direction
        if distance_from_sma > 0.02:
            # Check if trend is consistent (EMA and SMA aligned)
            if (ema_20 > sma_20 and current_price > ema_20) or (
                ema_20 < sma_20 and current_price < ema_20
            ):
                logger.info(
                    f"Regime detected: TRENDING (distance from SMA={distance_from_sma:.2%})"
                )
                return MarketRegime.TRENDING

        # RANGING: Price oscillating within Bollinger Bands, low trend strength
        if bb_upper and bb_lower:
            bb_width = (bb_upper - bb_lower) / current_price
            price_position = (current_price - bb_lower) / (bb_upper - bb_lower)

            # Wide bands + price in middle = ranging
            if bb_width > 0.03 and 0.3 < price_position < 0.7:
                logger.info(
                    f"Regime detected: RANGING "
                    f"(BB width={bb_width:.2%}, position={price_position:.2f})"
                )
                return MarketRegime.RANGING

        # Default to RANGING if no strong trend or volatility
        logger.info("Regime detected: RANGING (default)")
        return MarketRegime.RANGING

    def select_strategies(self, context: StrategySelectionContext) -> StrategySelectionDecision:
        """
        Select appropriate strategies based on market context.

        Args:
            context: Strategy selection context

        Returns:
            Strategy selection decision
        """
        # Check if trading should proceed at all
        should_trade, blocking_reason = self._check_trading_allowed(context)

        if not should_trade:
            return StrategySelectionDecision(
                selected_strategy_names=[],
                preferred_horizon=TradingHorizon.INTRADAY,
                reasoning=blocking_reason,
                should_trade=False,
            )

        # Select strategies based on market regime
        if context.market_regime == MarketRegime.TRENDING:
            strategies = ["EMA_Crossover", "MACD_Trend"]
            horizon = self._determine_horizon(context, default=TradingHorizon.BOTH)
            reasoning = (
                f"TRENDING market: Using trend-following strategies. Horizon: {horizon.value}"
            )

        elif context.market_regime == MarketRegime.RANGING:
            strategies = ["BollingerBands_MeanReversion", "RSI_OversoldOverbought"]
            horizon = TradingHorizon.INTRADAY  # Mean reversion best intraday
            reasoning = f"RANGING market: Using mean-reversion strategies. Horizon: {horizon.value}"

        elif context.market_regime == MarketRegime.VOLATILE:
            # In volatile markets, avoid trading or use only high-confidence setups
            if context.volatility > Decimal("0.04"):  # Very high volatility (>4%)
                return StrategySelectionDecision(
                    selected_strategy_names=[],
                    preferred_horizon=TradingHorizon.INTRADAY,
                    reasoning=f"VOLATILE market (volatility={context.volatility:.2%}): Too risky, staying out",
                    should_trade=False,
                )
            else:
                # Moderate volatility: Use trend-following with caution
                strategies = ["EMA_Crossover"]
                horizon = TradingHorizon.INTRADAY
                reasoning = (
                    f"VOLATILE market (volatility={context.volatility:.2%}): "
                    f"Using single trend-following strategy with INTRADAY horizon"
                )

        else:  # UNKNOWN
            # Conservative approach: use all strategies, let consensus decide
            strategies = [
                "EMA_Crossover",
                "MACD_Trend",
                "BollingerBands_MeanReversion",
                "RSI_OversoldOverbought",
            ]
            horizon = TradingHorizon.INTRADAY
            reasoning = "UNKNOWN market regime: Using all strategies, requiring consensus"

        # Adjust based on time of day
        if context.time_until_close_minutes < 60:
            # Less than 1 hour to close: only intraday strategies
            horizon = TradingHorizon.INTRADAY
            reasoning += f" | {context.time_until_close_minutes}min to close: INTRADAY only"

        logger.info(f"Strategy selection: {strategies} ({reasoning})")

        return StrategySelectionDecision(
            selected_strategy_names=strategies,
            preferred_horizon=horizon,
            reasoning=reasoning,
            should_trade=True,
        )

    def _check_trading_allowed(self, context: StrategySelectionContext) -> tuple[bool, str]:
        """
        Check if trading is allowed given current context.

        Args:
            context: Strategy selection context

        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        # Check position limit
        if context.current_positions >= self.max_positions:
            return (
                False,
                f"Max positions reached ({context.current_positions}/{self.max_positions})",
            )

        # Check portfolio heat
        if context.portfolio_heat >= self.max_portfolio_heat:
            return (
                False,
                f"Portfolio heat too high ({context.portfolio_heat:.2%}/{self.max_portfolio_heat:.2%})",
            )

        # Check time of day
        if context.time_until_close_minutes < self.no_new_trades_after_minutes:
            return (
                False,
                f"Too close to market close ({context.time_until_close_minutes}min remaining)",
            )

        # All checks passed
        return True, ""

    def _determine_horizon(
        self, context: StrategySelectionContext, default: TradingHorizon
    ) -> TradingHorizon:
        """
        Determine preferred trading horizon based on context.

        Args:
            context: Strategy selection context
            default: Default horizon if no strong preference

        Returns:
            Preferred trading horizon
        """
        # Force INTRADAY if close to market close
        if context.time_until_close_minutes < 120:  # Less than 2 hours
            return TradingHorizon.INTRADAY

        # Force INTRADAY if portfolio heat is high (reduce overnight risk)
        if context.portfolio_heat > Decimal("0.03"):
            return TradingHorizon.INTRADAY

        # Force INTRADAY in volatile conditions
        if context.volatility > Decimal("0.03"):
            return TradingHorizon.INTRADAY

        # SWING if strong trend and early in day
        if (
            context.market_regime == MarketRegime.TRENDING
            and context.time_until_close_minutes > 180
            and context.volatility < Decimal("0.025")
        ):
            return TradingHorizon.SWING

        return default

    def should_exit_intraday_positions(self, minutes_until_close: int) -> tuple[bool, str]:
        """
        Check if intraday positions should be exited.

        Args:
            minutes_until_close: Minutes until market close

        Returns:
            Tuple of (should_exit: bool, reason: str)
        """
        if minutes_until_close <= self.intraday_exit_minutes:
            return (
                True,
                f"Market closing in {minutes_until_close} minutes - exiting intraday positions",
            )
        return False, ""

    def calculate_time_until_close(self, current_time: datetime | None = None) -> int:
        """
        Calculate minutes until market close (4:00 PM ET).

        Args:
            current_time: Current datetime (defaults to now)

        Returns:
            Minutes until market close
        """
        if current_time is None:
            current_time = datetime.now()

        # Market close time (4:00 PM)
        market_close = time(16, 0)
        close_datetime = current_time.replace(
            hour=market_close.hour,
            minute=market_close.minute,
            second=0,
            microsecond=0,
        )

        # Calculate difference
        delta = close_datetime - current_time
        minutes = int(delta.total_seconds() / 60)

        return max(0, minutes)  # Don't return negative
