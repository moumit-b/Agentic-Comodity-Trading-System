# Project Runbook

> **Last Updated:** 2025-12-31 (Enhanced Production Architecture)
>
> **Current Phase:** Documentation Complete → Phase 1 (Core Infrastructure) Starting
>
> **Model:** Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

---

## Current Status

### Documentation Phase ✅ COMPLETE

**What We Built:**
- [x] Repository structure with all directories
- [x] Python virtual environment (.venv) - Python 3.12+
- [x] Claude Code hooks (Python-based):
  - git_guard.py - blocks git commits/pushes
  - touch_marker.py - tracks file modifications
  - stop_quality_gate.py - runs ruff on session stop
- [x] Claude commands (ctx-refresh, ctx-ask, checkpoint)
- [x] Claude skills (context-pack, quality-gates, checkpoint, ctx-ask, ctx-refresh)
- [x] PowerShell scripts (gemini_context_pack.ps1, gemini_ask.ps1, quality_gate.ps1)
- [x] Initial pyproject.toml with dev dependencies
- [x] Bootstrap verification tests (5 tests passing)

**Enhanced Documentation:**
- [x] **docs/PROJECT_REQUIREMENTS.md** (1162 lines) - Complete production specification
  - 7-agent architecture with full interfaces
  - PostgreSQL database schema (10+ tables)
  - Progressive automation modes (ADVISORY → PAPER_AUTO → LIVE_CONFIRM → LIVE_AUTO)
  - Complete configuration system with TradingConfig models
  - AWS deployment architecture
  - 6 development phases with success criteria

- [x] **docs/COST_TRACKING.md** - Cost analysis and tracking
  - Monthly cost breakdown (~$42/mo, covered by AWS student credits)
  - Decision matrices for all paid services
  - Three cost scenarios (MVP $0, Live Trading $51-71, High-Volume $180)
  - Payment tracking checklist

- [x] **docs/TRADING_SYSTEM_PLAN.md** - Updated with production architecture
  - 7-agent architecture (Market Data, Strategy Selector, Strategy Pool, Risk Manager, Settlement Tracker, Execution, Coordinator)
  - 1-minute data frequency via Alpaca WebSocket
  - Multi-timeframe analysis (1m → 5m → 15m → 1h → 1d)
  - PostgreSQL + Redis stack
  - AWS Lambda deployment
  - Cash account PDT compliance strategy

**Key Architecture Decisions:**
1. **7-Agent System** (expanded from MVP's 5):
   - NEW: Strategy Selector Agent (market regime detection)
   - NEW: Settlement Tracker Agent (T+1 cash account compliance)
   - Enhanced: All other agents with production features

2. **Real-Time Data:** 1-minute bars via Alpaca WebSocket (not hourly yfinance)

3. **Production Database:**
   - PostgreSQL 14+ (AWS RDS) with monthly partitioning
   - Redis 7+ (AWS ElastiCache) for hot data caching
   - NOT SQLite (too limited for production)

4. **Progressive Automation:**
   - ADVISORY: Notifications only (default, safe)
   - PAPER_AUTO: Auto-execute on paper account
   - LIVE_CONFIRM: Discord DM + dashboard approval (30-120s timeout)
   - LIVE_AUTO: Full autonomous (feature flag protected)

5. **Cloud Deployment:** AWS with student credits (~$42/mo)
   - Lambda for 1-minute trading loop
   - RDS PostgreSQL (db.t3.micro)
   - ElastiCache Redis (cache.t3.micro)
   - EC2 for Streamlit dashboard

---

## Current Work: Phase 1 - Core Infrastructure

**Goal:** Build production-grade foundation with real-time data streaming

**In Progress:**
- [x] Documentation complete (PROJECT_REQUIREMENTS.md, COST_TRACKING.md, TRADING_SYSTEM_PLAN.md)
- [x] Runbook updated (this file)
- [ ] **NEXT:** Update pyproject.toml with production dependencies
- [ ] Create src/core/config.py with TradingConfig models
- [ ] Create src/core/database.py with SQLAlchemy async setup
- [ ] Create database schema migration (Alembic)
- [ ] Create src/agents/market_data.py with Alpaca WebSocket
- [ ] Create src/services/redis_cache.py

**Dependencies to Add:**
```toml
# Async & Networking
websockets = ">=12.0"
aiohttp = ">=3.9.0"

# Database
asyncpg = ">=0.29.0"
sqlalchemy = ">=2.0.0"
alembic = ">=1.13.0"
redis = ">=5.0.0"

# Dashboard
streamlit = ">=1.29.0"
plotly = ">=5.18.0"

# Discord
discord.py = ">=2.3.0"

# AWS
boto3 = ">=1.34.0"
aioboto3 = ">=12.0.0"
```

**Success Criteria:**
- [ ] 1-minute bars streaming from Alpaca to PostgreSQL
- [ ] Redis caching working with TTL
- [ ] Multi-timeframe aggregation validated (1m → 5m → 15m → 1h → 1d)
- [ ] Indicators computed correctly across all timeframes
- [ ] Tests passing with >80% coverage

---

## Development Phases

### Phase 1: Core Infrastructure (CURRENT)
**Priority:** HIGH
**Deliverables:**
- Configuration system (pydantic models, .env)
- PostgreSQL + Redis setup
- Market Data Agent with Alpaca WebSocket
- Multi-timeframe aggregation
- Indicator computation across timeframes

**Timeline:** Complete before moving to Phase 2

### Phase 2: Strategy Framework (NEXT)
**Deliverables:**
- Strategy Selector Agent (market regime detection)
- Strategy Pool (trend-following, mean-reversion)
- Signal generation with confidence scores
- Multi-timeframe signal validation

### Phase 3: Risk & Settlement
**Deliverables:**
- Risk Manager Agent (position sizing, circuit breakers)
- Settlement Tracker Agent (T+1 compliance)
- Portfolio risk checks
- Circuit breaker implementation

### Phase 4: Execution & Notifications
**Deliverables:**
- Execution Agent (4 automation modes)
- Discord bot with interactive confirmations
- Alpaca order placement (bracket orders)
- Kill switch implementation

### Phase 5: Coordinator & Dashboard
**Deliverables:**
- Coordinator (1-minute trading loop)
- Streamlit dashboard (real-time monitoring)
- Audit logging
- Health checks

### Phase 6: AWS Deployment
**Deliverables:**
- Terraform infrastructure
- Lambda deployment
- CloudWatch monitoring
- Production go-live

---

## Completed Items

### Enhanced Requirements Phase (2025-12-31)

- ✅ **Revised docs/PROJECT_REQUIREMENTS.md** (1162 lines)
  - Complete 7-agent architecture
  - Full database schema (10+ tables)
  - Progressive automation modes
  - Configuration system design
  - AWS deployment plan

- ✅ **Created docs/COST_TRACKING.md**
  - Monthly cost breakdown
  - Service decision matrices
  - Cost scenarios (MVP, Live Trading, High-Volume)
  - Payment tracking system

- ✅ **Revised docs/TRADING_SYSTEM_PLAN.md**
  - Updated multi-agent architecture section (7 agents)
  - Added 1-minute data streaming
  - Updated technology stack (PostgreSQL, Redis, AWS)
  - Enhanced development phases (6 phases)
  - Added PDT compliance strategy (cash account)
  - Updated cost-benefit summary

### Bootstrap Phase (2025-12-30)

- ✅ Reviewed and improved TRADING_SYSTEM_PLAN.md (initial version)
- ✅ Reviewed and improved DEV_WORKFLOW.md
- ✅ Audited directory structure
- ✅ Improved configuration files (CLAUDE.md, GEMINI.md, .gitignore)
- ✅ Created Python hooks
- ✅ Created initial PROJECT_REQUIREMENTS.md (basic version)
- ✅ Created initial runbook.md
- ✅ Created pyproject.toml with dev dependencies
- ✅ Installed dependencies via `uv sync --all-extras` (58 packages)
- ✅ Created bootstrap verification tests (5 tests, all passing)

---

## Key Architecture Details

### 7-Agent System

```
                     +------------------+
                     |   Coordinator    |
                     +--------+---------+
                              |
    +-------------------------+-------------------------+
    |         |         |         |         |           |
+---v---+ +---v---+ +---v---+ +---v---+ +---v---+ +-----v-----+
|Market | |Strategy| |Strategy| | Risk  | |Settle-| |Execution |
| Data  | |Selector| |  Pool  | |Manager| | ment  | |  Agent   |
+-------+ +--------+ +--------+ +-------+ +-------+ +----------+
```

1. **Market Data Agent** - Alpaca WebSocket, 1-minute bars, multi-timeframe aggregation
2. **Strategy Selector Agent** - Market regime detection, intelligent strategy selection
3. **Strategy Pool** - Trend-following, mean-reversion, breakout strategies
4. **Risk Manager Agent** - Position sizing, circuit breakers, portfolio risk
5. **Settlement Tracker Agent** - T+1 cash settlement tracking for PDT compliance
6. **Execution Agent** - Multi-mode execution (ADVISORY/PAPER_AUTO/LIVE_CONFIRM/LIVE_AUTO)
7. **Coordinator** - Agent orchestration, 1-minute trading loop

### Database Schema (PostgreSQL)

**Key Tables:**
- `bars_1m` - 1-minute bar data (partitioned by month)
- `bars_aggregated` - 5m, 15m, 1h, 1d bars
- `positions` - Open/closed positions with horizon (INTRADAY/SWING)
- `signals` - Generated signals with confidence scores
- `decisions` - Risk validation results
- `executions` - Order execution audit trail
- `settlements` - T+1 cash settlement tracking
- `circuit_breakers` - Trigger history
- `daily_limits` - Daily P&L tracking
- `config_overrides` - Runtime config changes

### Progressive Automation

| Mode | Behavior | Safety Level |
|------|----------|--------------|
| ADVISORY | Notifications only | Highest (default) |
| PAPER_AUTO | Auto-execute on paper | High |
| LIVE_CONFIRM | Discord approval required | Medium |
| LIVE_AUTO | Fully autonomous | Lower (feature flag) |

**Safety Layers:**
1. Feature flags (`enable_live_auto=False` by default)
2. Risk Manager validation
3. Settlement awareness (T+1 tracking)
4. Time-based rules (no trades after 3:30 PM)
5. Human confirmation (Discord DM + dashboard)
6. Kill switch (CLI + Discord + dashboard)
7. CloudWatch alarms

### Circuit Breakers

- Daily loss limit: Halt if loss ≥ 3% of account
- Daily profit target: Consider reducing size if profit ≥ 2%
- Consecutive losses: Halt after 3 consecutive losing trades
- Max trades per day: Limit to 10 trades
- Stale data: Halt if last update > 30 seconds old
- Extreme volatility: Halt if ATR > 3× 20-day average

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-31 | Use 7-agent architecture (not 5) | Added Strategy Selector + Settlement Tracker for production needs |
| 2025-12-31 | Use 1-minute bars (not hourly) | High precision trading, capture short-term moves, Alpaca WebSocket free |
| 2025-12-31 | Use PostgreSQL + Redis (not SQLite) | Production-grade reliability, table partitioning, caching layer required |
| 2025-12-31 | Deploy on AWS (not local) | 24/5 availability, student credits, managed services (RDS, ElastiCache) |
| 2025-12-31 | Progressive automation (4 modes) | Safety through gradual trust-building, explicit feature flags |
| 2025-12-31 | Cash account strategy (< $25k) | Unlimited day trades via T+1 settlement tracking (PDT workaround) |
| 2025-12-31 | Use Python 3.12+ (not 3.11) | Required for pandas-ta, async improvements |
| 2025-12-31 | Multi-timeframe analysis (1m→1d) | Better signal quality, regime adaptation, entry timing |
| 2025-12-30 | Use Python hooks instead of PowerShell | Consistency with codebase, easier testing |
| 2025-12-30 | Start with rule-based strategies | Simpler, faster to validate, defer ML until proven necessary |
| 2025-12-30 | Use pandas-ta instead of TA-Lib | Pure Python, no compilation issues on Windows |
| 2025-12-30 | Use Discord for notifications | Instant mobile alerts, interactive confirmations with discord.py |
| 2025-12-30 | Target ETFs (USO, UNG) not futures | Simpler, no contract rollovers, works with standard brokers |

---

## Development Workflow Reminders

### Daily Loop
1. **Start:** Review runbook, check current phase tasks
2. **Plan:** Update todo list, outline next chunk
3. **Build:** Implement in small diffs, keep changes focused
4. **Verify:** Run quality gates (`uv run ruff check .`, `uv run pytest`)
5. **Checkpoint:** Use `/checkpoint` when chunk complete (tests + context refresh)

### Key Commands
- `/ctx-refresh` - Refresh Gemini context pack (with cooldown)
- `/ctx-ask <question>` - Ask Gemini a big-context question
- `/checkpoint` - Run quality gates + force context refresh + update runbook

### Safety Reminders
- **Moumit controls all git actions** (commits, pushes, rebases)
- **No secrets in repo** (.env is gitignored, use AWS Secrets Manager)
- **Advisory-first mode** (ADVISORY is default, LIVE_AUTO requires explicit flag)
- **Test everything** (>80% coverage requirement)
- **All 7 safety layers active** (feature flags → kill switch)

---

## Testing Checklist

**Phase 1 (Core Infrastructure):**
- [ ] Alpaca WebSocket connects and streams 1-minute bars
- [ ] PostgreSQL schema created via Alembic migration
- [ ] Redis connection working with TTL
- [ ] Multi-timeframe aggregation produces correct bars
- [ ] Indicators match known values (RSI, MACD, EMA, ATR, BB)
- [ ] Data quality validation catches gaps/stale data

**Phase 2 (Strategy Framework):**
- [ ] Market regime detection accurate (TRENDING/RANGING/VOLATILE)
- [ ] Strategy selector chooses correct strategy for regime
- [ ] Signals generated with confidence scores
- [ ] Multi-timeframe analysis produces consistent signals
- [ ] Stop-loss/take-profit calculations reasonable

**Phase 3 (Risk & Settlement):**
- [ ] Position sizing respects 1% risk limit
- [ ] Circuit breakers trigger at correct thresholds
- [ ] Settlement tracker prevents trading with unsettled funds
- [ ] Portfolio heat calculated correctly
- [ ] Correlated positions rejected (both USO/UNG long)

**Phase 4 (Execution & Notifications):**
- [ ] ADVISORY sends Discord notifications
- [ ] PAPER_AUTO executes on paper account
- [ ] LIVE_CONFIRM waits for Discord approval
- [ ] LIVE_AUTO blocked by feature flag
- [ ] Kill switch closes all positions immediately
- [ ] Bracket orders placed correctly

**Phase 5 (Coordinator & Dashboard):**
- [ ] Trading loop runs every 1 minute
- [ ] All agent decisions logged to database
- [ ] Dashboard shows real-time positions
- [ ] Config adjustable without restart
- [ ] Health checks report agent status

**Phase 6 (AWS Deployment):**
- [ ] Lambda function executes trading loop
- [ ] RDS PostgreSQL accessible from Lambda
- [ ] ElastiCache Redis connected
- [ ] Streamlit dashboard running on EC2
- [ ] CloudWatch alarms configured
- [ ] Secrets Manager storing API keys

**Pre-Live Validation:**
- [ ] 4+ weeks successful paper trading (PAPER_AUTO mode)
- [ ] Backtest on 2-3 years of data (multiple market regimes)
- [ ] Sharpe ratio > 0.5
- [ ] Max drawdown < 15%
- [ ] Paper trading P&L matches backtest expectations
- [ ] All circuit breakers tested
- [ ] Kill switch tested
- [ ] Settlement tracking validated

---

## Resources

### Documentation
- `docs/PROJECT_REQUIREMENTS.md` - Complete production specification (1162 lines)
- `docs/COST_TRACKING.md` - Cost analysis and service tracking
- `docs/TRADING_SYSTEM_PLAN.md` - Trading system architecture
- `docs/DEV_WORKFLOW.md` - Claude + Gemini workflow
- `docs/BOOTSTRAP_PROMPT.md` - Initial setup instructions

### Configuration
- `CLAUDE.md` - Development constitution
- `GEMINI.md` - Gemini job description
- `.env.example` - Environment variables template
- `.claude/settings.json` - Hook configuration
- `pyproject.toml` - Python package configuration

### Scripts
- `scripts/gemini_context_pack.ps1` - Refresh context pack
- `scripts/gemini_ask.ps1` - Ask Gemini a question
- `scripts/quality_gate.ps1` - Run ruff + pytest

### Commands & Skills
- `.claude/commands/ctx-refresh.md` - Refresh context pack
- `.claude/commands/ctx-ask.md` - Ask Gemini
- `.claude/commands/checkpoint.md` - End-of-chunk validation
- `.claude/skills/context-pack/` - Context management skill
- `.claude/skills/quality-gates/` - Quality gates skill
- `.claude/skills/checkpoint/` - Checkpoint skill

---

## Implementation Plan (Next Steps)

### Immediate (Phase 1 Tasks)

1. **Update pyproject.toml** with production dependencies
   - Add: websockets, aiohttp, asyncpg, sqlalchemy, alembic, redis
   - Add: streamlit, plotly, discord.py
   - Add: boto3, aioboto3

2. **Create src/core/config.py**
   - TradingConfig with all parameters
   - DatabaseConfig for PostgreSQL/Redis
   - AlpacaConfig for API credentials
   - AutomationMode enum

3. **Create src/core/database.py**
   - SQLAlchemy async engine setup
   - Session management
   - Connection pooling

4. **Create Alembic migration**
   - Initialize Alembic
   - Create initial schema (10+ tables)
   - Add monthly partitioning for bars_1m

5. **Create src/agents/market_data.py**
   - Alpaca WebSocket client
   - 1-minute bar ingestion
   - Multi-timeframe aggregation logic

6. **Create src/services/redis_cache.py**
   - Redis client wrapper
   - TTL management
   - Cache invalidation

### Medium-Term (Phases 2-3)

7. Strategy Selector Agent
8. Strategy Pool (trend-following, mean-reversion)
9. Risk Manager Agent
10. Settlement Tracker Agent

### Long-Term (Phases 4-6)

11. Execution Agent + Discord bot
12. Coordinator + Streamlit dashboard
13. AWS deployment (Terraform + Lambda)
14. 4+ weeks paper trading validation
15. Go-live with LIVE_CONFIRM mode

---

## Known Issues / Blockers

**None currently.** Documentation phase complete, ready to start Phase 1 implementation.

---

## Open Questions

1. **Local Development Environment:**
   - Should we use Docker Compose for PostgreSQL + Redis locally?
   - **Decision:** Yes, mirrors AWS setup, easier than local installs
   - **Action:** Create docker-compose.yml in Phase 1

2. **Alpaca Account:**
   - Paper account or live account for initial development?
   - **Decision:** Paper account first, at least 4 weeks validation before live
   - **Action:** Sign up for Alpaca paper account

3. **Discord Bot vs Webhook:**
   - Interactive bot (discord.py) or simple webhook?
   - **Decision:** Both - webhook for ADVISORY, bot for LIVE_CONFIRM
   - **Action:** Implement webhook first (Phase 1), bot in Phase 4

4. **Time Zone Handling:**
   - Store timestamps as UTC or ET?
   - **Decision:** UTC in database, convert to ET for display
   - **Rationale:** Standard practice, avoids DST issues

---

**END OF RUNBOOK**

*Next update: After Phase 1 completion (Core Infrastructure)*
