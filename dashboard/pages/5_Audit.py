"""Audit trail page for decision tracking and compliance."""

import streamlit as st

from dashboard.config import DASHBOARD_TITLE, PAGE_ICON
from dashboard.utils.data_loader import load_decisions, load_executions, load_signals
from dashboard.utils.formatters import (
    format_currency,
    format_percentage,
    format_timestamp,
    shorten_text,
)

# Page configuration
st.set_page_config(
    page_title=f"Audit - {DASHBOARD_TITLE}",
    page_icon=PAGE_ICON,
    layout="wide",
)

st.title("📝 Decision Audit Trail")

st.write(
    "Complete audit trail of all trading decisions. This page provides transparency "
    "and compliance documentation for regulatory purposes."
)

# Load data
decisions_df = load_decisions(limit=1000)
signals_df = load_signals(limit=1000)
executions_df = load_executions(limit=1000)

if decisions_df.empty:
    st.info("No decisions logged yet. Decisions will appear here once signals are evaluated.")
    st.stop()

# Summary metrics
st.header("Audit Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Decisions", len(decisions_df))

with col2:
    approved_count = len(decisions_df[decisions_df["approved"] == True])
    approval_rate = (approved_count / len(decisions_df) * 100) if len(decisions_df) > 0 else 0
    st.metric("Approved", approved_count, f"{approval_rate:.1f}%")

with col3:
    rejected_count = len(decisions_df[decisions_df["approved"] == False])
    rejection_rate = (rejected_count / len(decisions_df) * 100) if len(decisions_df) > 0 else 0
    st.metric("Rejected", rejected_count, f"{rejection_rate:.1f}%")

with col4:
    # Average risk per approved trade
    approved_decisions = decisions_df[decisions_df["approved"] == True]
    if not approved_decisions.empty:
        avg_risk_pct = approved_decisions["risk_pct"].mean()
        st.metric("Avg Risk/Trade", format_percentage(avg_risk_pct))
    else:
        st.metric("Avg Risk/Trade", "N/A")

st.divider()

# Filters
st.header("Filter Decisions")

col1, col2, col3 = st.columns(3)

with col1:
    # Approval status filter
    status_options = ["All", "Approved", "Rejected"]
    selected_status = st.selectbox("Status", options=status_options, key="filter_status")

with col2:
    # Symbol filter
    symbols = ["All"] + sorted(decisions_df["symbol"].unique().tolist())
    selected_symbol = st.selectbox("Symbol", options=symbols, key="filter_symbol")

with col3:
    # Date range (simplified)
    st.write("**Date Range:**")
    st.caption("Coming soon")

# Apply filters
filtered_df = decisions_df.copy()

if selected_status == "Approved":
    filtered_df = filtered_df[filtered_df["approved"] == True]
elif selected_status == "Rejected":
    filtered_df = filtered_df[filtered_df["approved"] == False]

if selected_symbol != "All":
    filtered_df = filtered_df[filtered_df["symbol"] == selected_symbol]

st.caption(f"Showing {len(filtered_df)} of {len(decisions_df)} decisions")

st.divider()

# Decision table
st.header("Decision History")

if not filtered_df.empty:
    # Display each decision with expandable details
    for idx, decision in filtered_df.iterrows():
        # Find matching signal
        matching_signal = None
        if not signals_df.empty:
            matching = signals_df[
                (signals_df["symbol"] == decision["symbol"])
                & (abs((signals_df["timestamp"] - decision["timestamp"]).total_seconds()) < 60)
            ]
            if not matching.empty:
                matching_signal = matching.iloc[0]

        # Decision card
        with st.container():
            # Header row
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.write(
                    f"**{decision['symbol']}** - "
                    f"{format_timestamp(decision['timestamp'], '%Y-%m-%d %H:%M:%S')}"
                )

            with col2:
                if matching_signal is not None:
                    st.caption(f"Strategy: {matching_signal['strategy_name']}")
                else:
                    st.caption("Strategy: Unknown")

            with col3:
                if decision["approved"]:
                    st.markdown(":green[✓ APPROVED]")
                else:
                    st.markdown(":red[✗ REJECTED]")

            # Expandable details
            with st.expander("View Details", expanded=False):
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Decision Details**")
                    st.write(f"Timestamp: {format_timestamp(decision['timestamp'])}")
                    st.write(f"Symbol: {decision['symbol']}")
                    st.write(f"Approved: {'Yes' if decision['approved'] else 'No'}")

                    if decision["approved"]:
                        st.write(f"Position Size: {decision['position_size']} shares")
                        st.write(f"Risk Amount: {format_currency(decision['risk_amount'])}")
                        st.write(f"Risk %: {format_percentage(decision['risk_pct'])}")
                    else:
                        st.write("**Rejection Reason:**")
                        st.error(decision["rejection_reason"])

                with col2:
                    if matching_signal is not None:
                        st.write("**Signal Details**")
                        st.write(f"Direction: {matching_signal['direction']}")
                        st.write(f"Strategy: {matching_signal['strategy_name']}")
                        st.write(f"Timeframe: {matching_signal['timeframe']}")
                        st.write(f"Confidence: {format_percentage(matching_signal['confidence'])}")
                        st.write(f"Entry: {format_currency(matching_signal['suggested_entry'])}")
                        st.write(f"Stop: {format_currency(matching_signal['suggested_stop'])}")
                        st.write(f"Target: {format_currency(matching_signal['suggested_target'])}")

                # Execution status
                if decision["approved"]:
                    # Find matching execution
                    matching_execution = None
                    if not executions_df.empty:
                        matching_exec = executions_df[
                            (executions_df["symbol"] == decision["symbol"])
                            & (
                                abs(
                                    (
                                        executions_df["created_at"] - decision["timestamp"]
                                    ).total_seconds()
                                )
                                < 300
                            )
                        ]
                        if not matching_exec.empty:
                            matching_execution = matching_exec.iloc[0]

                    if matching_execution is not None:
                        st.divider()
                        st.write("**Execution Status**")

                        exec_col1, exec_col2 = st.columns(2)

                        with exec_col1:
                            st.write(f"Status: {matching_execution['status']}")
                            st.write(f"Order ID: {matching_execution['id']}")

                        with exec_col2:
                            if matching_execution["filled_price"]:
                                st.write(
                                    f"Filled Price: {format_currency(matching_execution['filled_price'])}"
                                )
                            st.write(
                                f"Created: {format_timestamp(matching_execution['created_at'])}"
                            )

            st.markdown("---")

    # Export functionality
    if st.button("📥 Export Audit Trail to CSV"):
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="audit_trail_export.csv",
            mime="text/csv",
        )

else:
    st.info("No decisions match the selected filters.")

st.divider()

# Rejection analysis
st.header("Rejection Analysis")

if not decisions_df.empty:
    rejected_df = decisions_df[decisions_df["approved"] == False]

    if not rejected_df.empty:
        # Count rejection reasons
        rejection_reasons = rejected_df["rejection_reason"].value_counts()

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Top Rejection Reasons")

            for reason, count in rejection_reasons.head(10).items():
                pct = (count / len(rejected_df)) * 100
                st.write(f"**{shorten_text(reason, 80)}**")
                st.progress(int(pct), text=f"{count} occurrences ({pct:.1f}%)")

        with col2:
            st.subheader("Rejection Stats")

            st.metric("Total Rejections", len(rejected_df))

            rejection_rate = (len(rejected_df) / len(decisions_df)) * 100
            st.metric("Rejection Rate", f"{rejection_rate:.1f}%")

            unique_reasons = rejected_df["rejection_reason"].nunique()
            st.metric("Unique Reasons", unique_reasons)

    else:
        st.success("✓ No rejections! All decisions were approved.")

else:
    st.info("No rejection data available.")

# Sidebar
with st.sidebar:
    st.header("Audit Controls")

    st.info(
        "**Compliance Note:**\n\n"
        "This audit trail maintains a complete record of all trading decisions "
        "for regulatory compliance and performance review."
    )

    st.divider()

    st.write("**Export Options:**")

    if st.button("Export Full Audit Trail", use_container_width=True):
        st.info("Full export functionality coming soon")

    if st.button("Generate Compliance Report", use_container_width=True):
        st.info("Compliance report generation coming soon")

    st.divider()

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()

    st.divider()

    st.caption(
        f"**Audit Coverage:**\n"
        f"Total Decisions: {len(decisions_df)}\n"
        f"Date Range: {format_timestamp(decisions_df['timestamp'].min(), '%Y-%m-%d')} "
        f"to {format_timestamp(decisions_df['timestamp'].max(), '%Y-%m-%d')}"
        if not decisions_df.empty
        else "No data"
    )
