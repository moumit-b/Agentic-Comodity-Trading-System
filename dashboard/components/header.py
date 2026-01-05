"""Header component with status indicators and kill switch."""

import asyncio
import logging
from datetime import timedelta

import streamlit as st
from sqlalchemy import text

from dashboard.config import COLORS
from dashboard.utils.data_loader import load_account_status
from dashboard.utils.formatters import format_currency, format_timestamp
from src.core.config import RedisConfig, TradingConfig
from src.core.database import get_session
from src.services.circuit_breakers import CircuitBreakerService
from src.services.redis_cache import RedisCache

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


def check_database_status() -> bool:
    """Check if database is accessible."""
    try:

        async def _check():
            async with get_session() as session:
                await session.execute(text("SELECT 1"))
                return True

        return run_async(_check())
    except Exception:
        return False


def check_redis_status() -> bool:
    """Check if Redis is accessible."""
    try:
        redis = RedisCache(RedisConfig())
        redis.connect()
        return redis.health_check()
    except Exception:
        return False


@st.fragment(run_every=timedelta(seconds=5))
def render_header():
    """Render dashboard header with status indicators and controls."""
    # Get account status
    account_status = load_account_status()

    # Load config
    config = TradingConfig()

    # Create header columns
    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 3])

    # Column 1: System Status Indicators
    with col1:
        st.markdown("**System Status**")

        # Database status
        db_status = check_database_status()
        db_icon = "🟢" if db_status else "🔴"
        st.markdown(f"{db_icon} Database")

        # Redis status
        redis_status = check_redis_status()
        redis_icon = "🟢" if redis_status else "🔴"
        st.markdown(f"{redis_icon} Redis")

    # Column 2: Market & Alpaca Status
    with col2:
        st.markdown("**Market**")

        # Market open/closed
        market_icon = "🟢" if account_status["market_open"] else "🔴"
        market_text = "Open" if account_status["market_open"] else "Closed"
        st.markdown(f"{market_icon} {market_text}")

        # Alpaca connection
        alpaca_icon = "🟢" if account_status["balance"] > 0 else "🟡"
        st.markdown(f"{alpaca_icon} Alpaca")

    # Column 3: Automation Mode
    with col3:
        st.markdown("**Mode**")

        mode = config.automation_mode
        mode_colors = {
            "ADVISORY": "gray",
            "PAPER_AUTO": "orange",
            "LIVE_CONFIRM": "orange",
            "LIVE_AUTO": "red",
        }

        mode_color = mode_colors.get(mode.value, "gray")
        st.markdown(f"**:{mode_color}[{mode.value}]**")

    # Column 4: Account Balance
    with col4:
        st.markdown("**Account**")

        balance = account_status["balance"]
        buying_power = account_status["buying_power"]

        st.markdown(f"**{format_currency(balance)}**")
        st.caption(f"BP: {format_currency(buying_power)}")

    # Column 5: Kill Switch & Refresh
    with col5:
        st.markdown("**Controls**")

        # Kill switch button
        kill_switch_clicked = st.button(
            "🛑 KILL SWITCH",
            type="primary",
            use_container_width=True,
            help="Activate emergency kill switch to halt all trading",
        )

        if kill_switch_clicked:
            # Show confirmation dialog
            st.session_state["kill_switch_confirm"] = True

        # Last refresh timestamp
        st.caption(f"Updated: {format_timestamp(account_status['timestamp'], '%H:%M:%S')}")

    # Kill switch confirmation modal
    if st.session_state.get("kill_switch_confirm", False):
        with st.expander("⚠️ CONFIRM KILL SWITCH", expanded=True):
            st.warning(
                "**WARNING:** Activating the kill switch will:\n"
                "- Immediately halt all trading\n"
                "- Cancel pending orders\n"
                "- Prevent new signals from executing\n"
                "- Close open positions (if configured)\n\n"
                "This action requires manual clearance to resume trading."
            )

            col_confirm, col_cancel = st.columns(2)

            with col_confirm:
                if st.button("✅ CONFIRM KILL SWITCH", type="primary", use_container_width=True):
                    try:
                        # Activate kill switch
                        circuit_breaker = CircuitBreakerService()
                        run_async(circuit_breaker.activate_kill_switch())

                        st.success("🛑 Kill switch activated successfully!")
                        st.session_state["kill_switch_confirm"] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to activate kill switch: {e}")

            with col_cancel:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state["kill_switch_confirm"] = False
                    st.rerun()

    # Check if kill switch is active
    try:
        circuit_breaker = CircuitBreakerService()
        breaker_status = run_async(
            circuit_breaker.check_all_breakers(
                daily_pnl_pct=0,
                consecutive_losses=0,
                portfolio_heat=0,
            )
        )

        if breaker_status.is_tripped:
            st.error(
                f"⚠️ **CIRCUIT BREAKERS ACTIVE**: {', '.join(breaker_status.reasons)}",
                icon="🛑",
            )

            # Offer to clear kill switch if it's the only active breaker
            if "KILL_SWITCH" in [b.value for b in breaker_status.active_breakers]:
                if st.button("Clear Kill Switch", type="secondary"):
                    try:
                        cleared = run_async(circuit_breaker.clear_kill_switch())
                        if cleared:
                            st.success("Kill switch cleared!")
                            st.rerun()
                        else:
                            st.error("Failed to clear kill switch")
                    except Exception as e:
                        st.error(f"Error clearing kill switch: {e}")

    except Exception as e:
        logger.error(f"Failed to check circuit breakers: {e}")

    st.divider()
