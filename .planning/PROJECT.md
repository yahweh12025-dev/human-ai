# Human-AI Swarm — Trading Engine Improvements

## What This Is

Autonomous multi-agent swarm for high-alpha crypto (Binance Futures) and forex (MT5 EA) trading. Currently running EA Trader v10.1 ($4,431) and Binance Scalper v11.1 ($4,497) as part of a 7-agent orchestration system (OpenClaw, Hermes, OpenCode, Pi.dev, Social, PAI, Researcher). The goal is to harden the trading engines for prop-firm compliance and improve strategy performance through institutional-grade risk management and market-aware signal generation.

## Core Value

Trading engines must survive before they can thrive — risk infrastructure comes first, then strategy optimization. Both engines must operate within prop-firm drawdown limits without manual intervention.

## Requirements

### Validated

- ✓ EA Trader v10.1 — running, session-aware (ASIAN/LONDON/LONDON_NY/NY_CLOSE/AFTER_NY), regime detection (TREND/SCALP/RANGE/DEAD), ATR-adaptive parameters, prop-firm guardrails (3% daily / 5% max drawdown / 0.05L hard cap)
- ✓ Binance Scalper v11.1 — running, demo futures, 8-coin portfolio (BTC/ETH/BNB/SOL/XRP/TRX/ADA), ATR-adaptive SL/TP, 130s optimal hold time, data-driven equity allocation
- ✓ Multi-agent orchestration with OpenClaw manager, automode v7
- ✓ GDrive backup/sync infrastructure
- ✓ Market research: Binance scalping best practices, MT5 EA optimization, prop-firm risk management

### Active

- [ ] **RISK-01**: Circuit breaker at 15-20% total account drawdown — pause all trading, resume only after manual review
- [ ] **RISK-02**: Real-time equity-based drawdown monitoring (not just balance) — firms use equity
- [ ] **RISK-03**: Self-imposed daily loss limit at 60% of prop firm's max — prevents hitting firm's hard limit
- [ ] **RISK-04**: Consecutive loss detection — 2 losses in a row → stop for the day (prevents revenge trading)
- [ ] **RISK-05**: Correlation-aware position sizing — max 2-3% aggregate risk across all correlated pairs
- [ ] **BINANCE-01**: Funding rate integration — avoid longs when funding > +0.1%, check before each entry
- [ ] **BINANCE-02**: Multi-TF bias gating — 4H/Daily structure filters 15m signals (only trade in trend direction)
- [ ] **BINANCE-03**: Regime detection enhancement — BB width / ATR ratio to detect and pause during low-vol regimes
- [ ] **BINANCE-04**: Post-only limit order execution — switch from taker to maker for fee rebates (saves 0.10%)
- [ ] **BINANCE-05**: CVD + Order Book Imbalance + VWAP bands as additional signal filters
- [ ] **EA-01**: Walk-forward optimization with out-of-sample validation — stop overfitting to past data
- [ ] **EA-02**: Smart Money Concepts — liquidity sweeps, Order Blocks, FVGs on MT5
- [ ] **EA-03**: ATR-based adaptive SL (1.5x ATR) and TP (3x ATR) — current is ATR-adaptive but needs validation
- [ ] **EA-04**: Session filter — skip Asian session, trade London/NY only
- [ ] **EA-05**: News filter — block trading 30min before NFP/CPI/FOMC (spread widening protection)
- [ ] **MONITOR-01**: Real-time dashboard (Grafana) for P&L, drawdown, open positions
- [ ] **MONITOR-02**: Telegram alerts for circuit breaker triggers, daily loss limits, funding rate warnings

### Out of Scope

- New trading instruments/coins outside current portfolio — focus on improving existing pairs first
- Full MT5 strategy rewrite — improve v10.1 incrementally, not from scratch
- Social media/content features — covered by existing Social agent, unrelated to trading improvements

## Context

Brownfield project with two production trading engines. Binance Scalper has been running on demo futures with data-proven optimal hold times (130s). EA Trader has live results ($4,431). Both engines have basic risk guardrails but lack institutional-grade circuit breakers, equity tracking, and correlation-aware sizing. The user has done domain research on 5 pillars (0.5% rule, daily loss discipline, buffer building, trade limits, 2-loss rule) and wants these codified into the engines. GSD agents are not installed — roadmap will be generated inline.

## Constraints

- **Prop-firm compliance**: Risk systems must match or exceed funded account requirements (equity-based drawdown, daily loss limits)
- **Incremental changes**: Both engines are running and profitable — changes must not break existing functionality
- **Demo-first validation**: All Binance improvements deploy to demo futures first; EA changes validate in MT5 strategy tester
- **No GSD agents**: Roadmap and plans generated inline without subagent support
- **Runtime**: opencode v1.15.12

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Risk before strategy (Phase 1 before Phase 2) | Most retail bots blow up from risk, not strategy | ✓ Approved |
| Self-imposed limits tighter than firm's | Hit your own limit first, not the firm's hard limit | ✓ Approved |
| 2-phase roadmap: Risk infra → Strategy perf | Clean separation; Phase 1 output feeds Phase 2 input | ✓ Approved |

---
*Last updated: 2026-05-28 after initialization*
