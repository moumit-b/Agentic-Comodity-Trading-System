"""Signal feed component showing recent trading signals."""

import streamlit as st

from dashboard.config import COLORS, MAX_SIGNAL_DISPLAY
from dashboard.utils.data_loader import load_decisions, load_signals
from dashboard.utils.formatters import (
    format_confidence,
    format_currency,
    format_timestamp,
    shorten_text,
)


def render_signal_feed():
    """Render real-time signal feed with approval status."""
    st.subheader("Signal Feed")

    # Load signals and decisions
    signals_df = load_signals(limit=MAX_SIGNAL_DISPLAY)
    decisions_df = load_decisions(limit=MAX_SIGNAL_DISPLAY)

    if signals_df.empty:
        st.info("No signals generated yet. Waiting for market data and strategy execution.")
        return

    # Display filters
    col1, col2 = st.columns(2)

    with col1:
        # Strategy filter
        strategies = ["All"] + sorted(signals_df["strategy_name"].unique().tolist())
        selected_strategy = st.selectbox(
            "Strategy",
            options=strategies,
            key="signal_feed_strategy",
        )

    with col2:
        # Direction filter
        directions = ["All", "LONG", "SHORT"]
        selected_direction = st.selectbox(
            "Direction",
            options=directions,
            key="signal_feed_direction",
        )

    # Filter signals
    filtered_df = signals_df.copy()

    if selected_strategy != "All":
        filtered_df = filtered_df[filtered_df["strategy_name"] == selected_strategy]

    if selected_direction != "All":
        filtered_df = filtered_df[filtered_df["direction"] == selected_direction]

    # Display signal count
    st.caption(f"Showing {len(filtered_df)} of {len(signals_df)} signals")

    # Display signals
    for idx, signal in filtered_df.iterrows():
        # Get corresponding decision if exists
        decision = None
        if not decisions_df.empty:
            matching_decisions = decisions_df[
                (decisions_df["symbol"] == signal["symbol"])
                & (abs((decisions_df["timestamp"] - signal["timestamp"]).total_seconds()) < 60)
            ]
            if not matching_decisions.empty:
                decision = matching_decisions.iloc[0]

        # Signal card
        with st.container():
            # Header row
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                # Direction indicator
                direction_icon = "📈" if signal["direction"] == "LONG" else "📉"
                direction_color = (
                    COLORS["profit"] if signal["direction"] == "LONG" else COLORS["loss"]
                )

                st.markdown(
                    f"{direction_icon} **{signal['symbol']}** "
                    f":{direction_color}[{signal['direction']}]"
                )

            with col2:
                st.caption(f"**{signal['strategy_name']}** • {signal['timeframe']}")

            with col3:
                # Approval status
                if decision is not None:
                    if decision["approved"]:
                        st.markdown(f":green[✓ APPROVED]")
                    else:
                        st.markdown(f":red[✗ REJECTED]")
                else:
                    st.markdown(f":gray[PENDING]")

            # Details row
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.caption("Entry")
                st.write(format_currency(signal["suggested_entry"]))

            with col2:
                st.caption("Stop")
                st.write(format_currency(signal["suggested_stop"]))

            with col3:
                st.caption("Target")
                st.write(format_currency(signal["suggested_target"]))

            with col4:
                st.caption("Confidence")
                st.markdown(format_confidence(signal["confidence"]))

            # Expandable details
            with st.expander("Signal Details", expanded=False):
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Signal Info**")
                    st.write(f"Timestamp: {format_timestamp(signal['timestamp'])}")
                    st.write(f"Signal Strength: {signal['signal_strength']:.1f}")
                    st.write(f"Confidence: {signal['confidence']:.2%}")

                with col2:
                    st.write("**Price Levels**")
                    st.write(f"Entry: {format_currency(signal['suggested_entry'])}")
                    st.write(f"Stop Loss: {format_currency(signal['suggested_stop'])}")
                    st.write(f"Take Profit: {format_currency(signal['suggested_target'])}")

                    # Calculate R:R ratio
                    risk = abs(signal["suggested_entry"] - signal["suggested_stop"])
                    reward = abs(signal["suggested_target"] - signal["suggested_entry"])
                    if risk > 0:
                        rr_ratio = reward / risk
                        st.write(f"Risk:Reward: 1:{rr_ratio:.2f}")

                # Show decision details if available
                if decision is not None:
                    st.divider()
                    st.write("**Decision**")

                    if decision["approved"]:
                        st.success(
                            f"✓ Approved - Position Size: {decision['position_size']} shares"
                        )
                        st.write(
                            f"Risk: {format_currency(decision['risk_amount'])} ({decision['risk_pct']:.2%})"
                        )
                    else:
                        st.error(f"✗ Rejected: {shorten_text(decision['rejection_reason'], 100)}")

            st.divider()

    # Summary metrics at bottom
    if not filtered_df.empty:
        st.subheader("Feed Summary")

        col1, col2, col3 = st.columns(3)

        with col1:
            long_count = len(filtered_df[filtered_df["direction"] == "LONG"])
            short_count = len(filtered_df[filtered_df["direction"] == "SHORT"])
            st.metric("Long Signals", long_count)
            st.metric("Short Signals", short_count)

        with col2:
            avg_confidence = filtered_df["confidence"].mean()
            st.metric("Avg Confidence", f"{avg_confidence:.1%}")

            avg_strength = filtered_df["signal_strength"].mean()
            st.metric("Avg Strength", f"{avg_strength:.1f}")

        with col3:
            # Approval rate
            if not decisions_df.empty and len(filtered_df) > 0:
                # Match signals with decisions
                approved_count = 0
                total_with_decisions = 0

                for _, signal in filtered_df.iterrows():
                    matching = decisions_df[
                        (decisions_df["symbol"] == signal["symbol"])
                        & (
                            abs((decisions_df["timestamp"] - signal["timestamp"]).total_seconds())
                            < 60
                        )
                    ]
                    if not matching.empty:
                        total_with_decisions += 1
                        if matching.iloc[0]["approved"]:
                            approved_count += 1

                if total_with_decisions > 0:
                    approval_rate = (approved_count / total_with_decisions) * 100
                    st.metric("Approval Rate", f"{approval_rate:.1f}%")
                else:
                    st.metric("Approval Rate", "N/A")
            else:
                st.metric("Approval Rate", "N/A")
