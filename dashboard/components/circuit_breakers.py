"""Circuit breaker status component."""

from datetime import timedelta

import streamlit as st

from dashboard.config import COLORS
from dashboard.utils.data_loader import load_circuit_breakers
from dashboard.utils.formatters import format_timestamp


@st.fragment(run_every=timedelta(seconds=5))
def render_circuit_breakers():
    """Render circuit breaker status panel."""
    st.subheader("Circuit Breakers")

    # Load circuit breaker data
    breakers_df = load_circuit_breakers()

    # Define all circuit breaker types
    all_breaker_types = [
        "DAILY_LOSS_LIMIT",
        "CONSECUTIVE_LOSSES",
        "MAX_POSITIONS",
        "MAX_DAILY_TRADES",
        "PORTFOLIO_HEAT",
        "VOLATILITY_SPIKE",
        "MANUAL_KILL_SWITCH",
    ]

    breaker_names = {
        "DAILY_LOSS_LIMIT": "Daily Loss Limit",
        "CONSECUTIVE_LOSSES": "Consecutive Losses",
        "MAX_POSITIONS": "Max Positions",
        "MAX_DAILY_TRADES": "Max Daily Trades",
        "PORTFOLIO_HEAT": "Portfolio Heat",
        "VOLATILITY_SPIKE": "Volatility Spike",
        "MANUAL_KILL_SWITCH": "Kill Switch",
    }

    # Get active breakers
    active_breakers = set()
    if not breakers_df.empty:
        active_df = breakers_df[breakers_df["is_active"]]
        active_breakers = set(active_df["breaker_type"].unique())

    # Display breaker status
    for breaker_type in all_breaker_types:
        is_active = breaker_type in active_breakers

        # Status indicator
        if is_active:
            icon = "🔴"
            status_text = "ACTIVE"
            status_color = COLORS["critical"]
        else:
            icon = "🟢"
            status_text = "OK"
            status_color = COLORS["profit"]

        # Breaker name
        name = breaker_names.get(breaker_type, breaker_type)

        # Display as columns
        col1, col2, col3 = st.columns([1, 3, 2])

        with col1:
            st.write(icon)

        with col2:
            st.write(f"**{name}**")

        with col3:
            st.markdown(f":{status_color}[{status_text}]")

        # Show details if active
        if is_active and not breakers_df.empty:
            active_breaker = breakers_df[
                (breakers_df["breaker_type"] == breaker_type) & (breakers_df["is_active"])
            ]

            if not active_breaker.empty:
                breaker = active_breaker.iloc[0]

                with st.expander(f"Details - {name}", expanded=False):
                    st.write(f"**Triggered:** {format_timestamp(breaker['triggered_at'])}")
                    st.write(f"**Reason:** {breaker['reason']}")

                    # Calculate time elapsed
                    from datetime import datetime

                    elapsed = datetime.now() - breaker["triggered_at"]
                    hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
                    minutes, seconds = divmod(remainder, 60)

                    st.write(f"**Duration:** {hours}h {minutes}m {seconds}s")

    # Summary metrics
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Active Breakers", len(active_breakers))

    with col2:
        total_breakers = len(all_breaker_types)
        healthy_pct = ((total_breakers - len(active_breakers)) / total_breakers) * 100
        st.metric("System Health", f"{healthy_pct:.0f}%")

    # Warning if any breakers are active
    if len(active_breakers) > 0:
        st.warning(
            f"⚠️ **{len(active_breakers)} circuit breaker(s) active!** "
            "Trading is halted. Check breaker details above."
        )
