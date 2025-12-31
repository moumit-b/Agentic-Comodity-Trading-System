"""Positions table component showing open positions with P&L."""

import streamlit as st

from dashboard.config import COLORS
from dashboard.utils.data_loader import load_positions
from dashboard.utils.formatters import (
    format_currency,
    format_pnl,
    format_percentage,
    format_shares,
    format_timestamp,
)


def render_positions_table():
    """Render open positions table."""
    st.subheader("Open Positions")

    positions_df = load_positions()

    if positions_df.empty:
        st.info("No open positions")
        return

    # Calculate total P&L
    total_pnl = positions_df["unrealized_pnl"].sum()
    total_pnl_pct = positions_df["unrealized_pnl_pct"].mean() if len(positions_df) > 0 else 0

    # Show summary
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Open Positions", len(positions_df))

    with col2:
        st.metric("Total P&L", format_pnl(total_pnl))

    with col3:
        st.metric("Avg P&L %", format_percentage(total_pnl_pct))

    # Format the dataframe for display
    display_df = positions_df.copy()

    # Format columns
    display_df["entry_price"] = display_df["entry_price"].apply(lambda x: format_currency(x))
    display_df["current_price"] = display_df["current_price"].apply(lambda x: format_currency(x))
    display_df["stop_loss"] = display_df["stop_loss"].apply(
        lambda x: format_currency(x) if x else "N/A"
    )
    display_df["take_profit"] = display_df["take_profit"].apply(
        lambda x: format_currency(x) if x else "N/A"
    )
    display_df["qty"] = display_df["qty"].apply(format_shares)

    # Format P&L columns with color
    def format_pnl_cell(value):
        if value > 0:
            return f"<span style='color:{COLORS['profit']}'>{format_pnl(value)}</span>"
        elif value < 0:
            return f"<span style='color:{COLORS['loss']}'>{format_pnl(value)}</span>"
        else:
            return format_pnl(value)

    def format_pnl_pct_cell(value):
        formatted = format_percentage(value)
        if value > 0:
            return f"<span style='color:{COLORS['profit']}'>{formatted}</span>"
        elif value < 0:
            return f"<span style='color:{COLORS['loss']}'>{formatted}</span>"
        else:
            return formatted

    display_df["unrealized_pnl_html"] = display_df["unrealized_pnl"].apply(format_pnl_cell)
    display_df["unrealized_pnl_pct_html"] = display_df["unrealized_pnl_pct"].apply(
        format_pnl_pct_cell
    )

    # Format timestamp
    display_df["opened_at"] = display_df["opened_at"].apply(
        lambda x: format_timestamp(x, "%Y-%m-%d %H:%M")
    )

    # Select and rename columns for display
    final_df = display_df[
        [
            "symbol",
            "side",
            "qty",
            "entry_price",
            "current_price",
            "unrealized_pnl_html",
            "unrealized_pnl_pct_html",
            "stop_loss",
            "take_profit",
            "opened_at",
        ]
    ]

    final_df.columns = [
        "Symbol",
        "Side",
        "Qty",
        "Entry",
        "Current",
        "P&L ($)",
        "P&L (%)",
        "Stop",
        "Target",
        "Opened",
    ]

    # Display as HTML table with colors
    st.markdown(
        final_df.to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )

    # Optional: Add expandable detail section
    with st.expander("Position Details"):
        selected_symbol = st.selectbox(
            "Select position to view details",
            options=positions_df["symbol"].unique(),
        )

        if selected_symbol:
            pos = positions_df[positions_df["symbol"] == selected_symbol].iloc[0]

            col1, col2 = st.columns(2)

            with col1:
                st.write("**Position Info**")
                st.write(f"Symbol: {pos['symbol']}")
                st.write(f"Side: {pos['side']}")
                st.write(f"Quantity: {format_shares(pos['qty'])}")
                st.write(f"Entry Price: {format_currency(pos['entry_price'])}")
                st.write(f"Current Price: {format_currency(pos['current_price'])}")

            with col2:
                st.write("**Risk Management**")
                st.write(
                    f"Stop Loss: {format_currency(pos['stop_loss']) if pos['stop_loss'] else 'N/A'}"
                )
                st.write(
                    f"Take Profit: {format_currency(pos['take_profit']) if pos['take_profit'] else 'N/A'}"
                )
                st.write(f"Unrealized P&L: {format_pnl(pos['unrealized_pnl'])}")
                st.write(f"Unrealized P&L %: {format_percentage(pos['unrealized_pnl_pct'])}")

            st.write(f"**Opened:** {format_timestamp(pos['opened_at'])}")
