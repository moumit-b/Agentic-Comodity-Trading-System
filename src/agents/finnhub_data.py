"""Finnhub Data Agent for real-time WebSocket market data."""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from src.core.config import FinnhubConfig

logger = logging.getLogger(__name__)


class FinnhubDataAgent:
    """
    Professional-grade Finnhub WebSocket agent for real-time market data.

    Features:
    - Real-time trade/quote streaming via WebSocket
    - Automatic reconnection with exponential backoff
    - Rate limiting (60 req/min free tier)
    - Bar aggregation (tick → 1-minute bars)
    - Heartbeat monitoring
    - Graceful error handling
    """

    def __init__(self, config: FinnhubConfig, on_bar_callback: Callable):
        """
        Initialize Finnhub Data Agent.

        Args:
            config: Finnhub configuration
            on_bar_callback: Async callback function(symbol, bar_data) for completed 1m bars
        """
        self.config = config
        self.on_bar_callback = on_bar_callback

        # WebSocket state
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._running = False
        self._reconnect_attempts = 0
        self._last_ping = time.time()

        # Subscribed symbols
        self._symbols: set[str] = set()

        # Bar aggregation buffers (tick → 1m bars)
        self._current_bars: dict[
            str, dict
        ] = {}  # symbol → {open, high, low, close, volume, vwap_sum, trade_count}
        self._bar_start_time: dict[str, datetime] = {}  # symbol → bar start timestamp

        # Rate limiting
        self._request_times: list[float] = []

    async def connect(self) -> None:
        """Initialize WebSocket connection to Finnhub."""
        logger.info("Connecting to Finnhub WebSocket...")

        if not self.config.api_key.get_secret_value():
            raise ValueError("FINNHUB_API_KEY not set in environment")

        self._running = True
        await self._establish_connection()

        logger.info("Finnhub Data Agent connected successfully")

    async def _establish_connection(self) -> None:
        """
        Establish WebSocket connection with retry logic.

        Implements exponential backoff for reconnection attempts.
        """
        while self._running and self._reconnect_attempts < self.config.ws_reconnect_attempts:
            try:
                ws_url = f"{self.config.ws_url}?token={self.config.api_key.get_secret_value()}"
                self._ws = await websockets.connect(
                    ws_url, ping_interval=self.config.ws_ping_interval
                )

                logger.info(f"WebSocket connected to {self.config.ws_url}")
                self._reconnect_attempts = 0

                # Resubscribe to symbols after reconnection
                if self._symbols:
                    await self._resubscribe_all()

                return

            except (ConnectionClosed, WebSocketException, OSError) as e:
                self._reconnect_attempts += 1
                backoff = min(2**self._reconnect_attempts, 60)  # Max 60s backoff

                logger.warning(
                    f"WebSocket connection failed (attempt {self._reconnect_attempts}/"
                    f"{self.config.ws_reconnect_attempts}): {e}"
                )

                if self._reconnect_attempts < self.config.ws_reconnect_attempts:
                    logger.info(f"Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                else:
                    logger.error("Max reconnection attempts reached. Giving up.")
                    raise

    async def disconnect(self) -> None:
        """Close WebSocket connection gracefully."""
        logger.info("Disconnecting Finnhub Data Agent...")

        self._running = False

        if self._ws and not self._ws.closed:
            await self._ws.close()
            self._ws = None

        logger.info("Finnhub Data Agent disconnected")

    async def subscribe(self, symbols: list[str]) -> None:
        """
        Subscribe to real-time trades for given symbols.

        Args:
            symbols: List of stock symbols (e.g., ["USO", "UNG"])
        """
        if not self._ws or self._ws.closed:
            raise RuntimeError("Not connected. Call connect() first.")

        logger.info(f"Subscribing to real-time trades for: {symbols}")

        for symbol in symbols:
            await self._subscribe_symbol(symbol)
            self._symbols.add(symbol)

        logger.info(f"Successfully subscribed to {len(symbols)} symbols")

    async def _subscribe_symbol(self, symbol: str) -> None:
        """
        Subscribe to a single symbol with rate limiting.

        Args:
            symbol: Stock symbol
        """
        # Rate limiting: max 60 req/min (free tier)
        await self._enforce_rate_limit()

        subscribe_msg = {"type": "subscribe", "symbol": symbol}

        try:
            await self._ws.send(json.dumps(subscribe_msg))
            logger.debug(f"Subscribed to {symbol}")
        except Exception as e:
            logger.error(f"Failed to subscribe to {symbol}: {e}")

    async def _resubscribe_all(self) -> None:
        """Resubscribe to all symbols after reconnection."""
        logger.info(f"Resubscribing to {len(self._symbols)} symbols after reconnection...")

        for symbol in self._symbols:
            await self._subscribe_symbol(symbol)

    async def _enforce_rate_limit(self) -> None:
        """
        Enforce rate limiting (60 req/min for free tier).

        Uses sliding window algorithm.
        """
        now = time.time()

        # Remove requests older than 60 seconds
        self._request_times = [t for t in self._request_times if now - t < 60]

        # Check if we're at the limit
        if len(self._request_times) >= self.config.rate_limit_per_minute:
            oldest = self._request_times[0]
            sleep_time = 60 - (now - oldest) + 0.1  # Small buffer

            logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)

        self._request_times.append(now)

    async def run(self) -> None:
        """
        Main WebSocket message loop.

        Listens for trade messages and aggregates into 1-minute bars.
        """
        if not self._ws:
            raise RuntimeError("Not connected. Call connect() first.")

        logger.info("Starting Finnhub WebSocket message loop...")

        try:
            async for message in self._ws:
                await self._handle_message(message)

        except ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")

            if self._running:
                logger.info("Attempting to reconnect...")
                await self._establish_connection()
                await self.run()  # Resume listening

        except Exception as e:
            logger.error(f"Error in WebSocket message loop: {e}", exc_info=True)
            raise

    async def _handle_message(self, message: str) -> None:
        """
        Handle incoming WebSocket message.

        Finnhub sends trade messages in format:
        {
            "data": [
                {"s": "AAPL", "p": 150.25, "t": 1672531200000, "v": 100},
                ...
            ],
            "type": "trade"
        }

        Args:
            message: Raw JSON message string
        """
        try:
            data = json.loads(message)

            if data.get("type") == "ping":
                # Respond to ping
                await self._ws.send(json.dumps({"type": "pong"}))
                self._last_ping = time.time()
                return

            if data.get("type") != "trade":
                return  # Ignore non-trade messages

            # Process trade data
            for trade in data.get("data", []):
                await self._process_trade(trade)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def _process_trade(self, trade: dict) -> None:
        """
        Process individual trade and aggregate into 1-minute bars.

        Args:
            trade: Trade dict with keys: s (symbol), p (price), t (timestamp_ms), v (volume)
        """
        try:
            symbol = trade["s"]
            price = float(trade["p"])
            timestamp_ms = int(trade["t"])
            volume = int(trade["v"])

            timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)

            # Round down to minute
            bar_time = timestamp.replace(second=0, microsecond=0)

            # Check if we need to finalize the previous bar
            if symbol in self._bar_start_time and bar_time != self._bar_start_time[symbol]:
                await self._finalize_bar(symbol)

            # Initialize or update current bar
            if symbol not in self._current_bars or bar_time != self._bar_start_time.get(symbol):
                self._current_bars[symbol] = {
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": volume,
                    "vwap_sum": price * volume,
                    "trade_count": 1,
                }
                self._bar_start_time[symbol] = bar_time
            else:
                bar = self._current_bars[symbol]
                bar["high"] = max(bar["high"], price)
                bar["low"] = min(bar["low"], price)
                bar["close"] = price
                bar["volume"] += volume
                bar["vwap_sum"] += price * volume
                bar["trade_count"] += 1

        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Invalid trade data: {trade}, error: {e}")

    async def _finalize_bar(self, symbol: str) -> None:
        """
        Finalize completed 1-minute bar and send to callback.

        Args:
            symbol: Stock symbol
        """
        try:
            if symbol not in self._current_bars:
                return

            bar = self._current_bars[symbol]
            timestamp = self._bar_start_time[symbol]

            # Calculate VWAP
            vwap = bar["vwap_sum"] / bar["volume"] if bar["volume"] > 0 else bar["close"]

            bar_data = {
                "timestamp": timestamp,
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "volume": bar["volume"],
                "vwap": vwap,
                "trade_count": bar["trade_count"],
            }

            logger.debug(
                f"Finnhub 1m bar finalized: {symbol} @ {timestamp} "
                f"O:{bar['open']:.2f} H:{bar['high']:.2f} L:{bar['low']:.2f} "
                f"C:{bar['close']:.2f} V:{bar['volume']}"
            )

            # Send to callback (MarketDataAgent)
            await self.on_bar_callback(symbol, bar_data)

            # Clear buffer
            del self._current_bars[symbol]

        except Exception as e:
            logger.error(f"Error finalizing bar for {symbol}: {e}", exc_info=True)

    def get_health_status(self) -> dict:
        """
        Get current health status of WebSocket connection.

        Returns:
            Dict with connection status, last ping time, subscribed symbols
        """
        return {
            "connected": self._ws is not None and not self._ws.closed,
            "running": self._running,
            "last_ping": self._last_ping,
            "time_since_ping": time.time() - self._last_ping,
            "subscribed_symbols": list(self._symbols),
            "reconnect_attempts": self._reconnect_attempts,
        }
