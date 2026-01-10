# Agentic-Comodotity-Trading-System
A multi-agentic trading system for commodities such as Oil and Natural Gas

**Status:** ✅ PRODUCTION-READY | Ready for AWS Deployment in PAPER_AUTO Mode

A **production-grade, progressively autonomous multi-agent trading system** for crude oil (USO) and natural gas (UNG) ETF trading, supporting both intraday and swing trading strategies with intelligent selection based on market conditions.

## 🚀 Quick Links

- **Deployment Guide:** [infrastructure/terraform/DEPLOYMENT_GUIDE.md](infrastructure/terraform/DEPLOYMENT_GUIDE.md)
- **Deployment Checklist:** [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- **Session Summary:** [SESSION_SUMMARY.md](SESSION_SUMMARY.md)
- **Verification Scripts:** [scripts/](scripts/)
  - Alpaca Auth: `uv run python scripts/verify_alpaca_auth.py`
  - Notifications: `uv run python scripts/verify_notifications.py`
  - API Endpoints: `uv run python scripts/verify_api_endpoints.py`

**Core Philosophy:**
- **Progressive automation:** ADVISORY → PAPER_AUTO → LIVE_CONFIRM → LIVE_AUTO
- **Safety-first:** 7-layer safety architecture with kill switch and circuit breakers
- **High precision:** 1-minute bar data frequency for accurate signal generation
- **Cash account compliance:** T+1 settlement tracking for Pattern Day Trader (PDT) workaround
- **Intelligent orchestration:** Market regime detection with dynamic strategy selection
- **Comprehensive risk management:** Configurable risk parameters, portfolio heat tracking
- **Audit trail:** Every decision logged with full reasoning
- **Cloud-native:** AWS deployment with RDS, ElastiCache, Lambda