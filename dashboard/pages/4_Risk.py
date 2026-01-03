"""Risk management and settlement tracking page."""

import asyncio

import streamlit as st

from dashboard.config import DASHBOARD_TITLE, PAGE_ICON
from dashboard.utils.data_loader import (
    load_account_status,
    load_positions,
    load_settlement_calendar,
)
from dashboard.utils.formatters import format_currency, format_date
from src.agents.risk_manager import RiskManagerAgent
from src.core.config import TradingConfig

# Page configuration
st.set_page_config(
    page_title=f"Risk - {DASHBOARD_TITLE}",
    page_icon=PAGE_ICON,
    layout="wide",
)


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


st.title("⚠️ Risk Management")

# Load data
config = TradingConfig()
account_status = load_account_status()
positions_df = load_positions()
settlement_df = load_settlement_calendar()

# Portfolio risk metrics
st.header("Portfolio Risk Metrics")

# Calculate portfolio heat
risk_manager = RiskManagerAgent(config)
try:
    portfolio_risk = run_async(risk_manager.calculate_portfolio_heat(account_status["balance"]))
    portfolio_heat_pct = float(portfolio_risk.current_heat * 100)
    heat_limit_pct = float(config.max_portfolio_heat_pct * 100)
except Exception as e:
    st.error(f"Failed to calculate portfolio heat: {e}")
    portfolio_heat_pct = 0.0
    heat_limit_pct = 100.0

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Portfolio Heat", f"{portfolio_heat_pct:.1f}%", f"Limit: {heat_limit_pct:.0f}%")

with col2:
    open_positions = len(positions_df) if not positions_df.empty else 0
    max_positions = config.max_positions
    st.metric("Open Positions", f"{open_positions}/{max_positions}")

with col3:
    risk_per_trade_pct = float(config.risk_per_trade_pct * 100)
    st.metric("Risk Per Trade", f"{risk_per_trade_pct:.2f}%")

with col4:
    daily_loss_limit = float(config.daily_loss_limit_pct * 100)
    st.metric("Daily Loss Limit", f"{daily_loss_limit:.1f}%")

st.divider()

# Position heat map
st.header("Position Heat Map")

if not positions_df.empty:
    # Calculate risk per position
    position_risks = []

    for _, pos in positions_df.iterrows():
        entry = pos["entry_price"]
        stop = pos["stop_loss"]
        qty = pos["qty"]

        if stop is not None and entry > 0:
            risk_per_share = abs(entry - stop)
            total_risk = risk_per_share * qty
            risk_pct = (total_risk / account_status["balance"]) * 100

            position_risks.append(
                {
                    "Symbol": pos["symbol"],
                    "Side": pos["side"],
                    "Qty": int(qty),
                    "Entry": entry,
                    "Stop": stop,
                    "Risk $": total_risk,
                    "Risk %": risk_pct,
                }
            )

    if position_risks:
        import pandas as pd

        risk_df = pd.DataFrame(position_risks)

        # Format columns
        risk_df["Entry"] = risk_df["Entry"].apply(format_currency)
        risk_df["Stop"] = risk_df["Stop"].apply(format_currency)
        risk_df["Risk $"] = risk_df["Risk $"].apply(format_currency)
        risk_df["Risk %"] = risk_df["Risk %"].apply(lambda x: f"{x:.2f}%")

        st.dataframe(risk_df, use_container_width=True, hide_index=True)

        # Visual heat map
        st.subheader("Risk Distribution")

        risk_values = [pr["Risk %"] for pr in position_risks]
        symbols = [pr["Symbol"] for pr in position_risks]

        col1, col2 = st.columns([2, 1])

        with col1:
            import plotly.graph_objects as go

            fig = go.Figure(
                data=[
                    go.Bar(
                        x=symbols,
                        y=risk_values,
                        marker_color=[
                            "#FF4B4B" if r > 1.5 else "#FFA500" if r > 1.0 else "#00D4AA"
                            for r in risk_values
                        ],
                    )
                ]
            )

            fig.update_layout(
                title="Risk per Position (%)",
                xaxis_title="Symbol",
                yaxis_title="Risk %",
                template="plotly_dark",
                height=300,
            )

            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.write("**Risk Levels:**")
            st.write("🟢 Low: < 1.0%")
            st.write("🟡 Medium: 1.0% - 1.5%")
            st.write("🔴 High: > 1.5%")

            st.divider()

            total_risk = sum([pr["Risk %"] for pr in position_risks])
            st.metric("Total Portfolio Risk", f"{total_risk:.2f}%")

    else:
        st.info("No position risk data available (missing stop loss levels)")

else:
    st.info("No open positions to analyze")

st.divider()

# Settlement calendar (T+1 tracking)
st.header("Settlement Calendar (T+1)")

st.write(
    "Cash account settlement tracking. Funds from sales settle on **T+1** (next business day)."
)

if not settlement_df.empty:
    # Format for display
    display_df = settlement_df.copy()

    display_df["trade_date"] = display_df["trade_date"].apply(format_date)
    display_df["settlement_date"] = display_df["settlement_date"].apply(format_date)
    display_df["proceeds"] = display_df["proceeds"].apply(format_currency)
    display_df["settled"] = display_df["settled"].apply(
        lambda x: "✓ Settled" if x else "⏳ Pending"
    )

    st.dataframe(
        display_df[["trade_date", "settlement_date", "symbol", "qty", "proceeds", "settled"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "trade_date": "Trade Date",
            "settlement_date": "Settlement Date",
            "symbol": "Symbol",
            "qty": "Quantity",
            "proceeds": "Proceeds",
            "settled": "Status",
        },
    )

    # Settlement summary
    col1, col2, col3 = st.columns(3)

    with col1:
        total_settled = display_df[display_df["settled"] == "✓ Settled"]["proceeds"].count()
        st.metric("Settled Transactions", total_settled)

    with col2:
        total_pending = display_df[display_df["settled"] == "⏳ Pending"]["proceeds"].count()
        st.metric("Pending Settlement", total_pending)

    with col3:
        # Calculate total pending amount
        pending_df = settlement_df[settlement_df["settled"] == False]
        if not pending_df.empty:
            pending_amount = pending_df["proceeds"].sum()
            st.metric("Pending Cash", format_currency(pending_amount))

else:
    st.info("No settlement records. Settlement tracking begins after closing positions.")

st.divider()

# Risk limits configuration
st.header("Risk Limits & Thresholds")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Position Limits")

    st.write(f"**Max Positions:** {config.max_positions}")
    st.write(f"**Max Trades Per Day:** {config.max_trades_per_day}")
    st.write(f"**Max Portfolio Heat:** {float(config.max_portfolio_heat_pct * 100):.0f}%")

    st.divider()

    st.subheader("Loss Protection")

    st.write(f"**Daily Loss Limit:** {float(config.daily_loss_limit_pct * 100):.1f}%")
    st.write(f"**Daily Profit Target:** {float(config.daily_profit_target_pct * 100):.1f}%")
    st.write(f"**Max Consecutive Losses:** {config.max_consecutive_losses}")

with col2:
    st.subheader("Trade Sizing")

    st.write(f"**Risk Per Trade:** {float(config.risk_per_trade_pct * 100):.2f}%")
    st.write(f"**Daily Profit Target:** {float(config.daily_profit_target_pct * 100):.1f}%")

    st.divider()

    st.subheader("Volatility Controls")

    st.write("**Volatility Spike Multiplier:** 2.5x")
    st.caption("Circuit breaker trips if market volatility exceeds this multiple")

# Sidebar
with st.sidebar:
    st.header("Risk Summary")

    # Overall risk level
    if portfolio_heat_pct > 60:
        risk_level = "🔴 High"
        risk_color = "error"
    elif portfolio_heat_pct > 30:
        risk_level = "🟡 Medium"
        risk_color = "warning"
    else:
        risk_level = "🟢 Low"
        risk_color = "success"

    st.metric("Risk Level", risk_level)

    st.divider()

    st.write("**Quick Actions:**")

    if st.button("Calculate VaR", use_container_width=True):
        st.info("VaR calculation coming soon")

    if st.button("Run Stress Test", use_container_width=True):
        st.info("Stress testing coming soon")

    st.divider()

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
