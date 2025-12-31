"""Discord notification service for trading alerts and confirmations."""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from src.core.config import DiscordConfig

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    CONFIRM = "CONFIRM"


@dataclass
class TradeAlert:
    """Trading alert message."""

    level: AlertLevel
    title: str
    description: str
    fields: dict[str, str]
    color: int
    requires_confirmation: bool = False
    order_id: str | None = None


class DiscordNotifier:
    """
    Discord notification service for:
    - Trade alerts and recommendations
    - Circuit breaker notifications
    - Confirmation requests
    - Daily summaries
    """

    def __init__(self, webhook_url: str | None = None, enabled: bool = True):
        """
        Initialize Discord notifier.

        Args:
            webhook_url: Discord webhook URL (optional)
            enabled: Whether notifications are enabled
        """
        self.webhook_url = webhook_url
        self.enabled = enabled and webhook_url is not None

        # Color codes for embed
        self.colors = {
            AlertLevel.INFO: 0x3498DB,  # Blue
            AlertLevel.WARNING: 0xF39C12,  # Orange
            AlertLevel.CRITICAL: 0xE74C3C,  # Red
            AlertLevel.CONFIRM: 0x9B59B6,  # Purple
        }

    async def send_alert(self, alert: TradeAlert) -> bool:
        """
        Send alert to Discord via webhook.

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully
        """
        if not self.enabled or not self.webhook_url:
            logger.debug("Discord notifications disabled, skipping alert")
            return False

        try:
            import aiohttp

            # Build Discord embed
            embed = {
                "title": alert.title,
                "description": alert.description,
                "color": alert.color,
                "timestamp": datetime.now().isoformat(),
                "footer": {"text": "Commodity Trading System"},
                "fields": [
                    {"name": name, "value": value, "inline": True}
                    for name, value in alert.fields.items()
                ],
            }

            # Send to webhook
            payload = {"embeds": [embed]}

            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as resp:
                    if resp.status != 204:
                        logger.error(f"Discord webhook failed with status {resp.status}")
                        return False

            logger.info(f"Sent Discord alert: {alert.title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return False

    async def notify_signal_generated(
        self,
        symbol: str,
        direction: str,
        strategy: str,
        confidence: Decimal,
        entry: Decimal,
        stop: Decimal,
        target: Decimal,
    ) -> bool:
        """Notify about new trading signal."""
        alert = TradeAlert(
            level=AlertLevel.INFO,
            title=f"📊 Signal: {direction} {symbol}",
            description=f"New {direction} signal from {strategy}",
            fields={
                "Symbol": symbol,
                "Strategy": strategy,
                "Confidence": f"{confidence:.1%}",
                "Entry": f"${entry:.2f}",
                "Stop Loss": f"${stop:.2f}",
                "Target": f"${target:.2f}",
                "R:R Ratio": f"{abs(target - entry) / abs(entry - stop):.2f}",
            },
            color=self.colors[AlertLevel.INFO],
        )
        return await self.send_alert(alert)

    async def notify_trade_execution(
        self,
        symbol: str,
        side: str,
        qty: Decimal,
        price: Decimal,
        order_id: str,
        is_paper: bool,
    ) -> bool:
        """Notify about trade execution."""
        mode_tag = "[PAPER]" if is_paper else "[LIVE]"
        alert = TradeAlert(
            level=AlertLevel.WARNING if not is_paper else AlertLevel.INFO,
            title=f"✅ {mode_tag} Trade Executed: {side} {symbol}",
            description=f"Order {order_id} filled",
            fields={
                "Symbol": symbol,
                "Side": side,
                "Quantity": str(qty),
                "Price": f"${price:.2f}",
                "Total": f"${qty * price:.2f}",
                "Order ID": order_id,
            },
            color=self.colors[AlertLevel.WARNING if not is_paper else AlertLevel.INFO],
        )
        return await self.send_alert(alert)

    async def notify_confirmation_required(
        self,
        symbol: str,
        direction: str,
        qty: Decimal,
        entry: Decimal,
        stop: Decimal,
        target: Decimal,
        order_id: str,
    ) -> bool:
        """Notify that confirmation is required for trade."""
        alert = TradeAlert(
            level=AlertLevel.CONFIRM,
            title=f"🔔 Confirmation Required: {direction} {symbol}",
            description=f"Approve or reject order {order_id}",
            fields={
                "Symbol": symbol,
                "Direction": direction,
                "Quantity": str(qty),
                "Entry": f"${entry:.2f}",
                "Stop Loss": f"${stop:.2f}",
                "Target": f"${target:.2f}",
                "Risk": f"${qty * abs(entry - stop):.2f}",
                "Order ID": order_id,
            },
            color=self.colors[AlertLevel.CONFIRM],
            requires_confirmation=True,
            order_id=order_id,
        )
        return await self.send_alert(alert)

    async def notify_circuit_breaker(
        self, breaker_type: str, reason: str, active_count: int
    ) -> bool:
        """Notify about circuit breaker trip."""
        alert = TradeAlert(
            level=AlertLevel.CRITICAL,
            title=f"🚨 CIRCUIT BREAKER: {breaker_type}",
            description="Trading halted due to safety trigger",
            fields={
                "Breaker Type": breaker_type,
                "Reason": reason,
                "Active Breakers": str(active_count),
                "Action": "All new trades blocked",
            },
            color=self.colors[AlertLevel.CRITICAL],
        )
        return await self.send_alert(alert)

    async def notify_daily_summary(
        self,
        date: str,
        pnl: Decimal,
        pnl_pct: Decimal,
        trades: int,
        wins: int,
        losses: int,
    ) -> bool:
        """Send daily performance summary."""
        win_rate = (wins / trades * 100) if trades > 0 else 0
        pnl_emoji = "📈" if pnl >= 0 else "📉"

        alert = TradeAlert(
            level=AlertLevel.INFO,
            title=f"{pnl_emoji} Daily Summary - {date}",
            description=f"P&L: ${pnl:.2f} ({pnl_pct:+.2%})",
            fields={
                "Total Trades": str(trades),
                "Wins": str(wins),
                "Losses": str(losses),
                "Win Rate": f"{win_rate:.1f}%",
                "Net P&L": f"${pnl:.2f}",
                "Return": f"{pnl_pct:+.2%}",
            },
            color=self.colors[AlertLevel.INFO] if pnl >= 0 else self.colors[AlertLevel.WARNING],
        )
        return await self.send_alert(alert)

    async def notify_risk_rejection(
        self, symbol: str, reason: str, failed_checks: list[str]
    ) -> bool:
        """Notify about trade rejection by risk manager."""
        alert = TradeAlert(
            level=AlertLevel.WARNING,
            title=f"⛔ Trade Rejected: {symbol}",
            description=reason,
            fields={
                "Symbol": symbol,
                "Failed Checks": ", ".join(failed_checks),
                "Action": "Trade not executed",
            },
            color=self.colors[AlertLevel.WARNING],
        )
        return await self.send_alert(alert)
