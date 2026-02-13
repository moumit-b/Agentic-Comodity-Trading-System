# Agentic Commodity Trading System

A **production-grade, multi-agent AI trading system** for crude oil (USO) and natural gas (UNG) ETFs, featuring GenAI-powered sentiment analysis, recursive self-learning, and a 7-layer safety architecture.

**Status:** Paper Trading (PAPER_AUTO) | 89/89 Tests Passing | Groq LLM Live

---

## Vision

Build a progressively autonomous commodity trading system that:

1. **Starts advisory-only** — generates signals, never auto-trades without permission
2. **Graduates to paper trading** — executes on Alpaca paper account with full safety rails
3. **Learns from its own decisions** — LLM-powered recursive learning tunes strategy parameters automatically
4. **Scales to live trading** — human confirmation required before any real-money execution

The system is designed around a **safety-first philosophy**: it will always prefer no-trade over a risky-trade, and every decision is logged for full audit trail.

---

## How It Works

### The Trading Pipeline (Every 60 Seconds)

```
                         MARKET DATA
                    Finnhub WebSocket (1m bars)
                    Alpaca API (account/positions)
                              |
                              v
                    +--------------------+
                    |  MarketDataAgent   |
                    |  Aggregates bars:  |
                    |  1m -> 5m -> 15m   |
                    |  Calculates RSI,   |
                    |  MACD, BB, EMA     |
                    +--------+-----------+
                             |
                             v
                    +--------------------+
                    | StrategySelector   |
                    | Detects market     |    "Is the market trending
                    | regime (trending/  |     or mean-reverting?"
                    | ranging/volatile)  |
                    +--------+-----------+
                             |
                             v
                    +--------------------+
                    |   StrategyPool     |    4 strategies run in parallel:
                    | - Bollinger Bands  |    - Mean reversion strategies
                    | - RSI Over/Under   |    - Trend following strategies
                    | - EMA Crossover    |    Each outputs a Signal with
                    | - MACD Trend       |    direction + confidence score
                    +--------+-----------+
                             |
                             v
                    +--------------------+
                    |   ContextAgent     |    LLM analyzes news headlines
                    |   (Groq LLM)      |    and adjusts ALL signal
                    |   Sentiment +0.8   |    confidences before ranking
                    |   Regime: Supply   |
                    +--------+-----------+
                             |
                             v
                    +--------------------+
                    |   RiskManager      |    7 validation checks:
                    |   Position sizing  |    - Max positions
                    |   Stop-loss calc   |    - Portfolio heat
                    |   Risk/reward      |    - Settlement (T+1)
                    +--------+-----------+
                             |
                             v
                    +--------------------+
                    | CircuitBreakers    |    7 safety breakers:
                    | Daily loss limit   |    - Loss/profit limits
                    | Kill switch        |    - Stale data detection
                    | Volatility spike   |    - Manual kill switch
                    +--------+-----------+
                             |
                             v
                    +--------------------+
                    | ExecutionAgent     |    Paper: auto-execute
                    | Alpaca API order   |    Live: requires human
                    | Discord alert      |    confirmation via Discord
                    +--------------------+
```

### The Learning Loop (Background, Continuous)

```
    Every signal -----> PREDICT: Log prediction to DB
                            |
    Every 5 min ------> OBSERVE: Compare predictions vs actual prices
                            |                   "Was I right?"
    Every 15 min -----> REFLECT: LLM analyzes accuracy patterns
                            |                   "Why was I wrong?"
                            v
                     Auto-apply strategy parameter adjustments
                     (RSI thresholds, confidence multipliers)
                     with 24h expiry and magnitude safety rails
```

---

## Tech Stack

### Core

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Language** | Python 3.13 | Async-first with type hints |
| **Framework** | asyncio + SQLAlchemy 2.0 | Fully async data pipeline |
| **Package Manager** | uv | Fast dependency resolution |
| **Linting** | Ruff | Code quality enforcement |
| **Testing** | pytest + pytest-asyncio | 89 tests, in-memory SQLite |

### AI / LLM

| Provider | Model | Purpose | Cost |
|----------|-------|---------|------|
| **Groq** | Llama 3.3 70B Versatile | Sentiment analysis, RLM reflection | Free (1000 req/day) |
| **Gemini** | 2.5 Flash-Lite | Fallback provider (planned) | Free (1000 req/day) |

### Data & Trading

| Service | Purpose |
|---------|---------|
| **Finnhub** | Real-time WebSocket market data (1-minute bars) |
| **Alpaca** | Paper/live trading execution, account management |
| **pandas + pandas-ta** | OHLCV aggregation, technical indicators |

### Infrastructure

| Service | Purpose |
|---------|---------|
| **AWS EC2** | Continuous trading loop (primary) |
| **AWS Lambda** | Serverless trading cycle (backup) |
| **AWS RDS (PostgreSQL)** | Persistent storage for signals, executions, learning |
| **AWS ElastiCache (Redis)** | LLM response caching, rate limiting |
| **AWS Secrets Manager** | API keys (Alpaca, Groq, Discord) |
| **Terraform** | Infrastructure as code |
| **Discord** | Trade notifications, kill switch commands |

### API & Dashboard

| Component | Technology |
|-----------|-----------|
| **REST API** | FastAPI with JWT auth, rate limiting |
| **Dashboard** | Streamlit with Plotly charts |
| **WebSocket** | Real-time price streaming to dashboard |

---

## Agent Architecture

The system is composed of **11 specialized agents** that communicate through a central coordinator:

```
src/
  agents/
    coordinator.py          # Master orchestrator - runs the trading pipeline
    market_data.py          # Ingests and aggregates OHLCV bars from Finnhub
    finnhub_data.py         # WebSocket connection to Finnhub for real-time data
    strategy_selector.py    # Detects market regime, selects active strategies
    strategy_pool.py        # Executes all active strategies in parallel
    context_agent.py        # LLM-powered news sentiment analysis
    learning_observer.py    # Recursive Learning Model (predict/observe/reflect)
    risk_manager.py         # Position sizing, risk/reward validation
    settlement_tracker.py   # T+1 cash settlement tracking (PDT compliance)
    execution_agent.py      # Routes trades to Alpaca (paper or live)

  strategies/
    base.py                 # Abstract strategy with dynamic threshold support
    mean_reversion.py       # Bollinger Bands + RSI strategies
    trend_following.py      # EMA Crossover + MACD strategies

  services/
    llm_service.py          # Multi-provider LLM with rate limiting + caching
    circuit_breakers.py     # 7-layer safety system with kill switch
    alpaca_api.py           # Alpaca trading API wrapper
    discord_notifier.py     # Trade alerts and kill switch via Discord
    redis_cache.py          # Redis caching layer
    task_scheduler.py       # Background RLM tasks (observe/reflect/news)

  api/
    main.py                 # FastAPI application
    auth.py                 # JWT authentication
    routers/                # REST endpoints (signals, executions, risk, etc.)

  models/                   # SQLAlchemy ORM (signals, executions, positions, etc.)
  core/                     # Config (Pydantic Settings) + Database setup
```

---

## Safety Architecture (7 Layers)

| Layer | Protection | What It Does |
|-------|-----------|-------------|
| 1 | **Daily Loss Limit** | Stops trading if daily P&L drops below -3% |
| 2 | **Daily Profit Target** | Takes profits at +5% to prevent giveback |
| 3 | **Consecutive Losses** | Pauses after 3 consecutive losing trades |
| 4 | **Portfolio Heat** | Caps total risk exposure at 5% of portfolio |
| 5 | **Volatility Spike** | Halts trading during abnormal market moves |
| 6 | **Stale Data** | Rejects signals if market data is outdated |
| 7 | **Manual Kill Switch** | Instant halt via Discord command or dashboard |

Fail-safe behavior: If the database is unreachable, the kill switch defaults to **ACTIVE** (no trading).

---

## Automation Modes

The system supports 4 progressive automation levels:

| Mode | Signals | Execution | Confirmation |
|------|---------|-----------|-------------|
| `ADVISORY` | Generated | Logged only | N/A |
| `PAPER_AUTO` | Generated | Auto-executed on paper account | N/A |
| `LIVE_CONFIRM` | Generated | Queued | Human via Discord |
| `LIVE_AUTO` | Generated | Auto-executed live | N/A |

**Current mode: `PAPER_AUTO`** — signals are automatically executed on Alpaca's paper trading environment with full safety rails active.

---

## Recursive Learning Model (RLM)

The system improves its own trading strategies through a 3-phase LLM-powered cycle:

### Phase 1: PREDICT
Every trading signal is logged with its predicted direction, target price, and confidence.

### Phase 2: OBSERVE (every 5 minutes)
Pending predictions are checked against actual price movements. Each prediction is marked correct or incorrect.

### Phase 3: REFLECT (every 15 minutes)
The LLM analyzes prediction accuracy patterns and suggests parameter adjustments:

```json
{
  "reflection": "RSI oversold threshold at 35 is too aggressive...",
  "suggested_adjustment": {
    "parameter": "oversold_threshold",
    "direction": "increase",
    "magnitude": "small",
    "reason": "Entering positions too early in downtrends"
  }
}
```

Adjustments are auto-applied in paper mode with:
- **Max 20% magnitude** change per adjustment
- **24-hour expiry** — overrides revert automatically
- **Full audit trail** in `strategy_overrides` table

---

## Dynamic Thresholds

Strategy parameters adapt to market conditions in real-time:

| Market Condition | RSI Oversold | RSI Overbought | Why |
|-----------------|-------------|----------------|-----|
| High Volatility (ATR > 3%) | 30 | 70 | Wait for extreme conditions |
| Normal Volatility | 35 | 65 | Standard thresholds |
| Low Volatility (ATR < 1%) | 40 | 60 | Catch smaller movements |

RLM overrides layer on top of volatility-based adjustments.

---

## Project Structure

```
Agentic-Comodity-Trading-System/
  src/                          # Application source code
    agents/                     # 10 specialized trading agents
    strategies/                 # 4 trading strategies (mean reversion + trend)
    services/                   # LLM, circuit breakers, Alpaca, Discord, Redis
    api/                        # FastAPI REST API + WebSocket
    models/                     # SQLAlchemy ORM models
    core/                       # Configuration + database setup
  tests/                        # 89 tests (Phase 2-5 coverage)
  scripts/                      # Entry points (trading cycle, continuous loop)
  infrastructure/
    terraform/                  # AWS infrastructure as code
    lambda/                     # Lambda deployment (Dockerized)
  alembic/                      # Database migrations
  pharma-research-groq/         # Separate Groq research module
  docs/                         # Architecture documentation
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Groq API key (free at [console.groq.com](https://console.groq.com))
- Alpaca API key (free paper trading at [alpaca.markets](https://alpaca.markets))
- Finnhub API key (free at [finnhub.io](https://finnhub.io))

### Setup

```bash
# Clone
git clone https://github.com/moumit-b/Agentic-Comodity-Trading-System.git
cd Agentic-Comodity-Trading-System

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys:
#   GROQ_API_KEY=gsk_...
#   ALPACA_API_KEY=...
#   ALPACA_API_SECRET=...
#   FINNHUB_API_KEY=...

# Run tests
uv run pytest tests/ -v

# Run a single trading cycle
uv run python scripts/run_trading_cycle.py

# Run continuous trading loop (production)
uv run python scripts/run_continuous_loop.py
```

### AWS Deployment

```bash
# Deploy infrastructure
cd infrastructure/terraform
terraform init
terraform apply

# Set secrets in AWS Secrets Manager
aws secretsmanager put-secret-value \
  --secret-id trading-system/alpaca/credentials \
  --secret-string '{"api_key":"...","api_secret":"..."}'

aws secretsmanager put-secret-value \
  --secret-id trading-system/llm/credentials \
  --secret-string '{"groq_api_key":"gsk_..."}'
```

---

## Configuration

All settings use Pydantic Settings with env var overrides:

### Phase 2 Feature Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `ENABLE_CONTEXT_AGENT` | `true` | LLM-powered sentiment analysis |
| `ENABLE_RLM` | `true` | Recursive Learning Model |
| `RLM_AUTO_APPLY` | `true` | Auto-apply strategy overrides (paper mode) |
| `ENABLE_DYNAMIC_THRESHOLDS` | `true` | Volatility-adjusted strategy parameters |

### Key Parameters

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `MAX_POSITIONS` | 3 | Maximum concurrent positions |
| `RISK_PER_TRADE` | 1.5% | Max risk per individual trade |
| `MAX_PORTFOLIO_HEAT` | 5% | Max total portfolio risk exposure |
| `DAILY_LOSS_LIMIT` | -3% | Circuit breaker trigger |
| `SYMBOLS` | USO, UNG | Traded commodity ETFs |

---

## Test Results

```
89 passed, 0 failed (4.5s)

Phase 2 (GenAI):     26 tests - LLM service, sentiment, RLM, dynamic thresholds
Phase 2 (Strategy):  16 tests - Strategy pool, selector, signal ranking
Phase 3 (Risk):      18 tests - Risk manager, settlement, circuit breakers
Phase 4 (Execution): 16 tests - Execution modes, confirmations, Discord
Phase 5 (Coord):      8 tests - Full coordinator pipeline integration
Bootstrap:             5 tests - Project structure validation
```

---

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | Done | Rule-based trading infrastructure (strategies, data pipeline) |
| Phase 2 | Done | GenAI agentic orchestration (Groq LLM, RLM, sentiment) |
| Phase 3 | Done | Risk management (7-check validation, circuit breakers) |
| Phase 4 | Done | Execution pipeline (Alpaca integration, confirmations) |
| Phase 5 | Done | Coordinator orchestration (full pipeline wiring) |
| Phase 6 | Next | Live paper trading validation + performance monitoring |
| Phase 7 | Planned | Live trading with human confirmation (LIVE_CONFIRM) |
| Phase 8 | Planned | Full autonomy with monitoring (LIVE_AUTO) |

---

## License

MIT
