"""Dashboard configuration."""

from pathlib import Path

# Dashboard settings
DASHBOARD_TITLE = "Trading System Dashboard"
AUTO_REFRESH_INTERVAL = 5000  # 5 seconds in milliseconds
PAGE_ICON = "📈"

# Chart settings
DEFAULT_CHART_HEIGHT = 500
DEFAULT_TIMEFRAME = "1D"
CHART_TIMEFRAMES = ["1H", "4H", "1D", "1W"]

# Color scheme (matching .streamlit/config.toml)
COLORS = {
    "primary": "#00D4AA",
    "background": "#0E1117",
    "secondary_bg": "#1A1F2C",
    "text": "#FAFAFA",
    "profit": "#00D4AA",
    "loss": "#FF4B4B",
    "neutral": "#808080",
    "warning": "#FFA500",
    "critical": "#FF0000",
}

# Risk thresholds
RISK_THRESHOLDS = {
    "portfolio_heat": {
        "low": 0.3,  # 0-30% is green
        "medium": 0.6,  # 30-60% is yellow
        "high": 1.0,  # 60-100% is red
    },
    "rsi": {
        "oversold": 30,
        "overbought": 70,
    },
}

# Data refresh settings
CACHE_TTL = 5  # Cache TTL in seconds (matches auto-refresh)
MAX_SIGNAL_DISPLAY = 50  # Maximum signals to display in feed
MAX_DECISION_DISPLAY = 100  # Maximum decisions in audit trail

# Database settings (inherit from main config)
PROJECT_ROOT = Path(__file__).parent.parent
