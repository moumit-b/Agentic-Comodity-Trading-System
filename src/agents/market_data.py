"""Market Data Agent for real-time 1-minute bars and multi-timeframe aggregation."""

import asyncio
import logging
from datetime import datetime

import pandas as pd
import pandas_ta as ta
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.models import Bar
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from src.core.config import AlpacaConfig, RedisConfig
from src.core.database import get_session
from src.models.bars import Bar1m, Indicator
from src.services.redis_cache import RedisCache

logger = logging.getLogger(__name__)


class MarketDataAgent:
    """
    Agent responsible for:
    - Streaming 1-minute bars from Alpaca WebSocket
    - Multi-timeframe aggregation (1m → 5m → 15m → 1h → 1d)
    - Technical indicator calculation
    - Market regime detection
    - Caching in Redis and persisting to PostgreSQL
    """

    def __init__(self, alpaca_config: AlpacaConfig, redis_config: RedisConfig):
        """
        Initialize Market Data Agent.

        Args:
            alpaca_config: Alpaca API configuration
            redis_config: Redis cache configuration
        """
        self.alpaca_config = alpaca_config
        self.redis_cache = RedisCache(redis_config)

        # Alpaca clients
        self._stream: StockDataStream | None = None
        self._historical_client: StockHistoricalDataClient | None = None

        # Subscribed symbols
        self._symbols: list[str] = []

        # In-memory buffers for aggregation
        self._bars_1m: dict[str, pd.DataFrame] = {}  # symbol -> DataFrame

    async def connect(self) -> None:
        """Initialize connections to Alpaca WebSocket and Redis."""
        logger.info("Connecting Market Data Agent...")

        # Connect to Redis
        self.redis_cache.connect()

        # Initialize Alpaca historical client
        self._historical_client = StockHistoricalDataClient(
            api_key=self.alpaca_config.api_key.get_secret_value(),
            secret_key=self.alpaca_config.api_secret.get_secret_value(),
        )

        # Initialize Alpaca WebSocket stream
        self._stream = StockDataStream(
            api_key=self.alpaca_config.api_key.get_secret_value(),
            secret_key=self.alpaca_config.api_secret.get_secret_value(),
        )

        logger.info("Market Data Agent connected successfully")

    async def disconnect(self) -> None:
        """Close all connections."""
        logger.info("Disconnecting Market Data Agent...")

        if self._stream:
            await self._stream.stop_ws()
            self._stream = None

        self.redis_cache.disconnect()
        logger.info("Market Data Agent disconnected")

    async def subscribe(self, symbols: list[str]) -> None:
        """
        Subscribe to real-time 1-minute bars for given symbols.

        Args:
            symbols: List of stock symbols (e.g., ["USO", "UNG"])
        """
        if not self._stream:
            raise RuntimeError("Not connected. Call connect() first.")

        self._symbols = symbols
        logger.info(f"Subscribing to 1-minute bars for: {symbols}")

        # Register bar handler
        async def handle_bar(bar: Bar):
            await self._on_bar_received(bar)

        # Subscribe to bars
        self._stream.subscribe_bars(handle_bar, *symbols)

        # Start WebSocket in background
        asyncio.create_task(self._stream._run_forever())

        logger.info(f"Successfully subscribed to {len(symbols)} symbols")

    async def _on_bar_received(self, bar: Bar) -> None:
        """
        Handle incoming 1-minute bar from Alpaca WebSocket.

        Args:
            bar: Alpaca Bar object
        """
        try:
            symbol = bar.symbol
            logger.debug(
                f"Received 1m bar: {symbol} @ {bar.timestamp} "
                f"O:{bar.open} H:{bar.high} L:{bar.low} C:{bar.close} V:{bar.volume}"
            )

            # Convert to DataFrame row
            bar_data = {
                "timestamp": bar.timestamp,
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": int(bar.volume),
                "vwap": float(bar.vwap) if bar.vwap else None,
                "trade_count": bar.trade_count if hasattr(bar, "trade_count") else None,
            }

            # Append to in-memory buffer
            if symbol not in self._bars_1m:
                self._bars_1m[symbol] = pd.DataFrame([bar_data])
            else:
                self._bars_1m[symbol] = pd.concat(
                    [self._bars_1m[symbol], pd.DataFrame([bar_data])],
                    ignore_index=True,
                )

            # Keep only last 500 bars in memory
            if len(self._bars_1m[symbol]) > 500:
                self._bars_1m[symbol] = self._bars_1m[symbol].iloc[-500:]

            # Cache in Redis
            self.redis_cache.cache_bars_1m(symbol, self._bars_1m[symbol])

            # Persist to PostgreSQL
            await self._persist_bar_1m(symbol, bar_data)

            # Trigger aggregation
            await self._aggregate_timeframes(symbol)

        except Exception as e:
            logger.error(f"Error processing bar for {bar.symbol}: {e}", exc_info=True)

    async def _persist_bar_1m(self, symbol: str, bar_data: dict) -> None:
        """
        Persist 1-minute bar to PostgreSQL.

        Args:
            symbol: Stock symbol
            bar_data: Bar data dict
        """
        try:
            async with get_session() as session:
                bar = Bar1m(symbol=symbol, **bar_data)
                session.add(bar)
                # Commit happens automatically in get_session context manager
            logger.debug(f"Persisted 1m bar to DB: {symbol} @ {bar_data['timestamp']}")
        except Exception as e:
            logger.error(f"Failed to persist 1m bar for {symbol}: {e}")

    async def _aggregate_timeframes(self, symbol: str) -> None:
        """
        Aggregate 1-minute bars to 5m, 15m, 1h, 1d timeframes.

        Args:
            symbol: Stock symbol
        """
        try:
            df_1m = self._bars_1m.get(symbol)
            if df_1m is None or len(df_1m) < 5:
                return  # Need at least 5 bars for 5m aggregation

            df_1m = df_1m.copy()
            df_1m["timestamp"] = pd.to_datetime(df_1m["timestamp"])
            df_1m.set_index("timestamp", inplace=True)

            timeframes = {
                "5m": "5T",
                "15m": "15T",
                "1h": "1H",
                "1d": "1D",
            }

            for tf_name, resample_rule in timeframes.items():
                df_agg = (
                    df_1m.resample(resample_rule)
                    .agg(
                        {
                            "open": "first",
                            "high": "max",
                            "low": "min",
                            "close": "last",
                            "volume": "sum",
                            "vwap": "mean",
                        }
                    )
                    .dropna()
                )

                if len(df_agg) > 0:
                    # Cache in Redis
                    df_agg_reset = df_agg.reset_index()
                    self.redis_cache.cache_bars_aggregated(symbol, tf_name, df_agg_reset)

                    # Calculate indicators for this timeframe
                    await self._calculate_indicators(symbol, tf_name, df_agg)

        except Exception as e:
            logger.error(f"Error aggregating timeframes for {symbol}: {e}")

    async def _calculate_indicators(self, symbol: str, timeframe: str, df: pd.DataFrame) -> None:
        """
        Calculate technical indicators for given timeframe.

        Args:
            symbol: Stock symbol
            timeframe: Timeframe (e.g., "5m", "1h")
            df: DataFrame with OHLCV data (timestamp as index)
        """
        try:
            if len(df) < 20:
                return  # Need at least 20 bars for indicators

            # Calculate indicators using pandas_ta
            df_copy = df.copy()

            # SMA & EMA
            df_copy["sma_20"] = ta.sma(df_copy["close"], length=20)
            df_copy["ema_20"] = ta.ema(df_copy["close"], length=20)

            # RSI
            df_copy["rsi"] = ta.rsi(df_copy["close"], length=14)

            # ATR
            atr = ta.atr(df_copy["high"], df_copy["low"], df_copy["close"], length=14)
            df_copy["atr"] = atr

            # MACD
            macd = ta.macd(df_copy["close"], fast=12, slow=26, signal=9)
            if macd is not None:
                df_copy["macd"] = macd["MACD_12_26_9"]
                df_copy["macd_signal"] = macd["MACDs_12_26_9"]
                df_copy["macd_histogram"] = macd["MACDh_12_26_9"]

            # Bollinger Bands
            bbands = ta.bbands(df_copy["close"], length=20, std=2)
            if bbands is not None and not bbands.empty:
                # Dynamically find columns
                upper_col = next((c for c in bbands.columns if c.startswith("BBU")), None)
                mid_col = next((c for c in bbands.columns if c.startswith("BBM")), None)
                lower_col = next((c for c in bbands.columns if c.startswith("BBL")), None)
                
                if upper_col: df_copy["bb_upper"] = bbands[upper_col]
                if mid_col: df_copy["bb_middle"] = bbands[mid_col]
                if lower_col: df_copy["bb_lower"] = bbands[lower_col]

            # Get latest row
            latest = df_copy.iloc[-1]

            indicators = {
                "sma_20": float(latest.get("sma_20", 0))
                if pd.notna(latest.get("sma_20"))
                else None,
                "ema_20": float(latest.get("ema_20", 0))
                if pd.notna(latest.get("ema_20"))
                else None,
                "rsi": float(latest.get("rsi", 0)) if pd.notna(latest.get("rsi")) else None,
                "atr": float(latest.get("atr", 0)) if pd.notna(latest.get("atr")) else None,
                "macd": float(latest.get("macd", 0)) if pd.notna(latest.get("macd")) else None,
                "macd_signal": float(latest.get("macd_signal", 0))
                if pd.notna(latest.get("macd_signal"))
                else None,
                "macd_histogram": float(latest.get("macd_histogram", 0))
                if pd.notna(latest.get("macd_histogram"))
                else None,
                "bb_upper": float(latest.get("bb_upper", 0))
                if pd.notna(latest.get("bb_upper"))
                else None,
                "bb_middle": float(latest.get("bb_middle", 0))
                if pd.notna(latest.get("bb_middle"))
                else None,
                "bb_lower": float(latest.get("bb_lower", 0))
                if pd.notna(latest.get("bb_lower"))
                else None,
            }

            # Cache in Redis
            self.redis_cache.cache_indicators(symbol, timeframe, indicators)

            # Persist to PostgreSQL
            await self._persist_indicators(symbol, timeframe, latest.name, indicators)

            logger.debug(f"Calculated indicators for {symbol} {timeframe}")

        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol} {timeframe}: {e}")

    async def _persist_indicators(
        self, symbol: str, timeframe: str, timestamp: datetime, indicators: dict
    ) -> None:
        """
        Persist indicators to PostgreSQL.

        Args:
            symbol: Stock symbol
            timeframe: Timeframe
            timestamp: Indicator timestamp
            indicators: Dict of indicator values
        """
        try:
            async with get_session() as session:
                indicator = Indicator(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    **indicators,
                )
                session.add(indicator)
            logger.debug(f"Persisted indicators to DB: {symbol} {timeframe}")
        except Exception as e:
            logger.error(f"Failed to persist indicators for {symbol} {timeframe}: {e}")

    async def get_bars(self, symbol: str, timeframe: str, count: int = 100) -> pd.DataFrame:
        """
        Get recent bars for symbol and timeframe.

        Checks Redis cache first, falls back to in-memory buffer or database.

        Args:
            symbol: Stock symbol
            timeframe: Timeframe ("1m", "5m", "15m", "1h", "1d")
            count: Number of bars to retrieve

        Returns:
            DataFrame with OHLCV data
        """
        # Try Redis cache first
        if timeframe == "1m":
            cached = self.redis_cache.get_bars_1m(symbol)
        else:
            cached = self.redis_cache.get_bars_aggregated(symbol, timeframe)

        if cached is not None and len(cached) >= count:
            return cached.tail(count)

        # Fall back to in-memory buffer for 1m
        if timeframe == "1m" and symbol in self._bars_1m:
            return self._bars_1m[symbol].tail(count)

        # TODO: Fall back to database query
        logger.warning(f"No cached data for {symbol} {timeframe}, returning empty DataFrame")
        return pd.DataFrame()

    async def get_indicators(self, symbol: str, timeframes: list[str]) -> dict[str, dict]:
        """
        Get latest indicators for multiple timeframes.

        Args:
            symbol: Stock symbol
            timeframes: List of timeframes (e.g., ["5m", "15m", "1h"])

        Returns:
            Dict mapping timeframe -> indicators dict
        """
        result = {}
        for tf in timeframes:
            indicators = self.redis_cache.get_indicators(symbol, tf)
            if indicators:
                result[tf] = indicators

        return result

    def get_market_regime(self, symbol: str) -> str:
        """
        Detect current market regime for symbol.

        Uses cached value if available, otherwise analyzes recent price action.

        Args:
            symbol: Stock symbol

        Returns:
            Market regime: "TRENDING", "RANGING", "VOLATILE", or "UNKNOWN"
        """
        # Check cache first
        cached_regime = self.redis_cache.get_regime(symbol)
        if cached_regime:
            return cached_regime

        # Calculate regime from recent data
        try:
            df = self._bars_1m.get(symbol)
            if df is None or len(df) < 50:
                return "UNKNOWN"

            df = df.copy()
            close = df["close"].values

            # Simple regime detection logic
            # TODO: Make this more sophisticated
            sma_20 = pd.Series(close).rolling(20).mean().iloc[-1]
            current_price = close[-1]
            atr_14 = pd.Series(close).rolling(14).std().iloc[-1]

            # Volatility threshold
            volatility_pct = (atr_14 / current_price) * 100

            if volatility_pct > 3.0:
                regime = "VOLATILE"
            elif abs(current_price - sma_20) / sma_20 > 0.02:
                regime = "TRENDING"
            else:
                regime = "RANGING"

            # Cache the result
            self.redis_cache.cache_regime(symbol, regime)
            return regime

        except Exception as e:
            logger.error(f"Error detecting regime for {symbol}: {e}")
            return "UNKNOWN"

    async def fetch_historical_bars(
        self, symbol: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """
        Fetch historical 1-minute bars from Alpaca API.

        Args:
            symbol: Stock symbol
            start: Start datetime
            end: End datetime

        Returns:
            DataFrame with historical bars
        """
        if not self._historical_client:
            raise RuntimeError("Historical client not initialized")

        try:
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame(1, TimeFrameUnit.Minute),
                start=start,
                end=end,
            )

            bars = self._historical_client.get_stock_bars(request)
            df = bars.df

            logger.info(f"Fetched {len(df)} historical 1m bars for {symbol} from {start} to {end}")
            return df

        except Exception as e:
            logger.error(f"Error fetching historical bars for {symbol}: {e}")
            return pd.DataFrame()
