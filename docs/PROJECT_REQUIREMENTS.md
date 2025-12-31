# Project Requirements: Enhanced Agentic Commodity Trading System

> **Status:** Living document - Production-grade specification
>
> **Last Updated:** 2025-12-30
>
> **Version:** 2.0 (Enhanced Production System)

---

## 1. System Overview

### 1.1 What This Is

A **production-grade, progressively autonomous multi-agent trading system** for crude oil (USO) and natural gas (UNG) ETF trading, supporting both intraday and swing trading strategies with intelligent selection based on market conditions.

**Core Philosophy:**
- **Progressive automation:** ADVISORY → PAPER_AUTO → LIVE_CONFIRM → LIVE_AUTO
- **Safety-first:** 7-layer safety architecture with kill switch and circuit breakers
- **High precision:** 1-minute bar data frequency for accurate signal generation
- **Cash account compliance:** T+1 settlement tracking for Pattern Day Trader (PDT) workaround
- **Intelligent orchestration:** Market regime detection with dynamic strategy selection
- **Comprehensive risk management:** Configurable risk parameters, portfolio heat tracking
- **Audit trail:** Every decision logged with full reasoning
- **Cloud-native:** AWS deployment with RDS, ElastiCache, Lambda

### 1.2 What This Is NOT

- NOT a high-frequency trading (HFT) system (1-minute granularity, not milliseconds)
- NOT a complex ML research project initially (rule-based first, ML Phase 2+)
- NOT fully autonomous by default (requires explicit feature flag for LIVE_AUTO)
- NOT a margin trading system (cash account for PDT compliance)

###1.3 Success Criteria

**Phase 1 Complete (Core Infrastructure):**
- [x] 1-minute bar data streaming from Alpaca WebSocket
- [x] Multi-timeframe aggregation (1m → 5m → 15m → 1h → 1d)
- [x] PostgreSQL database with partitioned 1m bar storage
- [x] Redis caching layer operational
- [x] Configuration system with runtime overrides

**Phase 2 Complete (Strategy Framework):**
- [ ] Market regime detection (trending/ranging/volatile)
- [ ] Strategy Selector Agent operational
- [ ] Multiple strategies implemented (trend-follow, mean-revert, breakout)
- [ ] Multi-timeframe signal generation working

**Phase 3 Complete (Risk & Settlement):**
- [ ] T+1 settlement tracking preventing unsettled cash trades
- [ ] Portfolio heat calculation and enforcement
- [ ] Circuit breakers trigger correctly
- [ ] Time-based intraday exits enforced

**Phase 4 Complete (Execution & Notifications):**
- [ ] All 4 automation modes working (ADVISORY, PAPER_AUTO, LIVE_CONFIRM, LIVE_AUTO)
- [ ] Discord DM confirmation flow with timeout
- [ ] Dashboard approve button functional
- [ ] Kill switch closes all positions < 5 seconds

**Phase 5 Complete (Dashboard):**
- [ ] Real-time position monitoring
- [ ] Config adjustment UI functional
- [ ] P&L charts displaying correctly
- [ ] Alert history viewable

**Phase 6 Complete (AWS Deployment):**
- [ ] RDS PostgreSQL instance running
- [ ] ElastiCache Redis cluster operational
- [ ] Lambda trading loop executing every minute
- [ ] Streamlit dashboard hosted and accessible
- [ ] CloudWatch alarms configured

**Production Readiness:**
- [ ] 4+ weeks successful paper trading
- [ ] Sharpe ratio > 0.5 in paper trading
- [ ] Max drawdown < 10% in paper trading
- [ ] All safety layers tested and verified

---

## 2. Agent Architecture (7 Agents)

### 2.1 Architecture Diagram

```
                          +------------------+
                          |   Coordinator    |
                          | (Orchestrator)   |
                          +--------+---------+
                                   |
      +----------------------------+---------------------------+
      |            |           |          |           |        |
+-----v-----+ +----v----+ +----v----+ +---v---+ +----v----+ +-v--+
|  Market   | |Strategy | |Strategy | |  Risk | |Settle-  | |Exec|
|   Data    | |Selector | |  Pool   | |Manager| |ment     | |    |
+-----+-----+ +----+----+ +----+----+ +---+---+ +----+----+ +----+
      |            |           |          |           |
      |            |           |          |           |
+-----v------------v-----------v----------v-----------v-----+
|              Shared State (PostgreSQL + Redis)           |
|    + Event Bus (for async agent communication)           |
+----------------------------------------------------------+
```

### 2.2 Design Principles

- **Asynchronous communication:** Agents communicate via event bus and shared state
- **Stateless agents:** All state stored in database, agents are stateless
- **Separation of concerns:** Each agent has single, well-defined responsibility
- **Explicit interfaces:** Typed inputs/outputs using Pydantic models
- **Fail-safe design:** Prefer no-trade over risky-trade
- **Audit trail:** Every agent decision logged to database
- **Multi-timeframe aware:** All agents can reason about multiple timeframes

### 2.3 Agent Definitions

---

#### Agent 1: Market Data Agent

**Responsibility:** Real-time 1-minute bar streaming, multi-timeframe aggregation, indicator computation

**Data Sources:**
- Primary: Alpaca Market Data API (WebSocket) - 1-minute bars, real-time
- Fallback: yfinance for historical backfill

**Key Features:**
- WebSocket connection with exponential backoff reconnection
- 1-minute bar ingestion to PostgreSQL (partitioned by month)
- Real-time aggregation: 1m → 5m → 15m → 1h → 1d
- Redis caching for hot data (last 100 bars per timeframe)
- Data quality validation (gaps, stale timestamps, outliers)
- Indicator computation using pandas-ta (RSI, MACD, EMA, ATR, BB)
- Market regime detection (trending/ranging/volatile)

**Interface:**
```python
class MarketDataAgent(Protocol):
    async def connect(self) -> None:
        """Establish WebSocket connection to Alpaca."""
        ...

    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to real-time 1-minute bars."""
        ...

    async def get_bars(
        self,
        symbol: str,
        timeframe: Timeframe,  # Enum: M1, M5, M15, H1, D1
        count: int = 100
    ) -> pd.DataFrame:
        """Get bars for specified timeframe (from cache or database)."""
        ...

    async def get_indicators(
        self,
        symbol: str,
        timeframes: list[Timeframe]
    ) -> dict[Timeframe, IndicatorSet]:
        """Get technical indicators for multiple timeframes."""
        ...

    def get_market_regime(self, symbol: str) -> MarketRegime:
        """Detect market regime: TRENDING, RANGING, VOLATILE."""
        ...
```

**Database Tables:**
- `bars_1m` - Partitioned by month for efficient querying
- `bars_aggregated` - 5m, 15m, 1h, 1d bars
- `indicators` - Computed indicator values

**Implementation Notes:**
- Use `asyncpg` for async PostgreSQL access
- Redis keys: `bars:{symbol}:{timeframe}` with 15-minute TTL
- WebSocket reconnection: exponential backoff (1s → 60s max)
- Staleness threshold: Reject data > 30 seconds old (configurable)

---

#### Agent 2: Strategy Selector Agent (NEW)

**Responsibility:** Analyze market conditions and intelligently select appropriate strategies

**Key Features:**
- Market regime detection using ADX (trend strength), BB width (volatility), volume profile
- Time-of-day awareness (opening hour, midday, closing hour, overnight)
- Intraday vs swing trade decision based on time remaining until market close
- Strategy rotation based on recent performance
- Multi-timeframe condition analysis

**Market Regimes:**
- **TRENDING:** ADX > 25, price following EMA20/50, clear directional movement
- **RANGING:** ADX < 20, price oscillating within BB, low directional movement
- **VOLATILE:** BB width > 95th percentile, ATR > 150% of 20-day average

**Strategy Selection Logic:**
```python
Conditions:
    - TRENDING + Early Day → Trend-Following (EMA/MACD) + Intraday
    - TRENDING + Late Day → Trend-Following + Swing (allow overnight)
    - RANGING → Mean-Reversion (BB/RSI) + Intraday
    - VOLATILE → Breakout (Volume/Range) + Small position size
```

**Interface:**
```python
class StrategySelectorAgent(Protocol):
    def analyze_conditions(
        self,
        symbol: str,
        data: dict[Timeframe, pd.DataFrame],
        indicators: dict[Timeframe, IndicatorSet]
    ) -> MarketConditions:
        """Analyze current market conditions."""
        ...

    def select_strategies(
        self,
        conditions: MarketConditions,
        time_until_close: timedelta
    ) -> list[StrategySelection]:
        """Select appropriate strategies for current conditions."""
        ...

@dataclass
class MarketConditions:
    regime: MarketRegime  # TRENDING, RANGING, VOLATILE
    trend_strength: float  # 0-1 (ADX-based)
    volatility_percentile: float  # 0-100
    time_phase: TimePhase  # OPENING, MIDDAY, CLOSING, OVERNIGHT
    correlation_to_spy: float  # Market correlation

@dataclass
class StrategySelection:
    strategy_type: StrategyType
    trade_horizon: TradeHorizon  # INTRADAY, SWING
    confidence: float
    weight: float  # For ensemble voting
```

**Database Tables:**
- `market_regimes` - Historical regime classifications
- `strategy_performance` - Recent performance by regime type

---

#### Agent 3: Strategy Pool

**Responsibility:** Execute selected strategies and generate trading signals

**Available Strategies:**

1. **Trend-Following Strategies:**
   - **EMA Crossover:** Long when EMA20 > EMA50 and RSI > 40, Short when EMA20 < EMA50 and RSI < 60
   - **MACD Momentum:** MACD line crosses signal line with histogram confirmation

2. **Mean-Reversion Strategies:**
   - **Bollinger Band:** Buy at lower BB touch with RSI < 30, Sell at upper BB touch with RSI > 70
   - **RSI Reversal:** Oversold (RSI < 30) bounce, overbought (RSI > 70) pullback

3. **Breakout Strategies (Phase 2):**
   - **Range Breakout:** Price breaks above/below consolidation range with volume
   - **Volume Surge:** Unusual volume spike (> 2x avg) with directional move

**Multi-Timeframe Signal Generation:**
```python
# Higher timeframe = Direction
# Mid timeframe = Confirmation
# Lower timeframe = Entry timing

Example:
    1h chart: TRENDING upward (ADX 30, EMA20 > EMA50)
    15m chart: MACD bullish cross
    5m chart: Price pullback to EMA20, RSI bounces from 45
    → LONG signal with confidence 0.85
```

**Interface:**
```python
class StrategyPool(Protocol):
    strategies: dict[StrategyType, BaseStrategy]

    def analyze(
        self,
        selection: StrategySelection,
        symbol: str,
        data: dict[Timeframe, pd.DataFrame],
        indicators: dict[Timeframe, IndicatorSet]
    ) -> Signal:
        """Execute selected strategy and return signal."""
        ...

@dataclass
class Signal:
    symbol: str
    action: Action  # BUY, SELL, HOLD
    strategy_type: StrategyType
    trade_horizon: TradeHorizon
    confidence: float
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    reasoning: str
    timeframes_used: list[Timeframe]
    indicator_snapshot: dict
    timestamp: datetime
```

**Database Tables:**
- `signals` - All generated signals (HOLD signals not stored)
- `strategy_votes` - Individual strategy opinions (for ensemble)

---

#### Agent 4: Risk Manager Agent

**Responsibility:** Validate trades, enforce position sizing, manage circuit breakers

**Key Features:**
- Position sizing: 1-2% risk per trade (configurable)
- Portfolio heat: Total risk across all positions < 5%
- Stop-loss validation: 0.5 ATR < SL < 5 ATR
- Time-based exit enforcement (intraday positions closed by 3:55 PM ET)
- Circuit breakers: daily loss limit, profit target, consecutive losses
- Correlation check: Reject if USO + UNG both long/short (correlation > 0.7)
- Trailing stops: Dynamic adjustment based on favorable price movement

**Position Sizing Formula:**
```python
available_capital = settled_cash  # From Settlement Tracker
risk_amount = available_capital * risk_pct  # Default: 1%
position_size = risk_amount / (entry_price - stop_loss)
position_size = min(position_size, max_position_value / entry_price)
```

**Circuit Breakers:**
1. **Daily Loss Limit:** Halt if daily P&L < -3% of account
2. **Daily Profit Target:** Halt if daily P&L > +2% (lock in gains)
3. **Consecutive Losses:** Halt after 3 losing trades in a row
4. **Max Trades Per Day:** Limit 10 trades/day to prevent overtrading
5. **Portfolio Heat:** Reject if total portfolio risk > 5%
6. **Stale Data:** Reject if latest data > 30 seconds old
7. **Extreme Volatility:** Halt if ATR > 3x recent average

**Interface:**
```python
class RiskManagerAgent(Protocol):
    def validate_trade(
        self,
        signal: Signal,
        account_state: AccountState,
        positions: list[Position],
        settlement_state: SettlementState
    ) -> RiskDecision:
        """Comprehensive risk validation."""
        ...

    def calculate_position_size(
        self,
        signal: Signal,
        available_capital: Decimal,
        risk_pct: Decimal
    ) -> int:
        """Calculate shares to trade based on risk."""
        ...

    def get_portfolio_heat(
        self,
        positions: list[Position]
    ) -> PortfolioHeat:
        """Total risk across all positions."""
        ...

    def check_circuit_breakers(
        self,
        account_state: AccountState
    ) -> CircuitBreakerStatus:
        """Check all circuit breakers."""
        ...

@dataclass
class RiskDecision:
    approved: bool
    position_size: int
    risk_pct: Decimal
    portfolio_heat: Decimal
    rejection_reason: str | None
    circuit_breaker_triggered: str | None
```

**Database Tables:**
- `decisions` - Risk validation results
- `circuit_breakers` - Trigger history
- `daily_limits` - Daily P&L tracking
- `portfolio_heat_snapshots` - Risk over time

---

#### Agent 5: Settlement Tracker Agent (NEW)

**Responsibility:** Track T+1 cash settlement for PDT compliance (cash account)

**Key Features:**
- T+1 settlement date calculation (accounting for weekends/holidays)
- Available cash calculation: `total_cash - pending_settlements`
- Settlement calendar management
- Prevent trading with unsettled funds

**Cash Account Rules:**
- **Unlimited day trades** (no 3-trade/5-day PDT limit)
- **Must wait T+1 for cash settlement** before reusing funds
- **Good faith violations:** Prevent selling before purchase settles (tracked automatically)

**Settlement Date Calculation:**
```python
def calculate_settlement_date(trade_date: date) -> date:
    """T+1 for equities, skipping weekends and market holidays."""
    settlement_date = trade_date + timedelta(days=1)

    while settlement_date.weekday() >= 5 or is_market_holiday(settlement_date):
        settlement_date += timedelta(days=1)

    return settlement_date
```

**Interface:**
```python
class SettlementTrackerAgent(Protocol):
    def record_trade(
        self,
        trade: ExecutedTrade
    ) -> None:
        """Record trade for settlement tracking."""
        ...

    def get_settlement_state(self) -> SettlementState:
        """Get current settlement status."""
        ...

    def get_available_cash(
        self,
        current_time: datetime
    ) -> Decimal:
        """Calculate cash available for trading (settled only)."""
        ...

    async def process_settlements(self) -> list[Settlement]:
        """Process all pending settlements (run daily at 6 AM ET)."""
        ...

@dataclass
class SettlementState:
    total_cash: Decimal
    settled_cash: Decimal
    unsettled_cash: Decimal
    pending_settlements: list[PendingSettlement]
    available_for_trading: Decimal  # settled_cash
```

**Database Tables:**
- `settlements` - Trade settlement tracking
- `account_snapshots` - Daily cash balances

---

#### Agent 6: Execution Agent

**Responsibility:** Multi-mode trade execution with safety layers

**Automation Modes:**
```python
class AutomationMode(Enum):
    ADVISORY = "ADVISORY"          # Discord notification only, no execution
    PAPER_AUTO = "PAPER_AUTO"      # Auto-execute on Alpaca paper account
    LIVE_CONFIRM = "LIVE_CONFIRM"  # Discord DM + dashboard confirmation required
    LIVE_AUTO = "LIVE_AUTO"        # Feature flag protected, full autonomous
```

**Confirmation Flow (LIVE_CONFIRM mode):**
```
1. Risk-approved signal received
2. Send Discord DM with trade details + approve/reject buttons
3. ALSO update dashboard with pending trade (approve button)
4. Wait for confirmation (configurable timeout: 30-120s)
5. On approve: Execute trade
6. On reject/timeout: Log rejection and move on
```

**Order Types:**
- Market orders (for entries)
- Stop-loss orders (server-side with broker)
- Take-profit limit orders
- Trailing stop orders (Phase 2)

**Interface:**
```python
class ExecutionAgent(Protocol):
    async def execute(
        self,
        decision: ApprovedDecision,
        mode: AutomationMode
    ) -> ExecutionResult:
        """Execute trade based on automation mode."""
        ...

    async def request_confirmation(
        self,
        decision: ApprovedDecision,
        timeout_seconds: int = 60
    ) -> ConfirmationResult:
        """Request confirmation via Discord DM and dashboard."""
        ...

    async def place_order(
        self,
        order: Order
    ) -> OrderResult:
        """Place order with Alpaca (paper or live)."""
        ...

    async def close_all_positions(
        self,
        reason: str
    ) -> list[CloseResult]:
        """Emergency close all (kill switch)."""
        ...
```

**Database Tables:**
- `executions` - Order execution audit trail
- `confirmations` - Confirmation requests and responses

---

#### Agent 7: Coordinator (Orchestrator)

**Responsibility:** Wire all agents together, manage trading loop, enforce workflow

**Main Trading Loop (1-minute cycle):**
```python
async def trading_loop(self):
    while is_trading_hours():
        for symbol in ["USO", "UNG"]:
            # 1. Get multi-timeframe data
            data = await market_data.get_bars(symbol, [M1, M5, M15, H1, D1])
            indicators = await market_data.get_indicators(symbol, [M1, M5, M15, H1, D1])

            # 2. Analyze market regime and select strategies
            conditions = strategy_selector.analyze_conditions(symbol, data, indicators)
            selections = strategy_selector.select_strategies(conditions, time_until_close())

            # 3. Run selected strategies (may return multiple signals)
            for selection in selections:
                signal = strategy_pool.analyze(selection, symbol, data, indicators)

                if signal.action == Action.HOLD:
                    continue

                # 4. Get settlement state
                settlement = settlement_tracker.get_settlement_state()

                # 5. Risk validation
                decision = risk_manager.validate_trade(
                    signal, account_state, positions, settlement
                )

                if not decision.approved:
                    log_rejection(signal, decision)
                    continue

                # 6. Execute based on automation mode
                result = await execution.execute(decision, config.automation_mode)

                # 7. Record settlement if executed
                if result.success:
                    settlement_tracker.record_trade(result.trade)

        # Check time-based exits for intraday positions
        await check_intraday_exits()

        # Sleep until next minute
        await sleep_until_next_minute()
```

**Database Tables:**
- All agent tables accessible
- `coordinator_state` - Loop status and metrics

---

## 3. Technology Stack

### 3.1 Core Dependencies

```toml
[project.dependencies]
# Core
python = ">=3.12"
pandas = "^2.2"
numpy = "^1.26"

# Data Sources
alpaca-py = "^0.30"      # Upgraded for WebSocket support
yfinance = "^0.2"
pandas-ta = "^0.3.14b"

# Async & Networking
httpx = "^0.27"
websockets = "^12.0"
aiohttp = "^3.9"

# Database
asyncpg = "^0.29"        # PostgreSQL async driver
sqlalchemy = "^2.0"
alembic = "^1.13"        # Migrations
redis = "^5.0"

# Dashboard
streamlit = "^1.29"
plotly = "^5.18"

# Notifications
discord.py = "^2.3"      # Enhanced Discord bot

# AWS
boto3 = "^1.34"
aioboto3 = "^12.0"

# Configuration
pydantic = "^2.5"
pydantic-settings = "^2.1"

# Utilities
schedule = "^1.2"
python-dateutil = "^2.8"
pytz = "^2024.1"
```

### 3.2 Development Tools

```toml
[project.optional-dependencies.dev]
ruff = "^0.1"
pytest = "^7.4"
pytest-asyncio = "^0.23"
pytest-cov = "^4.1"
mypy = "^1.8"
types-redis = "*"
moto = "^5.0"            # AWS mocking
testcontainers = "^3.7"  # Container-based testing
```

---

## 4. Database Schema (PostgreSQL)

### 4.1 Market Data Tables

```sql
-- ============================================
-- 1-Minute Bars (Partitioned by Month)
-- ============================================

CREATE TABLE bars_1m (
    id BIGSERIAL,
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(12, 4) NOT NULL,
    high DECIMAL(12, 4) NOT NULL,
    low DECIMAL(12, 4) NOT NULL,
    close DECIMAL(12, 4) NOT NULL,
    volume BIGINT NOT NULL,
    vwap DECIMAL(12, 4),
    trade_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, timestamp)
) PARTITION BY RANGE (timestamp);

-- Monthly partitions
CREATE TABLE bars_1m_2025_01 PARTITION OF bars_1m
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
-- Continue for each month...

CREATE INDEX idx_bars_1m_symbol_ts ON bars_1m (symbol, timestamp DESC);

-- ============================================
-- Aggregated Bars (5m, 15m, 1h, 1d)
-- ============================================

CREATE TABLE bars_aggregated (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,  -- '5m', '15m', '1h', '1d'
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(12, 4) NOT NULL,
    high DECIMAL(12, 4) NOT NULL,
    low DECIMAL(12, 4) NOT NULL,
    close DECIMAL(12, 4) NOT NULL,
    volume BIGINT NOT NULL,
    UNIQUE (symbol, timeframe, timestamp)
);

CREATE INDEX idx_bars_agg ON bars_aggregated (symbol, timeframe, timestamp DESC);

-- ============================================
-- Indicators
-- ============================================

CREATE TABLE indicators (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    indicator_type VARCHAR(50) NOT NULL,  -- 'rsi', 'macd_line', 'ema_20'
    value DECIMAL(15, 6),
    extra_data JSONB,
    UNIQUE (symbol, timeframe, timestamp, indicator_type)
);
```

### 4.2 Account & Settlement Tables

```sql
-- ============================================
-- Account Snapshots
-- ============================================

CREATE TABLE account_snapshots (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_cash DECIMAL(15, 2) NOT NULL,
    settled_cash DECIMAL(15, 2) NOT NULL,
    unsettled_cash DECIMAL(15, 2) NOT NULL,
    equity DECIMAL(15, 2) NOT NULL,
    buying_power DECIMAL(15, 2) NOT NULL,
    daily_pnl DECIMAL(15, 2),
    total_pnl DECIMAL(15, 2)
);

-- ============================================
-- T+1 Settlements
-- ============================================

CREATE TABLE settlements (
    id BIGSERIAL PRIMARY KEY,
    trade_id VARCHAR(50) NOT NULL UNIQUE,
    symbol VARCHAR(10) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(12, 4) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    trade_date DATE NOT NULL,
    settlement_date DATE NOT NULL,  -- T+1
    settled_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'  -- PENDING, SETTLED
);

CREATE INDEX idx_settlements_pending ON settlements (settlement_date)
    WHERE status = 'PENDING';
```

### 4.3 Position & Trade Tables

```sql
-- ============================================
-- Positions
-- ============================================

CREATE TABLE positions (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- LONG, SHORT
    quantity INTEGER NOT NULL,
    entry_price DECIMAL(12, 4) NOT NULL,
    current_price DECIMAL(12, 4),
    stop_loss DECIMAL(12, 4),
    take_profit DECIMAL(12, 4),
    trailing_stop_pct DECIMAL(5, 2),
    trade_horizon VARCHAR(20) NOT NULL,  -- INTRADAY, SWING
    strategy_name VARCHAR(50),
    unrealized_pnl DECIMAL(15, 2),
    opened_at TIMESTAMPTZ NOT NULL,
    closed_at TIMESTAMPTZ,
    exit_price DECIMAL(12, 4),
    realized_pnl DECIMAL(15, 2),
    exit_reason VARCHAR(50),  -- STOP_LOSS, TAKE_PROFIT, TIME_EXIT, MANUAL
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN'  -- OPEN, CLOSED
);

CREATE INDEX idx_positions_open ON positions (symbol, status) WHERE status = 'OPEN';
```

### 4.4 Signal & Decision Tables

```sql
-- ============================================
-- Signals
-- ============================================

CREATE TABLE signals (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol VARCHAR(10) NOT NULL,
    action VARCHAR(10) NOT NULL,
    strategy_type VARCHAR(50) NOT NULL,
    trade_horizon VARCHAR(20) NOT NULL,
    confidence DECIMAL(4, 3) NOT NULL,
    entry_price DECIMAL(12, 4),
    stop_loss DECIMAL(12, 4),
    take_profit DECIMAL(12, 4),
    reasoning TEXT,
    market_regime VARCHAR(20),
    timeframes_used TEXT[],
    indicator_snapshot JSONB
);

-- ============================================
-- Risk Decisions
-- ============================================

CREATE TABLE decisions (
    id BIGSERIAL PRIMARY KEY,
    signal_id BIGINT REFERENCES signals(id),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved BOOLEAN NOT NULL,
    position_size INTEGER,
    risk_pct DECIMAL(5, 3),
    portfolio_heat DECIMAL(5, 3),
    available_cash DECIMAL(15, 2),
    rejection_reason TEXT,
    circuit_breaker_triggered VARCHAR(50)
);

-- ============================================
-- Executions
-- ============================================

CREATE TABLE executions (
    id BIGSERIAL PRIMARY KEY,
    decision_id BIGINT REFERENCES decisions(id),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    automation_mode VARCHAR(20) NOT NULL,
    confirmation_requested BOOLEAN DEFAULT FALSE,
    confirmation_received BOOLEAN,
    confirmation_timeout BOOLEAN,
    order_id VARCHAR(50),
    fill_price DECIMAL(12, 4),
    fill_quantity INTEGER,
    status VARCHAR(20) NOT NULL,  -- SUCCESS, REJECTED, TIMEOUT, ERROR
    error_message TEXT
);
```

### 4.5 Risk Management Tables

```sql
-- ============================================
-- Circuit Breakers
-- ============================================

CREATE TABLE circuit_breakers (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    breaker_type VARCHAR(50) NOT NULL,
    triggered BOOLEAN NOT NULL,
    trigger_value DECIMAL(15, 4),
    threshold_value DECIMAL(15, 4),
    reset_at TIMESTAMPTZ,
    notes TEXT
);

-- ============================================
-- Daily Limits
-- ============================================

CREATE TABLE daily_limits (
    id BIGSERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,
    starting_equity DECIMAL(15, 2) NOT NULL,
    current_pnl DECIMAL(15, 2) DEFAULT 0,
    profit_target DECIMAL(15, 2),
    loss_limit DECIMAL(15, 2),
    profit_target_hit BOOLEAN DEFAULT FALSE,
    loss_limit_hit BOOLEAN DEFAULT FALSE,
    trades_executed INTEGER DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Runtime Config Overrides
-- ============================================

CREATE TABLE config_overrides (
    id BIGSERIAL PRIMARY KEY,
    key VARCHAR(100) NOT NULL UNIQUE,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(50)  -- 'dashboard', 'cli', 'admin'
);
```

---

## 5. Configuration System

### 5.1 Configuration Model

**File: `src/core/config.py`**

```python
from decimal import Decimal
from enum import Enum
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

class AutomationMode(str, Enum):
    ADVISORY = "ADVISORY"
    PAPER_AUTO = "PAPER_AUTO"
    LIVE_CONFIRM = "LIVE_CONFIRM"
    LIVE_AUTO = "LIVE_AUTO"

class TradingConfig(BaseSettings):
    """Core trading configuration."""

    # === Symbols & Timeframes ===
    symbols: list[str] = Field(default=["USO", "UNG"])
    primary_timeframe: str = Field(default="1m")
    analysis_timeframes: list[str] = Field(default=["1m", "5m", "15m", "1h", "1d"])

    # === Risk Management ===
    risk_per_trade_pct: Decimal = Field(default=Decimal("0.01"))  # 1%
    max_risk_per_trade_pct: Decimal = Field(default=Decimal("0.02"))  # 2%
    max_portfolio_heat_pct: Decimal = Field(default=Decimal("0.05"))  # 5%
    max_positions: int = Field(default=2)

    # === Daily Limits ===
    daily_profit_target_pct: Decimal = Field(default=Decimal("0.02"))  # 2%
    daily_loss_limit_pct: Decimal = Field(default=Decimal("0.03"))  # 3%
    max_consecutive_losses: int = Field(default=3)
    max_trades_per_day: int = Field(default=10)

    # === Stop Loss & Take Profit ===
    default_stop_atr_multiple: Decimal = Field(default=Decimal("2.0"))
    default_tp_atr_multiple: Decimal = Field(default=Decimal("3.0"))
    enable_trailing_stop: bool = Field(default=True)
    trailing_stop_pct: Decimal = Field(default=Decimal("0.015"))  # 1.5%

    # === Time-Based Rules ===
    trading_start_et: str = Field(default="09:30")
    trading_end_et: str = Field(default="16:00")
    intraday_exit_time_et: str = Field(default="15:55")
    no_new_trades_after_et: str = Field(default="15:30")

    # === Automation Mode ===
    automation_mode: AutomationMode = Field(default=AutomationMode.ADVISORY)
    confirmation_timeout_seconds: int = Field(default=60)

    # === Feature Flags ===
    enable_live_auto: bool = Field(default=False)  # CRITICAL: Must be explicit
    enable_swing_trading: bool = Field(default=True)
    enable_breakout_strategies: bool = Field(default=False)

    @field_validator('automation_mode', mode='before')
    def validate_live_auto(cls, v, info):
        if v == AutomationMode.LIVE_AUTO:
            if not info.data.get('enable_live_auto', False):
                raise ValueError(
                    "LIVE_AUTO requires enable_live_auto=True feature flag"
                )
        return v

    class Config:
        env_prefix = "TRADING_"
        env_file = ".env"
```

---

## 6. Development Phases

### Phase 1: Core Infrastructure (Weeks 1-2)

**Goal:** Data pipeline, database, configuration

**Tasks:**
1. Set up PostgreSQL schema with Alembic migrations
2. Implement Redis caching layer
3. Create Market Data Agent with Alpaca WebSocket
4. Implement multi-timeframe aggregation
5. Create configuration system with pydantic-settings

**Deliverables:**
- `src/core/config.py`
- `src/core/database.py`
- `src/agents/market_data.py`
- `src/services/redis_cache.py`
- `alembic/versions/001_initial_schema.py`

---

### Phase 2: Strategy Framework (Weeks 3-4)

**Goal:** Strategy selection and signal generation

**Tasks:**
1. Implement Strategy Selector Agent with regime detection
2. Create Strategy Pool with base strategy
3. Implement trend-following strategies
4. Implement mean-reversion strategies
5. Build multi-timeframe signal logic

**Deliverables:**
- `src/agents/strategy_selector.py`
- `src/agents/strategy_pool.py`
- `src/strategies/base.py`
- `src/strategies/trend_following.py`
- `src/strategies/mean_reversion.py`

---

### Phase 3: Risk & Settlement (Weeks 5-6)

**Goal:** Risk management and cash tracking

**Tasks:**
1. Implement Settlement Tracker Agent
2. Enhance Risk Manager with portfolio heat
3. Implement all circuit breakers
4. Add time-based exit logic
5. Create position sizing logic

**Deliverables:**
- `src/agents/settlement_tracker.py`
- `src/agents/risk_manager.py`
- `src/services/circuit_breakers.py`

---

### Phase 4: Execution & Notifications (Weeks 7-8)

**Goal:** Multi-mode execution

**Tasks:**
1. Implement Execution Agent with all 4 modes
2. Create Discord bot for confirmations
3. Build confirmation flow
4. Implement order placement
5. Create kill switch

**Deliverables:**
- `src/agents/execution.py`
- `src/services/discord_bot.py`
- `src/services/kill_switch.py`

---

### Phase 5: Coordinator & Dashboard (Weeks 9-10)

**Goal:** Orchestration and monitoring

**Tasks:**
1. Implement Coordinator
2. Create Streamlit dashboard
3. Add position monitoring
4. Implement config override UI
5. Create P&L charts

**Deliverables:**
- `src/coordinator.py`
- `dashboard/app.py`

---

### Phase 6: AWS Deployment (Weeks 11-12)

**Goal:** Production deployment

**Tasks:**
1. Set up RDS PostgreSQL
2. Configure ElastiCache Redis
3. Create Lambda functions
4. Deploy dashboard to EC2/Fargate
5. Set up CloudWatch alarms

**Deliverables:**
- `infrastructure/terraform/`
- `lambda_handlers/`

---

## 7. AWS Infrastructure

### 7.1 Architecture

```
CloudWatch      Alpaca API
    |               |
    v               v
  Lambda  <--->  ElastiCache (Redis)
    |               ^
    v               |
RDS PostgreSQL <----+
    ^
    |
EC2 (Streamlit Dashboard)
```

### 7.2 Estimated Monthly Cost (with Student Credits)

| Service | Config | Cost |
|---------|--------|------|
| RDS PostgreSQL | db.t3.micro | ~$15 |
| ElastiCache Redis | cache.t3.micro | ~$12 |
| Lambda | 1M invocations | ~$0.20 |
| EC2 (Dashboard) | t3.micro | ~$8 |
| Secrets Manager | 4 secrets | ~$2 |
| CloudWatch | Logs + Alarms | ~$5 |
| **Total** | | **~$42/month** |

AWS Educate provides $100+ credits, covering 2+ months.

---

## 8. Safety Layers (7 Levels)

1. **Feature Flags:** `enable_live_auto=False` by default
2. **Risk Manager:** Position sizing, portfolio heat, circuit breakers
3. **Settlement Awareness:** Only trade settled cash
4. **Time-Based:** No trades after 3:30 PM, force close intraday at 3:55 PM
5. **Human Confirmation:** Discord DM + Dashboard
6. **Kill Switch:** CLI, Discord, Dashboard buttons
7. **CloudWatch Alerts:** Unusual activity monitoring

---

## 9. Success Metrics

### 9.1 Paper Trading (4+ Weeks Required)

- [ ] Sharpe ratio > 0.5
- [ ] Max drawdown < 10%
- [ ] Win rate > 45%
- [ ] Risk/reward > 1.2
- [ ] Zero unintended trades
- [ ] Circuit breakers tested

### 9.2 Live Trading (Conservative Start)

- [ ] Start with 10% of capital
- [ ] LIVE_CONFIRM mode only (no LIVE_AUTO initially)
- [ ] Monitor for 2 weeks before increasing allocation
- [ ] All safety layers verified

---

**END OF REQUIREMENTS**

*This document defines a production-grade autonomous trading system with comprehensive safety layers and progressive automation.*
