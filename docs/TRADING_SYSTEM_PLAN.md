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

The system will be designed as a **multi-agent architecture** — breaking down the trading process into multiple specialized components (agents) that work together, rather than one monolithic program.

Each agent is responsible for a specific task, and they communicate or feed into a central decision process. By integrating diverse perspectives from different agents, overall decision quality and robustness can improve.

### Proposed Agents

#### 1. Data Acquisition & Preprocessing Agent

Handles all data fetching and processing:
- Pull market data (price quotes, historical OHLCV, live ticks)
- Compute technical indicators (moving averages, RSI, ATR, etc.)
- Clean and format data for other agents

**Tools:** yfinance for historical data, broker API/websocket for live data, TA-Lib or pandas-ta for indicators

#### 2. Technical Analysis Agent

Core strategy intelligence focusing on price action:
- Determine short-term trend direction, momentum
- Identify support/resistance levels
- Detect overbought/oversold conditions
- Generate technical bias/signals with recommended stop-loss and take-profit levels

**Output example:** "Crude oil showing bullish momentum on 1-hour chart; consider long" or "Nat gas swing trade short signal triggered"

#### 3. Fundamental/Sentiment Agent

Watches for news and fundamental data:
- EIA Weekly Petroleum Status Report (crude inventories) — Wednesdays
- Natural Gas Storage reports — Thursdays
- OPEC+ announcements
- Weather forecasts (nat gas demand)
- Geopolitical developments

May use NLP for sentiment analysis of news headlines.

**Output example:** "Neutral technicals, but extremely bullish news: hurricane affecting Gulf oil output"

#### 4. Strategy-Specific Agents (Optional)

Separate agents for different methodologies:
- **Breakout Agent** — looking for volatility breakouts
- **Mean Reversion Agent** — looking for range-bound reversal opportunities

Multiple strategy agents whose outputs are considered by the decision layer can improve robustness.

#### 5. Risk Management & Position Sizing Agent

Evaluates trades before execution:
- Calculate position size given account capital and risk threshold (1-2% max per trade)
- Use stop-loss level to compute appropriate size
- Adjust or veto trades based on overall exposure
- Set stop-loss and take-profit aligned with volatility (ATR)
- Reject trades that don't meet risk/reward criteria

**Critical:** Even if analysis agents are optimistic, the risk agent is the sober check.

#### 6. Execution Agent

Handles actual order placement and trade management:
- Connect to brokerage API
- Place orders (market, limit, stop)
- Monitor trades after entry
- Handle trailing stops, profit targets
- Manage order errors (rejected, partial fills)

**Tools:** ib_insync (Interactive Brokers), Alpaca SDK, etc.

#### 7. Coordinator & Decision Logic

The "brain" that assembles inputs and makes final decisions:
- Trigger Data Agent to update information
- Invoke Market Analysis agents
- Aggregate/synthesize signals (weighted voting, consensus)
- Resolve conflicts between agents
- Pass approved trades to Risk Management
- Hand off to Execution

**Conflict resolution example:** "Go long if at least 2 out of 3 strategy signals agree and none veto; go short if 2 out of 3 are short; if mixed, no trade."

### Communication & Flow

Agents share data through in-code data structures or common state. The system runs on a single machine in a scheduled loop (can use threads/async for parallel data fetching).

**Key principle:** Maintain clear structure where each agent's output can be logged and reviewed. An audit log recording each agent's decision helps with debugging and trust.

---

## Modeling Techniques for Prediction

### Time-Series Price Prediction: LSTM Networks

Deep learning models, particularly **LSTM (Long Short-Term Memory)** networks, are highly effective for financial time series forecasting:
- Achieve higher forecasting accuracy than ARIMA or other ML methods for crude oil
- Capture sequential dependencies, long-term trends, and short-term fluctuations
- Handle highly nonlinear and seasonal nature of gas prices
- Internal memory gates capture both short-term spikes and longer-term seasonal trends

**Usage:** Train LSTM to predict next day's price change (swing) or next hour's movement (intraday).

### Other Models

- **Tree-based ensembles (Random Forest, XGBoost, LightGBM):** Fast to train, interpretable feature importance, can be combined with LSTM in hybrid approach
- **CNN or CNN-LSTM hybrid:** Treat time series like temporal image, can capture local patterns
- **Reinforcement Learning:** Agent learns policy to maximize trading rewards — longer-term exploration, requires lots of training data
- **Statistical models (ARIMA, exponential smoothing):** Baseline or sanity check

### Model Usage by Agent

- **Technical Agent:** Predictive ML model (LSTM/ensemble) + indicator-threshold rules
- **Fundamental Agent:** NLP classification for news sentiment (fine-tuned BERT or simpler keyword rules)
- **Risk Agent:** GARCH for volatility, or simpler ATR-based approach

### Ensemble Decision-Making

The multi-agent design is itself a form of model ensemble. The coordination algorithm (majority vote, weighted average) becomes the meta-model. Can be tuned through testing.

---

## Technology Stack

### Core

- **Language:** Python 3.11+
- **Data manipulation:** NumPy, Pandas
- **ML:** scikit-learn, TensorFlow/Keras or PyTorch
- **Technical indicators:** TA-Lib or pandas-ta

### Data Sources

- **Historical:** Yahoo Finance API (yfinance)
- **Live:** Broker API (Alpaca for ETFs, Interactive Brokers for futures)
- **News/Fundamentals:** FinancialModelingPrep, Alpha Vantage, NewsAPI, EIA API

### Backtesting

- **Framework:** Backtrader or custom Pandas-based
- **Approach:** Walk-forward analysis, test across different market conditions

### Database

- **SQLite or PostgreSQL** for logging trades, signals, model predictions

### Execution

- **Broker SDKs:** Alpaca Python SDK (ETFs), ib_insync (Interactive Brokers)
- **Scheduling:** Python schedule library, asyncio for event-driven

### Monitoring

- **Logging:** Python logging module
- **Notifications:** Discord webhook (MVP), Telegram bot, email
- **Visualization:** Matplotlib, Plotly, optionally Dash/Streamlit dashboard

### Development

- **Research:** Jupyter notebooks
- **Version control:** Git
- **Testing:** pytest, ruff for linting

---

## Development Phases

### A) Foundation (Workflow + Scaffolding)
1. Create repo skeleton
2. Add Python env + lint/test tools
3. Validate workflow end-to-end

### B) Product Skeleton (No Live Trading)
4. Build minimal CLI + config system
5. Add data layer abstraction (pluggable providers)
6. Add dashboard skeleton (local UI) OR start CLI-first

### C) Operational Data + Logging
7. Implement market data ingestion (MVP provider)
8. Add persistence (SQLite) for candles/signals/logs
9. Add observability: structured logs + runbook

### D) Advisory Engine (No Auto-Exec)
10. Implement analysis pipeline interfaces
11. Add alerting (Discord webhook) + dedupe/cooldowns
12. Add paper/shadow mode runner

### E) Broker Integration (Read-Only First)
13. Implement Schwab/IBKR account read (positions/cash)
14. Add trade-intent objects (proposed orders only)
15. Add explicit manual confirmation UI/CLI step

### F) Paper Trading & Evaluation
16. Paper execution + journaling
17. Backtesting harness + replay mode
18. Regression tests for data correctness

### G) Go-Live Hardening (Still Guarded)
19. Circuit breakers (max loss/day, stale data halt, volatility halt)
20. Kill switch
21. Start real-money with manual confirmation only

### H) Optional Automation (Only If Chosen)
22. Feature flag for auto-exec
23. Extra safety: two-step confirmations, restricted order types, whitelists

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

### Compliance
- PDT rule awareness if day trading ETFs ($25k threshold)
- Futures contract roll management

---

## Cost-Benefit Summary

| Choice | Benefits | Costs |
|--------|----------|-------|
| Intraday trading | No overnight risk, daily compounding potential | Time-intensive, higher transaction costs |
| Swing trading | Less screen time, larger per-trade profits | Overnight gap risk, wider stops needed |
| ETFs | Simple, no special account, easy sizing | Small fees, tracking error, limited hours |
| Futures | Direct exposure, 24-hour trading, no fund fees | Complex, high leverage, requires expertise |
| Multi-agent architecture | Robust, modular, diverse inputs | Development time, debugging complexity |
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