"""Formatting utilities for dashboard display."""

from datetime import datetime
from decimal import Decimal

from dashboard.config import COLORS


def format_currency(value: Decimal | float | None, decimals: int = 2) -> str:
    """Format value as currency ($X,XXX.XX)."""
    if value is None:
        return "$0.00"

    if isinstance(value, Decimal):
        value = float(value)

    return f"${value:,.{decimals}f}"


def format_percentage(value: Decimal | float | None, decimals: int = 2) -> str:
    """Format value as percentage (XX.XX%)."""
    if value is None:
        return "0.00%"

    if isinstance(value, Decimal):
        value = float(value)

    # If value is already in percentage form (e.g., 0.05 for 5%)
    if abs(value) < 1:
        value *= 100

    return f"{value:.{decimals}f}%"


def format_pnl(value: Decimal | float | None, decimals: int = 2) -> str:
    """Format P&L with + or - prefix."""
    if value is None:
        return "$0.00"

    if isinstance(value, Decimal):
        value = float(value)

    sign = "+" if value >= 0 else ""
    return f"{sign}{format_currency(value, decimals)}"


def format_pnl_colored(value: Decimal | float | None, decimals: int = 2) -> str:
    """Format P&L with color coding (green for profit, red for loss)."""
    if value is None:
        value = 0.0

    if isinstance(value, Decimal):
        value = float(value)

    formatted = format_pnl(value, decimals)

    if value > 0:
        return f":{COLORS['profit']}[{formatted}]"
    elif value < 0:
        return f":{COLORS['loss']}[{formatted}]"
    else:
        return formatted


def format_timestamp(dt: datetime | None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime as string."""
    if dt is None:
        return "N/A"

    return dt.strftime(format_str)


def format_date(dt: datetime | None, format_str: str = "%Y-%m-%d") -> str:
    """Format datetime as date string."""
    if dt is None:
        return "N/A"

    return dt.strftime(format_str)


def format_time(dt: datetime | None, format_str: str = "%H:%M:%S") -> str:
    """Format datetime as time string."""
    if dt is None:
        return "N/A"

    return dt.strftime(format_str)


def get_status_color(status: str) -> str:
    """Get color for status badge."""
    status_colors = {
        "OPEN": COLORS["primary"],
        "CLOSED": COLORS["neutral"],
        "FILLED": COLORS["profit"],
        "PENDING": COLORS["warning"],
        "REJECTED": COLORS["loss"],
        "APPROVED": COLORS["profit"],
        "ACTIVE": COLORS["critical"],
        "INACTIVE": COLORS["neutral"],
    }
    return status_colors.get(status.upper(), COLORS["neutral"])


def format_status_badge(status: str) -> str:
    """Format status with colored badge."""
    color = get_status_color(status)
    return f":{color}[{status.upper()}]"


def format_number(value: float | int | Decimal | None, decimals: int = 0) -> str:
    """Format number with thousand separators."""
    if value is None:
        return "0"

    if isinstance(value, Decimal):
        value = float(value)

    if decimals == 0:
        return f"{int(value):,}"
    else:
        return f"{value:,.{decimals}f}"


def format_shares(qty: int | Decimal | None) -> str:
    """Format share quantity."""
    if qty is None:
        return "0"

    if isinstance(qty, Decimal):
        qty = int(qty)

    return f"{qty:,}"


def shorten_text(text: str | None, max_length: int = 50) -> str:
    """Shorten text with ellipsis if too long."""
    if text is None:
        return ""

    if len(text) <= max_length:
        return text

    return text[: max_length - 3] + "..."


def format_confidence(confidence: Decimal | float | None) -> str:
    """Format confidence as percentage with color."""
    if confidence is None:
        return "N/A"

    if isinstance(confidence, Decimal):
        confidence = float(confidence)

    # Confidence is 0-1, convert to percentage
    pct = confidence * 100

    if pct >= 80:
        color = COLORS["profit"]
    elif pct >= 60:
        color = COLORS["warning"]
    else:
        color = COLORS["loss"]

    return f":{color}[{pct:.1f}%]"


def format_risk_pct(risk_pct: Decimal | float | None) -> str:
    """Format risk percentage with color (lower is better)."""
    if risk_pct is None:
        return "N/A"

    if isinstance(risk_pct, Decimal):
        risk_pct = float(risk_pct)

    # Convert to percentage if needed
    if risk_pct < 1:
        risk_pct *= 100

    if risk_pct <= 1:
        color = COLORS["profit"]
    elif risk_pct <= 2:
        color = COLORS["warning"]
    else:
        color = COLORS["loss"]

    return f":{color}[{risk_pct:.2f}%]"
