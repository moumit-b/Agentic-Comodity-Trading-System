"""Signals history and analysis page."""

import streamlit as st

from dashboard.config import DASHBOARD_TITLE, PAGE_ICON
from dashboard.utils.data_loader import load_decisions, load_signals
from dashboard.utils.formatters import (
    format_confidence,
    format_currency,
    format_percentage,
    format_timestamp,
)

# Page configuration
st.set_page_config(
    page_title=f"Signals - {DASHBOARD_TITLE}",
    page_icon=PAGE_ICON,
    layout="wide",
)

st.title("📡 Signal History & Analysis")

# Load data
signals_df = load_signals(limit=500)
decisions_df = load_decisions(limit=500)

if signals_df.empty:
    st.info(
        "No signals generated yet. The system will generate signals once market data is available."
    )
    st.stop()

# Summary metrics
st.header("Signal Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Signals", len(signals_df))

with col2:
    long_count = len(signals_df[signals_df["direction"] == "LONG"])
    long_pct = (long_count / len(signals_df) * 100) if len(signals_df) > 0 else 0
    st.metric("Long Signals", long_count, f"{long_pct:.1f}%")

with col3:
    short_count = len(signals_df[signals_df["direction"] == "SHORT"])
    short_pct = (short_count / len(signals_df) * 100) if len(signals_df) > 0 else 0
    st.metric("Short Signals", short_count, f"{short_pct:.1f}%")

with col4:
    avg_confidence = signals_df["confidence"].mean()
    st.metric("Avg Confidence", format_percentage(avg_confidence))

st.divider()

# Filters
st.header("Filter Signals")

col1, col2, col3, col4 = st.columns(4)

with col1:
    # Strategy filter
    strategies = ["All"] + sorted(signals_df["strategy_name"].unique().tolist())
    selected_strategy = st.selectbox("Strategy", options=strategies, key="filter_strategy")

with col2:
    # Direction filter
    directions = ["All", "LONG", "SHORT"]
    selected_direction = st.selectbox("Direction", options=directions, key="filter_direction")

with col3:
    # Symbol filter
    symbols = ["All"] + sorted(signals_df["symbol"].unique().tolist())
    selected_symbol = st.selectbox("Symbol", options=symbols, key="filter_symbol")

with col4:
    # Confidence threshold
    min_confidence = st.slider(
        "Min Confidence (%)",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
        key="filter_confidence",
    )

# Apply filters
filtered_df = signals_df.copy()

if selected_strategy != "All":
    filtered_df = filtered_df[filtered_df["strategy_name"] == selected_strategy]

if selected_direction != "All":
    filtered_df = filtered_df[filtered_df["direction"] == selected_direction]

if selected_symbol != "All":
    filtered_df = filtered_df[filtered_df["symbol"] == selected_symbol]

if min_confidence > 0:
    filtered_df = filtered_df[filtered_df["confidence"] >= (min_confidence / 100)]

st.caption(f"Showing {len(filtered_df)} of {len(signals_df)} signals")

st.divider()

# Signal table
st.header("Signal History")

if not filtered_df.empty:
    # Prepare display dataframe
    display_df = filtered_df.copy()

    # Format columns
    display_df["timestamp"] = display_df["timestamp"].apply(
        lambda x: format_timestamp(x, "%Y-%m-%d %H:%M")
    )
    display_df["confidence"] = display_df["confidence"].apply(lambda x: f"{x:.1%}")
    display_df["suggested_entry"] = display_df["suggested_entry"].apply(format_currency)
    display_df["suggested_stop"] = display_df["suggested_stop"].apply(format_currency)
    display_df["suggested_target"] = display_df["suggested_target"].apply(format_currency)

    # Add approval status column
    display_df["approved"] = "Unknown"

    for idx, signal in display_df.iterrows():
        # Find matching decision
        if not decisions_df.empty:
            matching = decisions_df[
                (decisions_df["symbol"] == signal["symbol"])
                & (
                    abs(
                        (
                            decisions_df["timestamp"] - signals_df.loc[idx, "timestamp"]
                        ).total_seconds()
                    )
                    < 60
                )
            ]
            if not matching.empty:
                display_df.loc[idx, "approved"] = (
                    "✓ Approved" if matching.iloc[0]["approved"] else "✗ Rejected"
                )

    # Display table
    st.dataframe(
        display_df[
            [
                "timestamp",
                "symbol",
                "direction",
                "strategy_name",
                "confidence",
                "signal_strength",
                "suggested_entry",
                "suggested_stop",
                "suggested_target",
                "approved",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp": "Time",
            "symbol": "Symbol",
            "direction": "Side",
            "strategy_name": "Strategy",
            "confidence": "Conf.",
            "signal_strength": "Strength",
            "suggested_entry": "Entry",
            "suggested_stop": "Stop",
            "suggested_target": "Target",
            "approved": "Status",
        },
    )

    # Export option
    if st.button("📥 Export to CSV", use_container_width=False):
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="signals_export.csv",
            mime="text/csv",
        )

else:
    st.info("No signals match the selected filters.")

st.divider()

# Strategy performance
st.header("Strategy Performance")

if not signals_df.empty:
    # Group by strategy
    strategy_stats = (
        signals_df.groupby("strategy_name")
        .agg(
            {
                "id": "count",
                "confidence": "mean",
                "signal_strength": "mean",
            }
        )
        .rename(
            columns={
                "id": "Signal Count",
                "confidence": "Avg Confidence",
                "signal_strength": "Avg Strength",
            }
        )
    )

    # Calculate approval rate per strategy
    if not decisions_df.empty:
        approval_rates = []

        for strategy in strategy_stats.index:
            strategy_signals = signals_df[signals_df["strategy_name"] == strategy]

            approved = 0
            total_with_decision = 0

            for _, sig in strategy_signals.iterrows():
                matching = decisions_df[
                    (decisions_df["symbol"] == sig["symbol"])
                    & (abs((decisions_df["timestamp"] - sig["timestamp"]).total_seconds()) < 60)
                ]

                if not matching.empty:
                    total_with_decision += 1
                    if matching.iloc[0]["approved"]:
                        approved += 1

            approval_rate = (approved / total_with_decision * 100) if total_with_decision > 0 else 0
            approval_rates.append(approval_rate)

        strategy_stats["Approval Rate (%)"] = approval_rates

    # Format for display
    strategy_stats["Avg Confidence"] = strategy_stats["Avg Confidence"].apply(lambda x: f"{x:.1%}")
    strategy_stats["Avg Strength"] = strategy_stats["Avg Strength"].apply(lambda x: f"{x:.1f}")

    st.dataframe(strategy_stats, use_container_width=True)

    # Visualize strategy distribution
    st.subheader("Signal Distribution by Strategy")

    strategy_counts = signals_df["strategy_name"].value_counts()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.bar_chart(strategy_counts)

    with col2:
        st.write("**Strategy Breakdown:**")
        for strategy, count in strategy_counts.items():
            pct = (count / len(signals_df)) * 100
            st.write(f"- {strategy}: {count} ({pct:.1f}%)")

st.divider()

# Symbol performance
st.header("Symbol Performance")

if not signals_df.empty:
    symbol_stats = (
        signals_df.groupby("symbol")
        .agg(
            {
                "id": "count",
                "confidence": "mean",
            }
        )
        .rename(columns={"id": "Signal Count", "confidence": "Avg Confidence"})
        .sort_values("Signal Count", ascending=False)
    )

    symbol_stats["Avg Confidence"] = symbol_stats["Avg Confidence"].apply(lambda x: f"{x:.1%}")

    st.dataframe(symbol_stats, use_container_width=True)

# Sidebar
with st.sidebar:
    st.header("Quick Stats")

    if not signals_df.empty:
        # High confidence signals
        high_conf_signals = len(signals_df[signals_df["confidence"] >= 0.8])
        st.metric("High Confidence (≥80%)", high_conf_signals)

        # Unique strategies
        unique_strategies = signals_df["strategy_name"].nunique()
        st.metric("Active Strategies", unique_strategies)

        # Recent signal
        latest_signal = signals_df.iloc[0]
        st.write("**Latest Signal:**")
        st.write(f"{latest_signal['direction']} {latest_signal['symbol']}")
        st.caption(format_timestamp(latest_signal["timestamp"]))

    st.divider()

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
