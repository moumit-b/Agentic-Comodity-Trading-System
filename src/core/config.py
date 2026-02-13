"""Configuration models for the trading system using pydantic-settings."""

from decimal import Decimal
from enum import Enum
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AutomationMode(str, Enum):
    """Trading automation modes with progressive safety levels."""

    ADVISORY = "ADVISORY"  # Only shows signals, no execution
    PAPER_AUTO = "PAPER_AUTO"  # Auto-executes in paper trading
    LIVE_CONFIRM = "LIVE_CONFIRM"  # Requires Discord/dashboard confirmation
    LIVE_AUTO = "LIVE_AUTO"  # Fully autonomous (requires feature flag)


class MarketRegime(str, Enum):
    """Market regime states for strategy selection."""

    TRENDING = "TRENDING"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    UNKNOWN = "UNKNOWN"


class TradingConfig(BaseSettings):
    """Core trading configuration with risk parameters and automation settings."""

    model_config = SettingsConfigDict(
        env_prefix="TRADING_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Symbols & Timeframes ===
    symbols: list[str] = Field(default=["USO", "UNG"])
    primary_timeframe: str = Field(default="1m")
    analysis_timeframes: list[str] = Field(default=["1m", "5m", "15m", "1h", "1d"])

    # === Risk Management ===
    risk_per_trade_pct: Decimal = Field(default=Decimal("0.01"), description="1% default")
    max_risk_per_trade_pct: Decimal = Field(default=Decimal("0.02"), description="2% hard limit")
    max_portfolio_heat_pct: Decimal = Field(
        default=Decimal("0.05"), description="5% total risk cap"
    )
    max_positions: int = Field(default=2, ge=1, le=10)

    # === Daily Limits ===
    daily_profit_target_pct: Decimal = Field(default=Decimal("0.02"), description="2% daily")
    daily_loss_limit_pct: Decimal = Field(default=Decimal("0.03"), description="3% daily")
    max_consecutive_losses: int = Field(default=3, ge=1, le=10)
    max_trades_per_day: int = Field(default=10, ge=1, le=50)

    # === Stop Loss & Take Profit ===
    default_stop_atr_multiple: Decimal = Field(default=Decimal("2.0"), gt=0)
    default_tp_atr_multiple: Decimal = Field(default=Decimal("3.0"), gt=0)
    enable_trailing_stop: bool = Field(default=True)
    trailing_stop_pct: Decimal = Field(default=Decimal("0.015"), description="1.5%")

    # === Time-Based Rules (ET timezone) ===
    trading_start_et: str = Field(default="09:30")
    trading_end_et: str = Field(default="16:00")
    intraday_exit_time_et: str = Field(default="15:55")
    no_new_trades_after_et: str = Field(default="15:30")

    # === Automation Mode ===
    automation_mode: AutomationMode = Field(default=AutomationMode.ADVISORY)
    confirmation_timeout_seconds: int = Field(default=60, ge=10, le=600)

    # === Feature Flags ===
    enable_live_auto: bool = Field(
        default=False, description="CRITICAL: Must be explicitly True for LIVE_AUTO"
    )
    enable_swing_trading: bool = Field(default=True)
    enable_breakout_strategies: bool = Field(default=False)

    # Phase 2: Context Agent
    enable_context_agent: bool = Field(default=True, description="Enable LLM-powered sentiment analysis")
    context_cache_ttl_minutes: int = Field(default=5, ge=1, le=60)

    # Phase 2: Recursive Learning Model (RLM)
    enable_rlm: bool = Field(default=True, description="Enable Recursive Learning Model")
    rlm_auto_apply: bool = Field(default=True, description="Auto-apply RLM adjustments (paper mode)")
    rlm_adjustment_expiry_hours: int = Field(default=24, ge=1, le=168)
    rlm_observation_interval_minutes: int = Field(default=5, ge=1, le=60)
    rlm_reflection_interval_minutes: int = Field(default=15, ge=5, le=120)

    # Phase 2: Dynamic Thresholds
    enable_dynamic_thresholds: bool = Field(default=True)

    @field_validator("automation_mode")
    @classmethod
    def validate_live_auto(cls, v: AutomationMode, info) -> AutomationMode:
        """Ensure LIVE_AUTO mode has explicit feature flag enabled."""
        if v == AutomationMode.LIVE_AUTO:
            enable_live_auto = info.data.get("enable_live_auto", False)
            if not enable_live_auto:
                raise ValueError(
                    "LIVE_AUTO mode requires enable_live_auto=True feature flag. "
                    "Set TRADING_ENABLE_LIVE_AUTO=true in .env"
                )
        return v


class DatabaseConfig(BaseSettings):
    """PostgreSQL database connection configuration."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    host: str = Field(default="localhost")
    port: int = Field(default=5432, ge=1, le=65535)
    name: str = Field(default="trading_system")
    user: str = Field(default="postgres")
    password: SecretStr = Field(default=SecretStr("postgres"))

    # Connection pool settings
    pool_size: int = Field(default=10, ge=1, le=50)
    max_overflow: int = Field(default=20, ge=0, le=100)
    pool_timeout: int = Field(default=30, ge=5, le=300)
    pool_recycle: int = Field(default=3600, description="Recycle connections every hour")

    # Performance settings
    echo_sql: bool = Field(default=False, description="Log all SQL queries")
    command_timeout: int = Field(default=60, description="Query timeout in seconds")

    @property
    def url(self) -> str:
        """Construct async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @property
    def url_sync(self) -> str:
        """Construct sync PostgreSQL connection URL for Alembic."""
        return (
            f"postgresql://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class RedisConfig(BaseSettings):
    """Redis cache configuration."""

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    host: str = Field(default="localhost")
    port: int = Field(default=6379, ge=1, le=65535)
    db: int = Field(default=0, ge=0, le=15)
    password: SecretStr | None = Field(default=None)

    # TTL settings (seconds)
    ttl_bars_1m: int = Field(default=300, description="5 minutes")
    ttl_bars_5m: int = Field(default=900, description="15 minutes")
    ttl_indicators: int = Field(default=600, description="10 minutes")
    ttl_regime: int = Field(default=300, description="5 minutes")

    # Connection settings
    socket_timeout: int = Field(default=5, ge=1, le=60)
    socket_connect_timeout: int = Field(default=5, ge=1, le=60)
    max_connections: int = Field(default=50, ge=1, le=200)

    @property
    def url(self) -> str:
        """Construct Redis connection URL."""
        if self.password:
            return f"redis://:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class AlpacaConfig(BaseSettings):
    """Alpaca API configuration for market data and trading."""

    model_config = SettingsConfigDict(
        env_prefix="ALPACA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: SecretStr = Field(default=SecretStr(""), description="Alpaca API key (paper or live)")
    api_secret: SecretStr = Field(default=SecretStr(""), description="Alpaca API secret")
    base_url: str = Field(
        default="https://paper-api.alpaca.markets",
        description="Paper: https://paper-api.alpaca.markets, Live: https://api.alpaca.markets",
    )
    data_url: str = Field(
        default="https://data.alpaca.markets", description="Market data API endpoint"
    )
    stream_url: str = Field(
        default="wss://stream.data.alpaca.markets", description="WebSocket data stream"
    )

    # Paper trading flag
    is_paper: bool = Field(default=True, description="Use paper trading account")

    # WebSocket settings
    ws_reconnect_attempts: int = Field(default=5, ge=1, le=20)
    ws_reconnect_delay: int = Field(default=5, ge=1, le=60, description="Seconds")

    @field_validator("base_url")
    @classmethod
    def validate_paper_url(cls, v: str, info) -> str:
        """Ensure paper/live URL matches is_paper flag."""
        is_paper = info.data.get("is_paper", True)
        is_paper_url = "paper" in v.lower()

        if is_paper and not is_paper_url:
            raise ValueError(
                "is_paper=True but base_url is live API. Set ALPACA_BASE_URL="
                "https://paper-api.alpaca.markets"
            )
        if not is_paper and is_paper_url:
            raise ValueError(
                "is_paper=False but base_url is paper API. Confirm you want live trading!"
            )
        return v


class DiscordConfig(BaseSettings):
    """Discord bot configuration for notifications and confirmations."""

    model_config = SettingsConfigDict(
        env_prefix="DISCORD_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: SecretStr = Field(default=SecretStr(""), description="Discord bot token")
    user_id: str = Field(default="", description="Your Discord user ID for DMs")
    confirmation_channel_id: str = Field(
        default="", description="Optional: dedicated confirmation channel"
    )

    # Notification settings
    send_daily_summary: bool = Field(default=True)
    send_trade_alerts: bool = Field(default=True)
    send_error_alerts: bool = Field(default=True)

    # Rate limiting
    max_messages_per_minute: int = Field(default=10, ge=1, le=30)


class FinnhubConfig(BaseSettings):
    """Finnhub API configuration for real-time market data."""

    model_config = SettingsConfigDict(
        env_prefix="FINNHUB_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: SecretStr = Field(default=SecretStr(""), description="Finnhub API key (free tier)")
    ws_url: str = Field(default="wss://ws.finnhub.io", description="WebSocket endpoint")

    # Connection settings
    ws_reconnect_attempts: int = Field(default=5, ge=1, le=20)
    ws_reconnect_delay: int = Field(default=5, ge=1, le=60, description="Seconds")
    ws_ping_interval: int = Field(default=30, ge=10, le=120, description="Keep-alive ping")

    # Rate limiting (free tier: 60 requests/min)
    rate_limit_per_minute: int = Field(default=55, ge=1, le=60, description="Safety buffer")

    # Data source priority
    use_as_primary: bool = Field(
        default=True, description="Use Finnhub as primary real-time source (Alpaca as backup)"
    )


class AWSConfig(BaseSettings):
    """AWS configuration for cloud deployment."""

    model_config = SettingsConfigDict(
        env_prefix="AWS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    region: str = Field(default="us-east-1")
    access_key_id: SecretStr = Field(default=SecretStr(""), description="AWS access key")
    secret_access_key: SecretStr = Field(default=SecretStr(""), description="AWS secret key")

    # RDS settings (overrides DatabaseConfig when deployed)
    rds_endpoint: str | None = Field(default=None, description="RDS instance endpoint")
    rds_port: int = Field(default=5432)

    # ElastiCache settings (overrides RedisConfig when deployed)
    elasticache_endpoint: str | None = Field(
        default=None, description="ElastiCache cluster endpoint"
    )
    elasticache_port: int = Field(default=6379)

    # Secrets Manager
    secrets_manager_arn: str | None = Field(
        default=None, description="ARN for secrets stored in Secrets Manager"
    )

    # Lambda settings
    lambda_timeout: int = Field(default=60, ge=10, le=900, description="Lambda timeout")
    lambda_memory: int = Field(default=512, ge=128, le=10240, description="Lambda memory MB")


class GeminiConfig(BaseSettings):
    """Gemini LLM configuration (fallback provider)."""

    model_config = SettingsConfigDict(
        env_prefix="GEMINI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Configuration
    api_key: SecretStr = Field(default=SecretStr(""), description="Gemini API key")
    model_name: str = Field(default="gemini-2.5-flash-lite", description="Model to use")

    # Rate Limits (Gemini 2.5 Flash-Lite free tier - 15 RPM, 1000 RPD)
    max_requests_per_minute: int = Field(default=15, ge=1, le=60)
    max_tokens_per_minute: int = Field(default=250_000, ge=1)
    max_requests_per_day: int = Field(default=1000, ge=1)

    # Caching
    cache_ttl_seconds: int = Field(default=300, description="5 min cache for context analysis")

    # Generation Parameters
    temperature: float = Field(default=0.3, ge=0.0, le=1.0, description="Lower = more deterministic")
    max_output_tokens: int = Field(default=1024, ge=1, le=8192)

    # Safety
    enable_llm: bool = Field(default=True, description="Feature flag to disable LLM calls")


class GroqConfig(BaseSettings):
    """Groq LLM configuration (primary provider - fastest free inference)."""

    model_config = SettingsConfigDict(
        env_prefix="GROQ_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Configuration
    api_key: SecretStr = Field(default=SecretStr(""), description="Groq API key")
    model_name: str = Field(
        default="llama-3.3-70b-versatile", description="Groq model to use"
    )

    # Rate Limits (Groq free tier)
    max_requests_per_minute: int = Field(default=30, ge=1, le=60)
    max_tokens_per_minute: int = Field(default=6000, ge=1)
    max_requests_per_day: int = Field(default=1000, ge=1)

    # Generation Parameters
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)

    # Safety
    enable_groq: bool = Field(default=True, description="Feature flag to enable Groq as primary")


@lru_cache
def get_config() -> tuple[
    TradingConfig,
    DatabaseConfig,
    RedisConfig,
    AlpacaConfig,
    DiscordConfig,
    FinnhubConfig,
    AWSConfig,
    GeminiConfig,
    GroqConfig,
]:
    """
    Load all configuration objects from environment.

    Cached to prevent repeated .env file reads.

    Returns:
        Tuple of (TradingConfig, DatabaseConfig, RedisConfig, AlpacaConfig,
                  DiscordConfig, FinnhubConfig, AWSConfig, GeminiConfig, GroqConfig)

    Example:
        >>> trading, db, redis, alpaca, discord, finnhub, aws, gemini, groq = get_config()
        >>> print(f"Risk per trade: {trading.risk_per_trade_pct}")
        >>> print(f"Database URL: {db.url}")
    """
    return (
        TradingConfig(),
        DatabaseConfig(),
        RedisConfig(),
        AlpacaConfig(),
        DiscordConfig(),
        FinnhubConfig(),
        AWSConfig(),
        GeminiConfig(),
        GroqConfig(),
    )
