"""Redis caching layer for hot data (bars, indicators, regime)."""

import json
import logging
from typing import Any

import pandas as pd
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from src.core.config import RedisConfig

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis client wrapper with TTL management and error handling."""

    def __init__(self, config: RedisConfig):
        """
        Initialize Redis client.

        Args:
            config: Redis configuration
        """
        self.config = config
        self._client: Redis | None = None

    def connect(self) -> None:
        """Establish connection to Redis server."""
        if self._client is not None:
            logger.warning("Redis client already connected")
            return

        try:
            password = self.config.password.get_secret_value() if self.config.password else None

            self._client = Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=password,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                max_connections=self.config.max_connections,
                decode_responses=True,  # Auto-decode bytes to str
            )

            # Test connection
            self._client.ping()
            logger.info(f"Redis connected: {self.config.host}:{self.config.port}/{self.config.db}")

        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._client = None
            raise

    def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
            logger.info("Redis disconnected")

    @property
    def client(self) -> Redis:
        """
        Get Redis client instance.

        Returns:
            Redis client

        Raises:
            RuntimeError: If not connected
        """
        if self._client is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    # ===== Bar Caching =====

    def cache_bars_1m(self, symbol: str, df: pd.DataFrame) -> None:
        """
        Cache 1-minute bars with TTL.

        Args:
            symbol: Stock symbol (e.g., "USO")
            df: DataFrame with OHLCV data
        """
        if df.empty:
            logger.warning(f"Skipping cache for empty DataFrame: {symbol}")
            return

        key = f"bars:1m:{symbol}"
        try:
            # Convert DataFrame to JSON
            data = df.to_json(orient="split", date_format="iso")
            self.client.setex(key, self.config.ttl_bars_1m, data)
            logger.debug(f"Cached {len(df)} 1m bars for {symbol}")
        except Exception as e:
            logger.error(f"Failed to cache 1m bars for {symbol}: {e}")

    def get_bars_1m(self, symbol: str) -> pd.DataFrame | None:
        """
        Retrieve cached 1-minute bars.

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame if cached, None if not found or expired
        """
        key = f"bars:1m:{symbol}"
        try:
            data = self.client.get(key)
            if data is None:
                return None

            df = pd.read_json(data, orient="split")
            logger.debug(f"Retrieved {len(df)} cached 1m bars for {symbol}")
            return df
        except Exception as e:
            logger.error(f"Failed to retrieve 1m bars for {symbol}: {e}")
            return None

    def cache_bars_aggregated(self, symbol: str, timeframe: str, df: pd.DataFrame) -> None:
        """
        Cache aggregated bars (5m, 15m, 1h, 1d) with TTL.

        Args:
            symbol: Stock symbol
            timeframe: Timeframe (e.g., "5m", "1h")
            df: DataFrame with OHLCV data
        """
        if df.empty:
            logger.warning(f"Skipping cache for empty DataFrame: {symbol} {timeframe}")
            return

        key = f"bars:{timeframe}:{symbol}"
        try:
            data = df.to_json(orient="split", date_format="iso")
            ttl = self.config.ttl_bars_5m  # Use 5m TTL for all aggregated
            self.client.setex(key, ttl, data)
            logger.debug(f"Cached {len(df)} {timeframe} bars for {symbol}")
        except Exception as e:
            logger.error(f"Failed to cache {timeframe} bars for {symbol}: {e}")

    def get_bars_aggregated(self, symbol: str, timeframe: str) -> pd.DataFrame | None:
        """
        Retrieve cached aggregated bars.

        Args:
            symbol: Stock symbol
            timeframe: Timeframe (e.g., "5m")

        Returns:
            DataFrame if cached, None otherwise
        """
        key = f"bars:{timeframe}:{symbol}"
        try:
            data = self.client.get(key)
            if data is None:
                return None

            df = pd.read_json(data, orient="split")
            logger.debug(f"Retrieved {len(df)} cached {timeframe} bars for {symbol}")
            return df
        except Exception as e:
            logger.error(f"Failed to retrieve {timeframe} bars for {symbol}: {e}")
            return None

    # ===== Indicator Caching =====

    def cache_indicators(self, symbol: str, timeframe: str, indicators: dict) -> None:
        """
        Cache technical indicators with TTL.

        Args:
            symbol: Stock symbol
            timeframe: Timeframe
            indicators: Dict of indicator name -> value
        """
        key = f"indicators:{timeframe}:{symbol}"
        try:
            data = json.dumps(indicators)
            self.client.setex(key, self.config.ttl_indicators, data)
            logger.debug(f"Cached indicators for {symbol} {timeframe}")
        except Exception as e:
            logger.error(f"Failed to cache indicators for {symbol} {timeframe}: {e}")

    def get_indicators(self, symbol: str, timeframe: str) -> dict | None:
        """
        Retrieve cached indicators.

        Args:
            symbol: Stock symbol
            timeframe: Timeframe

        Returns:
            Dict of indicators if cached, None otherwise
        """
        key = f"indicators:{timeframe}:{symbol}"
        try:
            data = self.client.get(key)
            if data is None:
                return None

            indicators = json.loads(data)
            logger.debug(f"Retrieved cached indicators for {symbol} {timeframe}")
            return indicators
        except Exception as e:
            logger.error(f"Failed to retrieve indicators for {symbol} {timeframe}: {e}")
            return None

    # ===== Market Regime Caching =====

    def cache_regime(self, symbol: str, regime: str) -> None:
        """
        Cache current market regime.

        Args:
            symbol: Stock symbol
            regime: Market regime (TRENDING, RANGING, VOLATILE)
        """
        key = f"regime:{symbol}"
        try:
            self.client.setex(key, self.config.ttl_regime, regime)
            logger.debug(f"Cached regime for {symbol}: {regime}")
        except Exception as e:
            logger.error(f"Failed to cache regime for {symbol}: {e}")

    def get_regime(self, symbol: str) -> str | None:
        """
        Retrieve cached market regime.

        Args:
            symbol: Stock symbol

        Returns:
            Regime string if cached, None otherwise
        """
        key = f"regime:{symbol}"
        try:
            regime = self.client.get(key)
            if regime:
                logger.debug(f"Retrieved cached regime for {symbol}: {regime}")
            return regime
        except Exception as e:
            logger.error(f"Failed to retrieve regime for {symbol}: {e}")
            return None

    # ===== Generic Key-Value =====

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set generic key-value pair with optional TTL.

        Args:
            key: Cache key
            value: Value to cache (will be JSON-serialized)
            ttl: Time-to-live in seconds (None = no expiry)
        """
        try:
            data = json.dumps(value) if not isinstance(value, str) else value
            if ttl:
                self.client.setex(key, ttl, data)
            else:
                self.client.set(key, data)
            logger.debug(f"Set cache key: {key} (TTL: {ttl})")
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")

    def get(self, key: str) -> Any | None:
        """
        Get generic key value.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        try:
            data = self.client.get(key)
            if data is None:
                return None

            # Try to parse as JSON, otherwise return raw string
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None

    def delete(self, key: str) -> None:
        """
        Delete cache key.

        Args:
            key: Cache key
        """
        try:
            self.client.delete(key)
            logger.debug(f"Deleted cache key: {key}")
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")

    def flush_all(self) -> None:
        """Flush all keys from current database. Use with caution!"""
        try:
            self.client.flushdb()
            logger.warning("Flushed all Redis keys from current database")
        except Exception as e:
            logger.error(f"Failed to flush Redis database: {e}")

    def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if connected and responsive, False otherwise
        """
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# ===== Global Redis Client =====

_redis_cache: RedisCache | None = None


def get_redis_client(config: RedisConfig | None = None) -> RedisCache:
    """
    Get global Redis cache instance.

    Args:
        config: Redis configuration (only needed on first call)

    Returns:
        RedisCache instance

    Example:
        >>> from src.core.config import RedisConfig
        >>> config = RedisConfig()
        >>> cache = get_redis_client(config)
        >>> cache.connect()
        >>> cache.set("test", "value", ttl=60)
    """
    global _redis_cache

    if _redis_cache is None:
        if config is None:
            from src.core.config import RedisConfig

            config = RedisConfig()
        _redis_cache = RedisCache(config)

    return _redis_cache
