"""Main Streamlit dashboard application."""

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from dashboard.components.circuit_breakers import render_circuit_breakers
from dashboard.components.header import render_header
from dashboard.components.order_confirmation import render_order_confirmation
from dashboard.components.positions_table import render_positions_table
from dashboard.components.price_chart import render_price_chart
from dashboard.components.risk_gauges import render_risk_gauges
from dashboard.components.signal_feed import render_signal_feed
from dashboard.config import DASHBOARD_TITLE, PAGE_ICON
from src.core.config import DatabaseConfig
from src.core.database import init_db

# Initialize database connection
if "db_initialized" not in st.session_state:
    db_config = DatabaseConfig()
    init_db(db_config)
    st.session_state.db_initialized = True

# Page configuration
st.set_page_config(
    page_title=DASHBOARD_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Trigger rerun every 30 seconds to keep fragments active
# Fragments will update every 5s independently
st_autorefresh(interval=30000, key="fragment_heartbeat")

# Main title
st.title(f"{PAGE_ICON} {DASHBOARD_TITLE}")

# Render header with status indicators
render_header()

# Main layout
col_left, col_right = st.columns([2, 1])

with col_left:
    # Price chart with technical indicators
    render_price_chart()

    st.divider()

    # Positions table
    render_positions_table()

with col_right:
    # Order confirmation (LIVE_CONFIRM mode only)
    render_order_confirmation()

    st.divider()

    # Signal feed
    render_signal_feed()

    st.divider()

    # Risk gauges
    render_risk_gauges()

    st.divider()

    # Circuit breaker status
    render_circuit_breakers()

# Sidebar
with st.sidebar:
    st.header("Navigation")
    st.page_link("app.py", label="Dashboard", icon="🏠")
    st.page_link("pages/1_Performance.py", label="Performance", icon="📊")
    st.page_link("pages/2_Signals.py", label="Signals", icon="📡")
    st.page_link("pages/3_Configuration.py", label="Configuration", icon="⚙️")
    st.page_link("pages/4_Risk.py", label="Risk", icon="⚠️")
    st.page_link("pages/5_Audit.py", label="Audit", icon="📝")

    st.divider()

    st.header("Quick Stats")
    # Quick stats will be populated from data_loader
    st.metric("Active Strategies", "0")
    st.metric("Today's Trades", "0")
    st.metric("Win Rate", "0%")

    st.divider()

    st.caption("Trading System Dashboard v1.0\n\nBuilt with Streamlit")
