"""Risk gauges component for displaying portfolio heat and risk metrics."""

import asyncio
from decimal import Decimal

import streamlit as st

from dashboard.config import RISK_THRESHOLDS
from dashboard.utils.chart_factory import create_gauge_chart
from dashboard.utils.data_loader import load_account_status, load_daily_performance, load_indicators
from src.agents.risk_manager import RiskManagerAgent
from src.core.config import TradingConfig


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


def render_risk_gauges():
    """Render risk gauge charts."""
    st.subheader("Risk Metrics")

    # Load account and daily performance data
    account_status = load_account_status()
    daily_performance_df = load_daily_performance()

    # Initialize risk manager
    config = TradingConfig()
    risk_manager = RiskManagerAgent(config)

    # Calculate portfolio heat
    try:
        portfolio_risk = run_async(risk_manager.calculate_portfolio_heat(account_status["balance"]))
        portfolio_heat_pct = float(portfolio_risk.current_heat * 100)
    except Exception:
        portfolio_heat_pct = 0.0

    # Get today's P&L percentage
    today_pnl_pct = 0.0
    if not daily_performance_df.empty:
        latest_pnl = daily_performance_df.iloc[0]["daily_pnl"]
        today_pnl_pct = float((latest_pnl / account_status["balance"]) * 100)

    # Get current RSI for primary symbol (USO)
    indicators_df = load_indicators("USO", timeframe="5m")
    current_rsi = 50.0  # Default neutral
    if not indicators_df.empty and "rsi" in indicators_df.columns:
        current_rsi = float(indicators_df["rsi"].iloc[-1])

    # Create gauge charts
    col1, col2 = st.columns(2)

    with col1:
        # Portfolio heat gauge
        heat_fig = create_gauge_chart(
            value=portfolio_heat_pct,
            title="Portfolio Heat",
            min_val=0,
            max_val=100,
            thresholds={
                "low": RISK_THRESHOLDS["portfolio_heat"]["low"] * 100,
                "medium": RISK_THRESHOLDS["portfolio_heat"]["medium"] * 100,
            },
        )
        st.plotly_chart(heat_fig, use_container_width=True)

    with col2:
        # RSI gauge
        rsi_fig = create_gauge_chart(
            value=current_rsi,
            title="RSI (USO)",
            min_val=0,
            max_val=100,
            thresholds={
                "low": RISK_THRESHOLDS["rsi"]["oversold"],
                "medium": RISK_THRESHOLDS["rsi"]["overbought"],
            },
        )
        st.plotly_chart(rsi_fig, use_container_width=True)

    # Daily P&L progress bar
    st.subheader("Daily P&L Progress")

    # Calculate target and limit percentages
    target_pct = float(config.daily_profit_target_pct * 100)
    limit_pct = -float(config.daily_loss_limit_pct * 100)

    # Determine color
    if today_pnl_pct >= target_pct:
        pnl_color = "green"
    elif today_pnl_pct <= limit_pct:
        pnl_color = "red"
    elif today_pnl_pct > 0:
        pnl_color = "normal"
    else:
        pnl_color = "inverse"

    # Progress bar (normalized to 0-100 scale)
    # Map: limit_pct (-3%) -> 0, 0% -> 50, target_pct (+2%) -> 100
    if today_pnl_pct <= limit_pct:
        progress = 0
    elif today_pnl_pct >= target_pct:
        progress = 100
    else:
        # Linear interpolation
        if today_pnl_pct < 0:
            # Between limit and 0
            progress = 50 * (today_pnl_pct - limit_pct) / abs(limit_pct)
        else:
            # Between 0 and target
            progress = 50 + 50 * (today_pnl_pct / target_pct)

    progress = max(0, min(100, int(progress)))

    st.progress(progress, text=f"Today's P&L: {today_pnl_pct:+.2f}%")

    # Show metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Daily Target",
            f"+{target_pct:.1f}%",
            delta=None,
            help="Daily profit target",
        )

    with col2:
        st.metric(
            "Current P&L",
            f"{today_pnl_pct:+.2f}%",
            delta=None,
            help="Today's unrealized P&L",
        )

    with col3:
        st.metric(
            "Daily Limit",
            f"{limit_pct:.1f}%",
            delta=None,
            help="Daily loss limit (circuit breaker)",
        )
