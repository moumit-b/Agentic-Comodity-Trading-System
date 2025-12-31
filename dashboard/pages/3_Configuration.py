"""Configuration page for adjusting trading parameters."""

import streamlit as st

from dashboard.config import DASHBOARD_TITLE, PAGE_ICON
from src.core.config import AutomationMode, TradingConfig

# Page configuration
st.set_page_config(
    page_title=f"Configuration - {DASHBOARD_TITLE}",
    page_icon=PAGE_ICON,
    layout="wide",
)

st.title("⚙️ System Configuration")

# Load current configuration
config = TradingConfig()

st.info(
    "**Note:** Configuration changes on this page are for display purposes only. "
    "To modify system settings, update the `.env` file or use the ConfigOverride model."
)

# Configuration sections
tab1, tab2, tab3 = st.tabs(["Trading Parameters", "Automation Mode", "Risk Limits"])

# Tab 1: Trading Parameters
with tab1:
    st.subheader("Trading Parameters")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Position Management**")

        # Max positions
        max_positions = st.slider(
            "Max Positions",
            min_value=1,
            max_value=10,
            value=int(config.max_positions),
            help="Maximum number of concurrent positions",
            disabled=True,
        )

        # Max trades per day
        max_trades = st.slider(
            "Max Trades Per Day",
            min_value=1,
            max_value=50,
            value=int(config.max_trades_per_day),
            help="Maximum number of trades allowed per day",
            disabled=True,
        )

        # Trading symbols
        st.write("**Symbols**")
        symbols = st.multiselect(
            "Trading Symbols",
            options=["USO", "UNG", "GLD", "SLV"],
            default=config.symbols,
            help="Symbols to trade",
            disabled=True,
        )

    with col2:
        st.write("**Risk Management**")

        # Risk per trade
        risk_per_trade = st.slider(
            "Risk Per Trade (%)",
            min_value=0.5,
            max_value=3.0,
            value=float(config.risk_per_trade_pct * 100),
            step=0.1,
            help="Percentage of account to risk per trade",
            disabled=True,
        )

        # Daily profit target
        profit_target = st.slider(
            "Daily Profit Target (%)",
            min_value=0.5,
            max_value=5.0,
            value=float(config.daily_profit_target_pct * 100),
            step=0.1,
            help="Daily profit target before reducing activity",
            disabled=True,
        )

        # Daily loss limit
        loss_limit = st.slider(
            "Daily Loss Limit (%)",
            min_value=1.0,
            max_value=10.0,
            value=float(config.daily_loss_limit_pct * 100),
            step=0.1,
            help="Maximum daily loss before halting trading",
            disabled=True,
        )

# Tab 2: Automation Mode
with tab2:
    st.subheader("Automation Mode")

    st.write(
        "The automation mode determines how the system handles trade execution. "
        "Select the appropriate mode based on your confidence level and risk tolerance."
    )

    # Current mode display
    current_mode = config.automation_mode

    mode_descriptions = {
        AutomationMode.ADVISORY: {
            "name": "Advisory Only",
            "description": "System generates signals and logs recommendations, but does not execute any trades.",
            "risk": "🟢 No Risk",
            "icon": "💡",
        },
        AutomationMode.PAPER_AUTO: {
            "name": "Paper Trading (Auto)",
            "description": "System automatically executes trades in paper trading account using simulated funds.",
            "risk": "🟡 Low Risk (Simulated)",
            "icon": "📝",
        },
        AutomationMode.LIVE_CONFIRM: {
            "name": "Live Trading (Manual Confirm)",
            "description": "System generates trade signals but requires manual approval before executing with real money.",
            "risk": "🟠 Medium Risk (Confirmation Required)",
            "icon": "⚠️",
        },
        AutomationMode.LIVE_AUTO: {
            "name": "Live Trading (Fully Automated)",
            "description": "System automatically executes all approved trades with real money. Maximum automation.",
            "risk": "🔴 High Risk (Fully Automated)",
            "icon": "🤖",
        },
    }

    # Display current mode
    current_mode_info = mode_descriptions[current_mode]

    st.success(
        f"**Current Mode:** {current_mode_info['icon']} {current_mode_info['name']}\n\n"
        f"{current_mode_info['description']}\n\n"
        f"**Risk Level:** {current_mode_info['risk']}"
    )

    st.divider()

    # Mode selection (display only)
    st.write("**Available Modes:**")

    for mode, info in mode_descriptions.items():
        with st.expander(f"{info['icon']} {info['name']}", expanded=(mode == current_mode)):
            st.write(f"**Description:** {info['description']}")
            st.write(f"**Risk Level:** {info['risk']}")

            if mode == current_mode:
                st.info("✓ Currently active")

# Tab 3: Risk Limits
with tab3:
    st.subheader("Risk Limits & Circuit Breakers")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Portfolio Limits**")

        # Max portfolio heat
        max_heat = st.slider(
            "Max Portfolio Heat (%)",
            min_value=10,
            max_value=100,
            value=int(config.max_portfolio_heat_pct * 100),
            step=5,
            help="Maximum percentage of account at risk across all positions",
            disabled=True,
        )

        # Consecutive losses limit
        consecutive_losses = st.number_input(
            "Consecutive Loss Limit",
            min_value=1,
            max_value=10,
            value=int(config.max_consecutive_losses),
            help="Maximum consecutive losing trades before halting",
            disabled=True,
        )

    with col2:
        st.write("**Drawdown Protection**")

        # Max drawdown
        max_drawdown = st.slider(
            "Max Drawdown (%)",
            min_value=5,
            max_value=50,
            value=int(config.max_drawdown_pct * 100),
            step=5,
            help="Maximum account drawdown before halting trading",
            disabled=True,
        )

        # Volatility multiplier
        volatility_multiplier = st.slider(
            "Volatility Spike Multiplier",
            min_value=1.5,
            max_value=5.0,
            value=float(config.volatility_spike_multiplier),
            step=0.1,
            help="Circuit breaker trips if volatility exceeds this multiple of average",
            disabled=True,
        )

    st.divider()

    # Circuit breaker summary
    st.write("**Circuit Breaker Configuration**")

    breakers = [
        ("Daily Loss Limit", f"{loss_limit:.1f}%", "Trips when daily loss exceeds limit"),
        (
            "Consecutive Losses",
            f"{consecutive_losses} trades",
            "Trips after consecutive losing trades",
        ),
        ("Max Positions", f"{max_positions} positions", "Prevents opening beyond limit"),
        (
            "Max Daily Trades",
            f"{max_trades} trades",
            "Prevents excessive trading in one day",
        ),
        ("Portfolio Heat", f"{max_heat}%", "Trips when total risk exceeds limit"),
        (
            "Volatility Spike",
            f"{volatility_multiplier}x",
            "Trips during extreme market conditions",
        ),
        ("Manual Kill Switch", "User Activated", "Emergency stop button"),
    ]

    for name, value, description in breakers:
        col1, col2, col3 = st.columns([2, 1, 3])

        with col1:
            st.write(f"**{name}**")

        with col2:
            st.code(value)

        with col3:
            st.caption(description)

# Sidebar
with st.sidebar:
    st.header("Configuration Help")

    st.info(
        "**To modify settings:**\n\n"
        "1. Update values in `.env` file\n"
        "2. Restart the trading system\n"
        "3. Or use ConfigOverride model for runtime changes"
    )

    st.divider()

    st.header("Quick Actions")

    if st.button("🔄 Refresh Configuration", use_container_width=True):
        st.rerun()

    st.divider()

    st.caption("Configuration page is read-only for safety.")
