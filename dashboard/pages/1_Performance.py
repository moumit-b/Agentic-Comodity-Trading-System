"""Performance analytics page."""

import streamlit as st

from dashboard.config import DASHBOARD_TITLE, PAGE_ICON
from dashboard.utils.chart_factory import create_equity_curve
from dashboard.utils.data_loader import (
    load_account_status,
    load_daily_performance,
    load_executions,
    load_positions,
)
from dashboard.utils.formatters import format_currency, format_percentage

# Page configuration
st.set_page_config(
    page_title=f"Performance - {DASHBOARD_TITLE}",
    page_icon=PAGE_ICON,
    layout="wide",
)

st.title("📊 Performance Analytics")

# Load data
account_status = load_account_status()
daily_performance_df = load_daily_performance()
executions_df = load_executions(limit=1000)
positions_df = load_positions()

# Account summary
st.header("Account Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    balance = account_status["balance"]
    st.metric("Account Balance", format_currency(balance))

with col2:
    buying_power = account_status["buying_power"]
    st.metric("Buying Power", format_currency(buying_power))

with col3:
    portfolio_value = account_status["portfolio_value"]
    st.metric("Portfolio Value", format_currency(portfolio_value))

with col4:
    cash = account_status["cash"]
    st.metric("Cash", format_currency(cash))

st.divider()

# Equity curve
st.header("Equity Curve")

if not daily_performance_df.empty:
    # Calculate starting balance (assume first day is starting balance)
    initial_balance = float(balance)

    fig = create_equity_curve(daily_performance_df, initial_balance=initial_balance)
    st.plotly_chart(fig, use_container_width=True)

    # Calculate metrics
    total_pnl = daily_performance_df["daily_pnl"].sum()
    total_return_pct = (total_pnl / initial_balance) * 100

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total P&L", format_currency(total_pnl), f"{total_return_pct:+.2f}%")

    with col2:
        max_daily_pnl = daily_performance_df["daily_pnl"].max()
        st.metric("Best Day", format_currency(max_daily_pnl))

    with col3:
        min_daily_pnl = daily_performance_df["daily_pnl"].min()
        st.metric("Worst Day", format_currency(min_daily_pnl))

else:
    st.info("No performance data available yet. Start trading to see your equity curve.")

st.divider()

# Trading statistics
st.header("Trading Statistics")

if not executions_df.empty:
    # Filter to filled executions only
    filled_executions = executions_df[executions_df["status"] == "FILLED"]

    if not filled_executions.empty:
        total_trades = len(filled_executions)

        # Calculate win rate (would need position close data for accurate win rate)
        # For now, show execution statistics

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Executions", total_trades)

        with col2:
            # Count by side
            long_count = len(filled_executions[filled_executions["side"] == "LONG"])
            short_count = len(filled_executions[filled_executions["side"] == "SHORT"])
            st.metric("Long Trades", long_count)
            st.caption(f"Short: {short_count}")

        with col3:
            # Average position size
            avg_qty = filled_executions["qty"].mean()
            st.metric("Avg Position Size", f"{avg_qty:.0f} shares")

        with col4:
            # Symbols traded
            symbols_traded = filled_executions["symbol"].nunique()
            st.metric("Symbols Traded", symbols_traded)

        st.divider()

        # Execution history table
        st.subheader("Recent Executions")

        # Display table
        display_df = filled_executions.head(20).copy()
        display_df["created_at"] = display_df["created_at"].dt.strftime("%Y-%m-%d %H:%M")
        display_df["filled_price"] = display_df["filled_price"].apply(
            lambda x: format_currency(x) if x else "N/A"
        )

        st.dataframe(
            display_df[["created_at", "symbol", "side", "qty", "filled_price", "status"]],
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info("No filled executions yet.")

else:
    st.info("No execution data available.")

st.divider()

# Daily performance breakdown
st.header("Daily Performance")

if not daily_performance_df.empty:
    # Show recent performance
    recent_days = daily_performance_df.head(30).copy()

    # Format for display
    recent_days["date"] = recent_days["date"].astype(str)
    recent_days["daily_pnl"] = recent_days["daily_pnl"].apply(format_currency)

    st.dataframe(
        recent_days[["date", "trades_count", "daily_pnl", "consecutive_losses"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "date": "Date",
            "trades_count": "Trades",
            "daily_pnl": "P&L",
            "consecutive_losses": "Consecutive Losses",
        },
    )

    # Calculate statistics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        winning_days = len(daily_performance_df[daily_performance_df["daily_pnl"] > 0])
        total_days = len(daily_performance_df)
        win_rate = (winning_days / total_days * 100) if total_days > 0 else 0
        st.metric("Winning Days", f"{winning_days}/{total_days}", f"{win_rate:.1f}%")

    with col2:
        avg_daily_pnl = daily_performance_df["daily_pnl"].mean()
        st.metric("Avg Daily P&L", format_currency(avg_daily_pnl))

    with col3:
        max_consecutive_losses = daily_performance_df["consecutive_losses"].max()
        st.metric("Max Consecutive Losses", int(max_consecutive_losses))

    with col4:
        avg_trades_per_day = daily_performance_df["trades_count"].mean()
        st.metric("Avg Trades/Day", f"{avg_trades_per_day:.1f}")

else:
    st.info("No daily performance data available.")

# Sidebar
with st.sidebar:
    st.header("Performance Filters")

    st.info("Filters coming soon:\n- Date range\n- Symbol filter\n- Strategy filter")

    st.divider()

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
