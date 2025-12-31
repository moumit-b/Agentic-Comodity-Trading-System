# Trading System Plan: Crude Oil and Natural Gas

> **Status:** Living document — refine and restructure as the project evolves. This is a starting point, not a rigid spec.

## Trading Style: Intraday and Swing Trading (Short-Term Focus)

**Time Horizon:** Short-term intraday and swing trading — positions opened and closed within the same day or over a few days, rather than held long-term. This aligns with a strategy of capitalizing on short-term price movements and volatility in crude oil and natural gas markets.

### Characteristics

- **Day trading (intraday):** Multiple trades per day, no overnight positions, requires intensive monitoring and fast decision-making
- **Swing trading:** Holds trades for several days to a few weeks, aiming to catch medium-term swings or trends, incurs overnight and weekend risk in exchange for potentially larger individual trade moves
- Both styles rely heavily on technical analysis given the short horizons — chart patterns, indicators, and price action are primary drivers
- Fundamental short-term catalysts (inventory reports, OPEC news) can cause abrupt moves that must be accounted for

### Pros and Cons

**Intraday:**
- Avoids overnight gaps (no exposure when markets are closed)
- Can use tighter stop-losses
- Requires constant attention
- Incurs more transaction costs due to high frequency

**Swing:**
- More flexibility in monitoring (don't need to watch every tick)
- Fewer trades
- Accepts overnight risk (price gaps on news/events)
- Must set wider stops to tolerate normal multi-day volatility

**Blended approach:** Occasionally day trade around major news for quick moves, while also holding swing positions when a strong multi-day trend is identified.

---

## Instrument Choice: Crude Oil & Natural Gas

### Market Focus

The plan centers on crude oil and natural gas — two highly traded commodities with deep liquidity and volatility. These markets often exhibit strong short-term movements due to:
- Supply-demand news
- Geopolitical events
- Weather (especially for natural gas)
- Inventory data

Specializing in oil and gas allows tuning the trading system to the unique rhythms of these markets:
- Crude oil reacts sharply to OPEC decisions and weekly U.S. inventory reports
- Natural gas is very sensitive to weather forecasts and seasonal demand

### Trading Vehicles: ETFs vs Futures

#### Commodity ETFs

Funds like USO (WTI crude oil) or UNG (natural gas) that trade like stocks.

**Pros:**
- Easy to trade (no specialized futures account needed)
- Simpler to manage (no contract expirations to roll)
- Suitable for beginners or smaller capital
- Position sizing in small increments (can buy even one share)
- Avoids high leverage of futures unless choosing leveraged ETFs

**Cons:**
- Don't perfectly track commodity price over long periods (contango, management fees)
- Trade only during stock market hours (~9:30am-4pm ET)
- Gap risk from one day's close to next open

#### Futures Contracts

WTI crude oil (CL) and Henry Hub natural gas (NG) futures on NYMEX.

**Pros:**
- Pure, direct exposure with near 24-hour trading (Globex)
- React to overnight events immediately
- Capital-efficient due to leverage
- No management fees
- Excellent liquidity and real-time tracking

**Cons:**
- High leverage is double-edged — requires strict risk management
- Requires specialized brokerage account
- Must understand contract specifications (expiry, rollover)
- Standard contract sizes may be too large (though micro futures exist: MCL = 100 barrels)

### Recommendation

Start with **ETFs** (USO, UNG) for simplicity. They provide sufficient volatility and volume for intraday/swing trading and integrate easily with stock trading platforms. Consider transitioning to futures (perhaps micro futures) if finer control or extended trading hours become necessary.

---

## Multi-Agent System Architecture

The system is designed as a **production-grade multi-agent architecture** with 7 specialized agents working together to achieve high-precision, progressively autonomous trading.

Each agent has a single responsibility, communicates via shared state (PostgreSQL + Redis), and logs all decisions for complete auditability. The architecture supports both intraday and swing trading with intelligent strategy selection based on market conditions.

### Enhanced Agent Architecture (7 Agents)

**Architecture Diagram:**

```
                     +------------------+
                     |   Coordinator    |
                     | (Orchestrator)   |
                     +--------+---------+
                              |
    +-------------------------+-------------------------+
    |         |         |         |         |           |
+---v---+ +---v---+ +---v---+ +---v---+ +---v---+ +-----v-----+
|Market | |Strategy| |Strategy| | Risk  | |Settle-| |Execution |
| Data  | |Selector| |  Pool  | |Manager| | ment  | |  Agent   |
+-------+ +--------+ +--------+ +-------+ +-------+ +----------+
```

**Key Principles:**
- **Asynchronous operation:** 1-minute trading loop, WebSocket data streaming
- **Stateless agents:** All state in database, agents are pure functions
- **Multi-timeframe awareness:** All agents reason about 1m/5m/15m/1h/1d data
- **Progressive automation:** ADVISORY → PAPER_AUTO → LIVE_CONFIRM → LIVE_AUTO
- **Cash account compliance:** T+1 settlement tracking for PDT workaround

#### 1. Market Data Agent

**Responsibility:** Real-time data ingestion and multi-timeframe aggregation

**Core Functions:**
- Stream 1-minute bars via Alpaca WebSocket (USO, UNG)
- Aggregate to multiple timeframes: 1m → 5m → 15m → 1h → 1d
- Compute technical indicators across all timeframes (pandas-ta: RSI, MACD, EMA, ATR, Bollinger Bands, ADX)
- Cache hot data in Redis (15-minute TTL)
- Store historical data in PostgreSQL (partitioned by month)
- Validate data quality: check for gaps, stale timestamps, anomalous values
- Provide both streaming (WebSocket) and historical (REST) interfaces

**Data Flow:**
```
Alpaca WebSocket → 1m bars → Redis cache → Multi-timeframe aggregation → Indicators → Strategy agents
                                        ↓
                                  PostgreSQL (historical)
```

**Interface:**
```python
class MarketDataAgent:
    async def start_stream(self, symbols: list[str]) -> None
    async def get_latest_bars(self, symbol: str, timeframe: str, count: int = 100) -> pd.DataFrame
    async def get_indicators(self, symbol: str, timeframe: str) -> IndicatorSet
    async def get_multi_timeframe_snapshot(self, symbol: str) -> dict[str, pd.DataFrame]
```

#### 2. Strategy Selector Agent

**Responsibility:** Market regime detection and intelligent strategy selection

**Core Functions:**
- Detect current market regime using multi-timeframe analysis:
  - **TRENDING**: ADX > 25, directional move confirmed across 15m/1h/4h
  - **RANGING**: ADX < 20, price oscillating within Bollinger Bands
  - **VOLATILE**: Bollinger Band width > 95th percentile, ATR spike
- Select optimal strategy based on regime + time-of-day + time-until-close
- Decide between intraday vs swing position based on signal strength and market hours
- Weight and combine signals from multiple strategies
- Track regime transitions and adapt dynamically

**Selection Logic:**
```python
if regime == TRENDING and time_until_close > 2h:
    primary_strategy = TrendFollowing
    horizon = SWING if signal_strength > 0.8 else INTRADAY
elif regime == RANGING:
    primary_strategy = MeanReversion
    horizon = INTRADAY  # Always close ranging trades same-day
elif regime == VOLATILE and time_until_close < 1h:
    return HOLD  # Avoid late-day volatility
```

**Interface:**
```python
class StrategySelectorAgent:
    async def detect_regime(self, symbol: str) -> MarketRegime
    async def select_strategy(self, symbol: str, regime: MarketRegime) -> StrategyConfig
    async def determine_horizon(self, signal: Signal, time_remaining: timedelta) -> PositionHorizon
```

#### 3. Strategy Pool

**Responsibility:** Generate trading signals using multiple rule-based strategies

**Implemented Strategies:**

**a) Trend-Following:**
- 1h timeframe: 20/50 EMA crossover (primary trend)
- 15m timeframe: MACD histogram confirmation (momentum)
- 5m timeframe: Entry timing (RSI 40-60 for pullback entries)
- Volume confirmation: Volume > 20-period MA
- Stop-loss: 2× ATR(14) from entry
- Take-profit: 3× ATR(14) or trailing 1.5× ATR

**b) Mean-Reversion:**
- Price touches outer Bollinger Band (2σ) on 15m chart
- RSI extreme: < 30 for buy, > 70 for sell
- Volume spike: Volume > 1.5× 20-period MA (panic confirmation)
- Entry: Wait for first candle closing back inside BB
- Stop-loss: Beyond recent swing extreme + 1× ATR
- Take-profit: Middle BB (mean) or opposite BB

**c) Breakout (Phase 2):**
- Consolidation detection: Price range < 0.5× ATR for 10+ bars
- Volume drying up during consolidation
- Breakout trigger: Price + volume expansion beyond consolidation range
- Confirmation: Retest of breakout level holds

**Signal Output:**
```python
@dataclass
class Signal:
    symbol: str
    action: Literal["BUY", "SELL", "HOLD"]
    strategy: str
    confidence: float  # 0.0-1.0
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    position_horizon: Literal["INTRADAY", "SWING"]
    reasoning: str
    timeframe_analysis: dict[str, str]  # {1h: bullish, 15m: confirmed, 5m: entry}
```

**Interface:**
```python
class StrategyPool:
    async def analyze_all(self, symbol: str, data: MultiTimeframeData) -> list[Signal]
    async def get_strategy(self, name: str) -> BaseStrategy
```

#### 4. Risk Manager Agent

**Responsibility:** Capital protection, position sizing, portfolio risk management

**Core Functions:**

**Position Sizing:**
```python
# Risk-based sizing: Risk 1% of account per trade
risk_amount = account_balance * risk_per_trade_pct  # Default: 1%
price_risk = abs(entry_price - stop_loss)
position_size = risk_amount / price_risk

# Apply constraints
max_position_value = account_balance * max_single_position_pct  # Default: 10%
position_size = min(position_size, max_position_value / entry_price)
```

**Portfolio Risk Checks:**
- **Correlation check**: Reject if both USO and UNG are long/short (high correlation risk)
- **Portfolio heat**: Sum of all open position risks ≤ 5% of account
- **Concentration**: Single position ≤ 10% of account value
- **Margin usage**: N/A (cash account only)

**Circuit Breakers:**
- Daily loss limit: Halt if daily loss ≥ 3% of account
- Daily profit target: Consider reducing size if daily profit ≥ 2% (take chips off table)
- Consecutive losses: Halt after 3 consecutive losing trades (review strategy)
- Max trades per day: Limit to 10 trades (prevent overtrading)
- Stale data: Halt if last data update > 30 seconds old
- Extreme volatility: Halt if ATR > 3× 20-day average

**Time-Based Rules:**
- No new trades after 3:30 PM ET (avoid late-day volatility)
- Force close all INTRADAY positions at 3:55 PM ET
- SWING positions: Set exit orders, allow overnight hold

**Interface:**
```python
class RiskManagerAgent:
    async def validate_trade(self, signal: Signal, account: AccountState, positions: list[Position]) -> RiskDecision
    async def calculate_position_size(self, signal: Signal, account: AccountState) -> int
    async def check_circuit_breakers(self) -> list[CircuitBreakerStatus]
    async def get_portfolio_heat(self, positions: list[Position]) -> Decimal
```

#### 5. Settlement Tracker Agent

**Responsibility:** Track T+1 settlement for cash account PDT compliance

**Core Functions:**
- Track cash settlement schedule: Trade date T → Settlement T+1
- Maintain available cash calculation:
  ```python
  available_cash = account_balance - unsettled_cash - open_position_value
  ```
- Prevent trading with unsettled funds (avoid Good Faith Violations)
- Track trade count per settled cash pool
- Provide settlement timeline for each position

**Settlement Rules:**
- Stock trade on Monday (T) → Cash settles Wednesday morning (T+1)
- Can re-trade with settled cash immediately (unlimited day trades)
- Cannot trade with unsettled cash until settlement date
- Track per-symbol: If sell USO on Monday, cannot buy USO with those proceeds until Wednesday

**Interface:**
```python
class SettlementTrackerAgent:
    async def get_available_cash(self, account_id: str) -> Decimal
    async def record_trade(self, trade: Trade) -> None
    async def get_settlement_schedule(self) -> list[SettlementEvent]
    async def can_trade_symbol(self, symbol: str, required_cash: Decimal) -> bool
```

#### 6. Execution Agent

**Responsibility:** Multi-mode order execution with progressive automation

**Execution Modes:**

**ADVISORY (Default):**
- Generate Discord notification with full signal details
- No automatic execution
- Human reviews and executes manually via broker

**PAPER_AUTO:**
- Automatically execute on Alpaca Paper Trading account
- Full logging and performance tracking
- No human confirmation required
- Use for strategy validation

**LIVE_CONFIRM:**
- Send Discord DM with approval buttons
- User has 30-120 seconds to approve/reject (configurable timeout)
- If timeout: Trade is rejected (safe default)
- If approved: Execute immediately
- Also available via dashboard button

**LIVE_AUTO:**
- Fully autonomous execution on live account
- **CRITICAL**: Requires `enable_live_auto=True` feature flag
- All safety layers still active (risk manager, circuit breakers, kill switch)
- Use only after 4+ weeks successful paper trading

**Order Management:**
- Place bracket orders: Entry + Stop-loss + Take-profit (all simultaneous)
- For INTRADAY: Market-on-close (MOC) fallback at 3:55 PM
- For SWING: Good-til-canceled (GTC) stop/limit orders
- Track order fills via Alpaca WebSocket
- Handle partial fills, rejections, timeout scenarios

**Interface:**
```python
class ExecutionAgent:
    async def execute(self, signal: Signal, decision: RiskDecision, mode: AutomationMode) -> ExecutionResult
    async def request_confirmation(self, signal: Signal, timeout: int) -> bool
    async def place_bracket_order(self, symbol: str, qty: int, entry: Decimal, stop: Decimal, target: Decimal) -> Order
    async def force_close_intraday_positions(self) -> list[Order]
```

#### 7. Coordinator

**Responsibility:** Orchestrate all agents, manage 1-minute trading loop

**Core Loop (Every 1 Minute):**
```python
async def trading_loop():
    # 1. Get latest market data
    for symbol in ["USO", "UNG"]:
        data = await market_data_agent.get_multi_timeframe_snapshot(symbol)

        # 2. Detect market regime
        regime = await strategy_selector_agent.detect_regime(symbol)

        # 3. Select optimal strategy
        strategy_config = await strategy_selector_agent.select_strategy(symbol, regime)

        # 4. Generate signals
        signals = await strategy_pool.analyze_all(symbol, data)

        # 5. Filter and rank signals
        best_signal = strategy_selector_agent.select_best_signal(signals, strategy_config)

        if best_signal.action != "HOLD":
            # 6. Risk validation
            account = await get_account_state()
            positions = await get_open_positions()

            # Check settlement
            available_cash = await settlement_tracker.get_available_cash(account.id)
            can_trade = await settlement_tracker.can_trade_symbol(symbol, best_signal.estimated_cost)

            if not can_trade:
                log_rejection(f"Insufficient settled cash for {symbol}")
                continue

            # Risk checks
            risk_decision = await risk_manager.validate_trade(best_signal, account, positions)

            # Circuit breaker check
            breakers = await risk_manager.check_circuit_breakers()
            if any(b.triggered for b in breakers):
                log_warning(f"Circuit breaker triggered: {breakers}")
                continue

            if risk_decision.approved:
                # 7. Execute (mode-dependent)
                result = await execution_agent.execute(
                    signal=best_signal,
                    decision=risk_decision,
                    mode=config.automation_mode
                )

                # 8. Log everything
                await log_decision(signal=best_signal, decision=risk_decision, result=result)
```

**Additional Responsibilities:**
- Manage agent lifecycle (startup, shutdown, health checks)
- Aggregate logs from all agents into unified audit trail
- Emit metrics: signals_generated, trades_executed, circuit_breakers_triggered
- Handle graceful shutdown: Close WebSocket connections, flush logs
- Manage kill switch: Emergency stop all trading, close all positions

**Interface:**
```python
class Coordinator:
    async def start(self) -> None
    async def stop(self) -> None
    async def health_check(self) -> dict[str, AgentHealth]
    async def trigger_kill_switch(self, reason: str) -> None
```

### Communication & Flow

**Architecture:**
- **Database:** PostgreSQL for persistent state (positions, signals, decisions, audit logs)
- **Cache:** Redis for hot data (latest bars, indicators, agent state)
- **Message Flow:** Async function calls (asyncio) - no message queue needed for single-process deployment
- **Shared State:** Each agent reads/writes to database + cache, maintains no internal state
- **Audit Trail:** Every agent decision logged to `agent_decisions` table with full context

**Data Flow Example:**
```
1. Market Data Agent → Redis (latest_bars:USO:1m) → PostgreSQL (bars_1m table)
2. Strategy Selector → Read Redis → Compute regime → Write Redis (regime:USO)
3. Strategy Pool → Read Redis → Generate signals → Write PostgreSQL (signals table)
4. Risk Manager → Read PostgreSQL (positions, daily_limits) → Validate → Write (decisions table)
5. Execution Agent → Read decision → Alpaca API → Write (executions table)
6. Coordinator → Aggregate logs → PostgreSQL (audit_log table)
```

**Key Principles:**
- **Stateless Agents:** All state externalized to database/cache
- **Idempotent Operations:** Agents can be restarted without data loss
- **Full Auditability:** Every decision traceable through logs
- **Real-time Monitoring:** All agents emit health metrics every 1 minute

---

## Modeling Techniques for Prediction

### Pragmatic MVP Approach: Rules + Simple ML

**Philosophy:** Start simple, add complexity only when proven necessary. Most retail traders succeed with disciplined rules, not sophisticated ML.

### Phase 1: Rule-Based (No ML)

Pure technical analysis using proven indicators:
- **Trend:** 20/50/200 EMA crossovers, MACD
- **Momentum:** RSI (overbought/oversold thresholds)
- **Volatility:** ATR for stop-loss sizing, Bollinger Bands for mean reversion
- **Volume:** Volume spikes as confirmation
- **Support/Resistance:** Price levels from recent swings

**Signal generation:** Simple IF/THEN rules (e.g., "BUY if: uptrend + RSI < 40 + MACD bullish cross")

### Phase 2: Feature-Based ML (If Phase 1 Works)

Only add ML if rule-based approach proves profitable in paper trading:
- **Model:** LightGBM or XGBoost (much faster than LSTM, often better for tabular data)
- **Features:** Technical indicators, time features (hour, day, month), volatility metrics, recent returns
- **Target:** Binary classification (buy/sell/hold) or regression (next period return)
- **Validation:** Walk-forward testing (train on past, test on future, never leak)

### Phase 3: Deep Learning (Optional, Long-Term)

**LSTM/Transformer networks** only if:
1. You have 3+ years of quality data
2. Feature-based ML is profitable but hitting limits
3. You have GPU compute available
4. You're willing to invest weeks in hyperparameter tuning

**Reality check:** Many successful algorithmic traders never use deep learning. Edge comes from discipline, risk management, and speed—not model sophistication.

### Model Usage by Agent

- **Technical Agent (MVP):** Pure indicator logic with tunable thresholds
- **Fundamental Agent (Phase 2):** Keyword sentiment (count "bullish" words vs "bearish"), upgrade to BERT later if needed
- **Risk Agent:** ATR-based position sizing (no ML needed)
- **Strategy Agents:** Each implements different rule set (breakout vs mean reversion)

### Ensemble Decision-Making

The multi-agent architecture IS the ensemble:
- Each agent votes (buy/sell/hold)
- Coordinator requires 2+ agents to agree before trading
- Conflicting signals = no trade (preserves capital)
- Weights can be tuned based on backtest performance

---

## Technology Stack

### Core (Production Choices)

- **Language:** Python 3.12+ (required for pandas-ta, async improvements)
- **Data manipulation:** Pandas 2.x, NumPy
- **Technical indicators:** pandas-ta (pure Python, easier than TA-Lib compilation)
- **Async framework:** asyncio + aiohttp + websockets
- **HTTP:** httpx (async-capable, modern replacement for requests)
- **Configuration:** pydantic-settings (typed config from .env)
- **ML (Phase 2+):** scikit-learn first, defer LSTM until proven necessary

### Data Sources & Real-Time Feeds

1. **Live market data:** Alpaca WebSocket (real-time 1-minute bars, free for paper account)
2. **Historical data:** Alpaca REST API for backfill (USO, UNG)
3. **Broker execution:** Alpaca Trading API (paper → live with progressive automation)
4. **News/fundamentals (Phase 2):** NewsAPI free tier, EIA API (public, no key needed)

### Persistence & Caching

**Database:** PostgreSQL 14+ (AWS RDS)
- **Why:** Production-grade reliability, JSONB support, table partitioning for time-series data
- **Schema:** 10+ tables (bars_1m, bars_aggregated, positions, signals, decisions, executions, settlements, circuit_breakers, daily_limits, audit_log)
- **Partitioning:** Monthly partitions for bars_1m table (efficient queries, easy archival)

**Cache:** Redis 7+ (AWS ElastiCache)
- **Why:** Sub-millisecond latency for hot data, pub/sub for agent coordination
- **Usage:** Latest bars, computed indicators, market regime state, agent health
- **TTL:** 15 minutes for indicator cache, 1 minute for bars

**Migrations:** Alembic (database version control)

### Execution & Scheduling

- **Broker SDK:** alpaca-py (official SDK, well-maintained)
- **Scheduler:** AWS Lambda (1-minute cron) for trading loop
- **Async:** asyncio + asyncpg + websockets (core architecture, not optional)
- **Concurrency:** Single-threaded asyncio event loop (simpler than multi-process)

### Monitoring & Alerts

**Notifications:**
- **Primary:** Discord bot (discord.py) with interactive buttons for LIVE_CONFIRM mode
- **Fallback:** Discord webhook for simple alerts
- **Dashboard:** Real-time status updates

**Observability:**
- **Logging:** Structured JSON logs to CloudWatch Logs
- **Metrics:** CloudWatch custom metrics (latency, signal count, execution success rate)
- **Alarms:** CloudWatch alarms for circuit breakers, stale data, API errors
- **Dashboard:** Streamlit app on EC2 (real-time position monitoring, P&L charts, config management)

**Runbook:** Automated updates via Gemini context packs

### Cloud Infrastructure (AWS)

**Core Services:**
- **RDS PostgreSQL:** db.t3.micro ($15/mo, covered by student credits)
- **ElastiCache Redis:** cache.t3.micro ($12/mo, covered by student credits)
- **Lambda:** Trading loop execution ($0.20/mo for ~30K invocations)
- **EC2 t3.micro:** Streamlit dashboard host ($8/mo)
- **Secrets Manager:** API keys and credentials ($0.40/mo)
- **CloudWatch:** Logs + metrics + alarms ($5/mo)

**Why AWS:**
- $100 student credits (2+ months free)
- Lambda perfect for 1-minute scheduled tasks
- RDS auto-backups and point-in-time recovery
- ElastiCache managed Redis with automatic failover
- Integrated logging/monitoring via CloudWatch

**Total Cost:** ~$42/mo (covered by student credits initially)

### Development Tools

- **Package management:** uv (fast, modern, better than pip/venv)
- **Linting:** ruff (all-in-one: flake8 + black + isort replacement)
- **Testing:** pytest + pytest-asyncio + pytest-cov
- **Type checking:** mypy (strict mode recommended for production)
- **Research:** Jupyter notebooks (analysis only, not production code)
- **Local dev:** Docker Compose for PostgreSQL + Redis (mirrors AWS setup)

---

## Development Phases

### Phase 1: Core Infrastructure (Priority: HIGH)

**Objective:** Build production-grade foundation with real-time data and database

**Deliverables:**
1. Configuration system (pydantic models, .env support)
2. PostgreSQL database setup (SQLAlchemy async, Alembic migrations)
3. Redis caching layer
4. Market Data Agent (Alpaca WebSocket, 1-minute bars)
5. Multi-timeframe aggregation (1m → 5m → 15m → 1h → 1d)
6. Basic indicator computation (RSI, MACD, EMA, ATR, Bollinger Bands)

**Files to create:**
- `src/core/config.py` - TradingConfig, DatabaseConfig, AlpacaConfig
- `src/core/database.py` - SQLAlchemy async setup, session management
- `src/services/redis_cache.py` - Redis client wrapper
- `src/agents/market_data.py` - Alpaca WebSocket streaming
- `src/services/indicators.py` - Multi-timeframe indicator computation
- `alembic/versions/001_initial_schema.py` - Database migration

**Success criteria:**
- 1-minute bars streaming from Alpaca to PostgreSQL
- Redis caching working with TTL
- Multi-timeframe aggregation validated
- Indicators computed correctly across all timeframes

### Phase 2: Strategy Framework

**Objective:** Implement Strategy Selector and Strategy Pool agents

**Deliverables:**
1. Market regime detection (TRENDING, RANGING, VOLATILE)
2. Strategy Selector Agent (regime detection + strategy selection)
3. Base strategy interface
4. Trend-following strategy implementation
5. Mean-reversion strategy implementation
6. Signal generation with multi-timeframe analysis

**Files to create:**
- `src/agents/strategy_selector.py` - Regime detection, strategy selection
- `src/agents/strategy_pool.py` - Strategy container
- `src/strategies/base.py` - Abstract strategy interface
- `src/strategies/trend_following.py` - EMA, MACD strategies
- `src/strategies/mean_reversion.py` - Bollinger Band, RSI strategies
- `src/models/signal.py` - Signal data models

**Success criteria:**
- Regime detection working on historical data
- Signals generated with confidence scores
- Multi-timeframe analysis producing consistent signals
- Strategy selection adapting to regime changes

### Phase 3: Risk & Settlement

**Objective:** Implement Risk Manager and Settlement Tracker agents

**Deliverables:**
1. Position sizing (risk-based, 1% per trade)
2. Portfolio risk checks (correlation, heat, concentration)
3. Circuit breakers (daily limits, consecutive losses, stale data)
4. T+1 settlement tracking for cash account
5. Settlement-aware trade validation

**Files to create:**
- `src/agents/risk_manager.py` - Risk validation, position sizing
- `src/agents/settlement_tracker.py` - T+1 tracking
- `src/services/circuit_breakers.py` - Circuit breaker logic
- `src/models/risk.py` - Risk calculation models
- `src/models/settlement.py` - Settlement data models

**Success criteria:**
- Position sizing correctly calculated based on 1% risk
- Circuit breakers trigger at correct thresholds
- Settlement tracking prevents trading with unsettled funds
- Portfolio heat calculated correctly

### Phase 4: Execution & Notifications

**Objective:** Implement multi-mode execution with Discord confirmations

**Deliverables:**
1. Execution Agent with 4 automation modes
2. Discord bot with interactive confirmation buttons
3. Alpaca order placement (bracket orders)
4. Order status tracking
5. Kill switch implementation

**Files to create:**
- `src/agents/execution.py` - Multi-mode execution
- `src/services/discord_bot.py` - Interactive Discord confirmations
- `src/services/order_manager.py` - Alpaca order placement
- `src/services/kill_switch.py` - Emergency stop

**Success criteria:**
- ADVISORY mode sends Discord notifications
- PAPER_AUTO executes on paper account
- LIVE_CONFIRM waits for Discord approval with timeout
- LIVE_AUTO blocked by feature flag
- Kill switch closes all positions

### Phase 5: Coordinator & Dashboard

**Objective:** Build orchestrator and real-time monitoring dashboard

**Deliverables:**
1. Coordinator agent (1-minute trading loop)
2. Agent lifecycle management
3. Streamlit dashboard (positions, P&L, config)
4. Health checks and metrics
5. Audit logging

**Files to create:**
- `src/coordinator.py` - Main orchestrator
- `dashboard/app.py` - Streamlit main entry
- `dashboard/pages/positions.py` - Position monitoring
- `dashboard/pages/config.py` - Runtime config
- `dashboard/pages/performance.py` - P&L charts
- `src/services/audit_log.py` - Unified logging

**Success criteria:**
- Trading loop running every 1 minute
- Dashboard shows real-time positions
- Config adjustable without restart
- All agent decisions logged to database

### Phase 6: AWS Deployment

**Objective:** Deploy to AWS with Lambda, RDS, and ElastiCache

**Deliverables:**
1. Terraform infrastructure (RDS, ElastiCache, Lambda, EC2)
2. Lambda handler for trading loop
3. Secrets Manager integration
4. CloudWatch logging and alarms
5. Deployment automation

**Files to create:**
- `infrastructure/terraform/main.tf` - AWS infrastructure
- `lambda_handlers/trading_loop.py` - Trading loop Lambda
- `lambda_handlers/settlement_check.py` - Daily settlement check
- `scripts/deploy.py` - Deployment automation
- `scripts/setup_secrets.py` - Secrets Manager setup

**Success criteria:**
- Trading loop running on Lambda (1-minute schedule)
- RDS PostgreSQL accessible from Lambda
- ElastiCache Redis connected
- Streamlit dashboard on EC2
- CloudWatch alarms configured

---

## Risk Management & Testing Protocols

### Backtesting Requirements
- Test on several years of data covering different environments (2020 oil crash, 2022 gas spike, etc.)
- Track drawdowns, win/loss ratio, consistency across time
- Walk-forward analysis
- Backtest components individually

### Paper Trading
- Run in broker's paper trading mode for weeks/months
- Verify data arrives correctly, orders execute properly
- Track slippage vs backtest expectations

### Go-Live Protocol
- Start with small capital/position sizes
- Scale up only after confidence established

### Hard Risk Limits
- **Risk per trade:** 1-2% of account maximum
- **Max drawdown:** Define threshold (e.g., 10-20%), pause if hit
- **Correlation awareness:** Reduce size when both oil and gas positions are aligned

### Execution Safety
- Every trade must have stop-loss order lodged with broker (server-side)
- Use take-profit orders where appropriate
- Don't rely solely on program logic for exits

### Monitoring
- Daily log review
- Alerts for unusual events
- Watch for market regime changes

### Compliance & PDT Workaround

**Cash Account Strategy (< $25k capital):**
- Use cash account instead of margin account to bypass Pattern Day Trader rule
- **Benefit:** Unlimited day trades (vs 3 trades/5 days on margin)
- **Constraint:** Must wait T+1 for cash settlement before re-trading
- **Solution:** Settlement Tracker Agent prevents trading with unsettled funds

**Settlement Rules:**
- Trade executed Monday (T) → Cash settles Wednesday morning (T+1)
- Can immediately re-trade with settled cash
- Cannot use unsettled cash (triggers Good Faith Violation)
- System automatically tracks settlement schedule per symbol

**Margin Account (if capital ≥ $25k):**
- Can switch to margin account for instant buying power
- No settlement delays
- Can short sell (if desired for future strategies)
- PDT rule no longer applies

---

## Cost-Benefit Summary

| Choice | Benefits | Costs |
|--------|----------|-------|
| **Trading Style** | | |
| Intraday trading | No overnight risk, daily compounding potential | Time-intensive, higher transaction costs |
| Swing trading | Less screen time, larger per-trade profits | Overnight gap risk, wider stops needed |
| **Instruments** | | |
| ETFs (USO, UNG) | Simple, no special account, easy sizing | Small fees, tracking error, limited hours |
| Futures (CL, NG) | Direct exposure, 24-hour trading, no fund fees | Complex, high leverage, requires expertise |
| **Architecture** | | |
| 7-agent system | Robust, modular, specialized responsibilities | Development time, debugging complexity |
| Multi-timeframe analysis | Better signal quality, regime adaptation | Higher data volume, computation overhead |
| Progressive automation | Safety through gradual trust-building | Longer validation period before full auto |
| **Data & Infrastructure** | | |
| 1-minute bars | High precision, captures short-term moves | Higher storage costs, more data processing |
| PostgreSQL + Redis | Production-grade, scalable, reliable | Setup complexity, monthly cost (~$27) |
| AWS deployment | 24/5 availability, student credits, managed services | Learning curve, monthly cost (~$42) |
| Alpaca WebSocket | Real-time data, free for paper account | Requires async programming, WebSocket handling |
| **Compliance** | | |
| Cash account (< $25k) | Unlimited day trades, no PDT restriction | T+1 settlement delays, must track settled cash |
| Margin account (≥ $25k) | Instant buying power, no settlement delays | PDT rule applies (3 trades/5 days if < $25k) |
| **ML/Modeling** | | |
| Rule-based strategies | Transparent, debuggable, fast to implement | May miss complex patterns |
| LSTM/Deep Learning | Higher prediction accuracy potential | Data needs, compute resources, overfit risk |

---

## References

1. Day Trading vs. Swing Trading - Investopedia
2. Day Trading vs. Swing Trading Futures - Iron Beam
3. Commodity ETFs vs. Futures - Go4Trades/Medium
4. Crude Oil: Futures vs ETFs - CME Group
5. Ensemble Decision-Making in Multi-Agent Systems - EmergentMind
6. Building a Deep Thinking Trading System with Multi-Agentic Architecture - Level Up Coding
7. Forecasting crude oil price using LSTM neural networks - AIMS Press
8. Predicting WTI Crude Oil Returns Using Machine Learning - Stevens Institute
9. Natural gas price prediction based on AI models - PLOS One
10. Short-term Petroleum Price Prediction (LSTM/LightGBM) - DR Press
11. Multivariate natural gas price forecasting - ScienceDirect
12. Energy futures trading strategies using RL - ScienceDirect
13. Building Multi-Agent Trading with Agno Framework - Medium