"""Price chart component with candlestick and technical indicators."""

from datetime import timedelta

import streamlit as st

from dashboard.config import CHART_TIMEFRAMES, DEFAULT_TIMEFRAME
from dashboard.utils.chart_factory import create_candlestick_chart
from dashboard.utils.data_loader import load_bars_1m, load_indicators, load_positions


@st.fragment(run_every=timedelta(seconds=30))
def render_price_chart():
    """Render interactive price chart with symbol and timeframe selection."""
    st.subheader("Price Chart")

    # Get available symbols from positions
    positions_df = load_positions()

    if positions_df.empty:
        # Default symbols if no positions
        symbols = ["USO", "UNG"]
    else:
        symbols = sorted(positions_df["symbol"].unique().tolist())
        # Ensure USO and UNG are in the list
        for symbol in ["USO", "UNG"]:
            if symbol not in symbols:
                symbols.append(symbol)
        symbols.sort()

    # Chart controls
    col1, col2 = st.columns([3, 1])

    with col1:
        selected_symbol = st.selectbox(
            "Symbol",
            options=symbols,
            index=0 if "USO" in symbols else 0,
            key="price_chart_symbol",
        )

    with col2:
        selected_timeframe = st.selectbox(
            "Timeframe",
            options=CHART_TIMEFRAMES,
            index=CHART_TIMEFRAMES.index(DEFAULT_TIMEFRAME),
            key="price_chart_timeframe",
        )

    # Determine number of bars to load based on timeframe
    bar_limits = {
        "1H": 60,  # 60 minutes = 1 hour
        "4H": 240,  # 240 minutes = 4 hours
        "1D": 390,  # Full trading day (6.5 hours * 60)
        "1W": 1950,  # 5 trading days * 390
    }

    limit = bar_limits.get(selected_timeframe, 390)

    # Load data
    bars_df = load_bars_1m(selected_symbol, limit=limit)
    indicators_df = load_indicators(selected_symbol, timeframe="5m")

    if bars_df.empty:
        st.info(
            f"No bar data available for {selected_symbol}. "
            "Start the Market Data Agent to begin collecting data."
        )
        return

    # Create and display chart
    fig = create_candlestick_chart(
        bars_df=bars_df,
        indicators_df=indicators_df if not indicators_df.empty else None,
        symbol=selected_symbol,
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show data summary
    with st.expander("Chart Data Summary"):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Bars Loaded", len(bars_df))

        with col2:
            if not bars_df.empty:
                current_price = bars_df["close"].iloc[-1]
                st.metric("Current Price", f"${current_price:.2f}")

        with col3:
            if not bars_df.empty:
                price_change = bars_df["close"].iloc[-1] - bars_df["close"].iloc[0]
                price_change_pct = (price_change / bars_df["close"].iloc[0]) * 100
                st.metric(
                    "Change",
                    f"${price_change:+.2f}",
                    f"{price_change_pct:+.2f}%",
                )

        with col4:
            if not indicators_df.empty and "rsi" in indicators_df.columns:
                current_rsi = indicators_df["rsi"].iloc[-1]
                st.metric("RSI", f"{current_rsi:.1f}")
