"""Chart factory for creating Plotly charts."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.config import COLORS, DEFAULT_CHART_HEIGHT, RISK_THRESHOLDS


def create_candlestick_chart(
    bars_df: pd.DataFrame,
    indicators_df: pd.DataFrame | None = None,
    symbol: str = "USO",
    height: int = DEFAULT_CHART_HEIGHT,
) -> go.Figure:
    """
    Create candlestick chart with technical indicators.

    Args:
        bars_df: DataFrame with columns: timestamp, open, high, low, close, volume
        indicators_df: Optional DataFrame with indicators (ema_8, ema_21, rsi, macd, etc.)
        symbol: Symbol name for title
        height: Chart height in pixels

    Returns:
        Plotly Figure with candlestick and subplots
    """
    # Create subplots: [Candlestick + Volume, RSI, MACD]
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f"{symbol} Price", "RSI", "MACD"),
    )

    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=bars_df["timestamp"],
            open=bars_df["open"],
            high=bars_df["high"],
            low=bars_df["low"],
            close=bars_df["close"],
            name="Price",
            increasing_line_color=COLORS["profit"],
            decreasing_line_color=COLORS["loss"],
        ),
        row=1,
        col=1,
    )

    # Add indicators if available
    if indicators_df is not None and not indicators_df.empty:
        # EMA 8
        if "ema_8" in indicators_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=indicators_df["timestamp"],
                    y=indicators_df["ema_8"],
                    name="EMA 8",
                    line=dict(color=COLORS["primary"], width=1),
                ),
                row=1,
                col=1,
            )

        # EMA 21
        if "ema_21" in indicators_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=indicators_df["timestamp"],
                    y=indicators_df["ema_21"],
                    name="EMA 21",
                    line=dict(color=COLORS["warning"], width=1),
                ),
                row=1,
                col=1,
            )

        # Bollinger Bands
        if all(col in indicators_df.columns for col in ["bb_upper", "bb_middle", "bb_lower"]):
            fig.add_trace(
                go.Scatter(
                    x=indicators_df["timestamp"],
                    y=indicators_df["bb_upper"],
                    name="BB Upper",
                    line=dict(color=COLORS["neutral"], width=1, dash="dot"),
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=indicators_df["timestamp"],
                    y=indicators_df["bb_lower"],
                    name="BB Lower",
                    line=dict(color=COLORS["neutral"], width=1, dash="dot"),
                    fill="tonexty",
                    fillcolor="rgba(128, 128, 128, 0.1)",
                ),
                row=1,
                col=1,
            )

        # VWAP
        if "vwap" in indicators_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=indicators_df["timestamp"],
                    y=indicators_df["vwap"],
                    name="VWAP",
                    line=dict(color=COLORS["text"], width=1, dash="dash"),
                ),
                row=1,
                col=1,
            )

        # RSI subplot
        if "rsi" in indicators_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=indicators_df["timestamp"],
                    y=indicators_df["rsi"],
                    name="RSI",
                    line=dict(color=COLORS["primary"], width=2),
                ),
                row=2,
                col=1,
            )

            # RSI overbought/oversold lines
            rsi_times = indicators_df["timestamp"]
            fig.add_hline(
                y=RISK_THRESHOLDS["rsi"]["overbought"],
                line_dash="dash",
                line_color=COLORS["loss"],
                row=2,
                col=1,
            )
            fig.add_hline(
                y=RISK_THRESHOLDS["rsi"]["oversold"],
                line_dash="dash",
                line_color=COLORS["profit"],
                row=2,
                col=1,
            )

        # MACD subplot
        if all(col in indicators_df.columns for col in ["macd", "macd_signal", "macd_hist"]):
            # MACD histogram
            colors = [
                COLORS["profit"] if val >= 0 else COLORS["loss"]
                for val in indicators_df["macd_hist"]
            ]
            fig.add_trace(
                go.Bar(
                    x=indicators_df["timestamp"],
                    y=indicators_df["macd_hist"],
                    name="MACD Histogram",
                    marker_color=colors,
                    showlegend=False,
                ),
                row=3,
                col=1,
            )

            # MACD line
            fig.add_trace(
                go.Scatter(
                    x=indicators_df["timestamp"],
                    y=indicators_df["macd"],
                    name="MACD",
                    line=dict(color=COLORS["primary"], width=2),
                ),
                row=3,
                col=1,
            )

            # Signal line
            fig.add_trace(
                go.Scatter(
                    x=indicators_df["timestamp"],
                    y=indicators_df["macd_signal"],
                    name="Signal",
                    line=dict(color=COLORS["warning"], width=2),
                ),
                row=3,
                col=1,
            )

    # Volume bars (on secondary y-axis in row 1)
    fig.add_trace(
        go.Bar(
            x=bars_df["timestamp"],
            y=bars_df["volume"],
            name="Volume",
            marker_color=COLORS["neutral"],
            opacity=0.3,
            yaxis="y2",
        ),
        row=1,
        col=1,
    )

    # Update layout
    fig.update_layout(
        height=height,
        template="plotly_dark",
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["secondary_bg"],
        font=dict(color=COLORS["text"]),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
    )

    # Update axes
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["neutral"], gridwidth=0.5)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["neutral"], gridwidth=0.5)

    # Y-axis for volume (row 1)
    fig.update_yaxes(secondary_y=True, showgrid=False, row=1, col=1)

    return fig


def create_equity_curve(
    daily_performance_df: pd.DataFrame,
    initial_balance: float = 10000,
) -> go.Figure:
    """
    Create equity curve chart with drawdown shading.

    Args:
        daily_performance_df: DataFrame with columns: date, daily_pnl
        initial_balance: Starting account balance

    Returns:
        Plotly Figure with equity curve
    """
    if daily_performance_df.empty:
        # Return empty chart
        fig = go.Figure()
        fig.add_annotation(
            text="No performance data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        return fig

    # Calculate cumulative equity
    daily_performance_df = daily_performance_df.sort_values("date")
    daily_performance_df["equity"] = initial_balance + daily_performance_df["daily_pnl"].cumsum()

    # Calculate running max for drawdown
    daily_performance_df["running_max"] = daily_performance_df["equity"].cummax()
    daily_performance_df["drawdown"] = (
        daily_performance_df["equity"] - daily_performance_df["running_max"]
    )

    fig = go.Figure()

    # Drawdown area (shaded red)
    fig.add_trace(
        go.Scatter(
            x=daily_performance_df["date"],
            y=daily_performance_df["running_max"],
            fill=None,
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=daily_performance_df["date"],
            y=daily_performance_df["equity"],
            fill="tonexty",
            fillcolor=f"rgba(255, 75, 75, 0.3)",
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Equity curve
    fig.add_trace(
        go.Scatter(
            x=daily_performance_df["date"],
            y=daily_performance_df["equity"],
            name="Equity",
            line=dict(color=COLORS["primary"], width=3),
            mode="lines",
        )
    )

    fig.update_layout(
        title="Equity Curve",
        template="plotly_dark",
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["secondary_bg"],
        font=dict(color=COLORS["text"]),
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Account Value ($)",
    )

    return fig


def create_gauge_chart(
    value: float,
    title: str,
    min_val: float = 0,
    max_val: float = 100,
    thresholds: dict | None = None,
) -> go.Figure:
    """
    Create semi-circular gauge chart.

    Args:
        value: Current value
        title: Gauge title
        min_val: Minimum value
        max_val: Maximum value
        thresholds: Optional dict with 'low' and 'medium' thresholds

    Returns:
        Plotly Figure with gauge
    """
    if thresholds is None:
        thresholds = {"low": max_val * 0.3, "medium": max_val * 0.6}

    # Determine color based on thresholds
    if value <= thresholds["low"]:
        color = COLORS["profit"]
    elif value <= thresholds["medium"]:
        color = COLORS["warning"]
    else:
        color = COLORS["loss"]

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={"text": title, "font": {"color": COLORS["text"]}},
            number={"suffix": "%", "font": {"color": COLORS["text"]}},
            gauge={
                "axis": {"range": [min_val, max_val], "tickcolor": COLORS["text"]},
                "bar": {"color": color},
                "bgcolor": COLORS["secondary_bg"],
                "borderwidth": 2,
                "bordercolor": COLORS["neutral"],
                "steps": [
                    {"range": [min_val, thresholds["low"]], "color": "rgba(0, 212, 170, 0.2)"},
                    {
                        "range": [thresholds["low"], thresholds["medium"]],
                        "color": "rgba(255, 165, 0, 0.2)",
                    },
                    {"range": [thresholds["medium"], max_val], "color": "rgba(255, 75, 75, 0.2)"},
                ],
                "threshold": {
                    "line": {"color": COLORS["critical"], "width": 4},
                    "thickness": 0.75,
                    "value": value,
                },
            },
        )
    )

    fig.update_layout(
        height=250,
        template="plotly_dark",
        paper_bgcolor=COLORS["background"],
        font=dict(color=COLORS["text"]),
    )

    return fig
