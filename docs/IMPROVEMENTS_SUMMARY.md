# Human-AI System Improvements Summary

**Last updated: 2026-05-15**

This document tracks major improvements made to the Human-AI swarm system across trading agents, infrastructure, and supporting systems.

---

## Session 2026-05-15 — Additional improvements

### GSD
- Updated GSD to **v1.42.2** (from v1.41.2)

### Firebase
- **Log backup service**: Runs every 30 minutes, persists to 7 Firestore collections (logs, daily_summaries, market_intel, supabase_mirror, system_snapshots, system_state, trading_state)
- **Supabase mirror**: All 9 Supabase tables replicated into Firebase (supabase_mirror collection)
- **EA Firebase sync removed**: EA agent no longer writes directly to Firebase; standalone backup service handles all persistence instead

### Video Pipeline
- **christian/trading folder split**: Videos now routed to separate GDrive destinations — `gdrive:HumanAI/videos/trading/all/` (TikTok + YouTube combined) and `gdrive:HumanAI/videos/christian/`
- **Mode toggle**: Video mode controlled via `data/config/video_mode.json` — set `"mode": "christian"` (default) or `"mode": "trading"`
- **Single trading/all/ destination**: TikTok and YouTube Shorts output merged into one folder (no more separate platform subdirs)
- **Video scheduler**: 4 videos/day, christian mode is the default; OpenClaw agent can toggle via config

### LLM Routing
- **All agents → NVIDIA direct**: Every agent now uses NVIDIA NIM API directly (model: nvidia/llama-3.3-nemotron-super-49b-v1)
- **OpenRouter removed**: No longer a dependency for any agent; llm_routing.json updated accordingly

---

## EA Trading Agent

### v10 — H1 Bias Filter + Multi-Symbol Expansion
- **H1 EMA bias filter**: Long signals only above H1 EMA, shorts only below — reduces counter-trend noise
- **Breakout score boost**: +2 added to breakout confirmation (score≥6 required for breakout entries)
- **New symbols**: EURUSD and GBPUSD added alongside XAUUSD/XAGUSD
- **LONDON_NY trail tightened**: Trailing stop reduced from 15 pips to 10 pips during London/NY overlap
- **NY_CLOSE TREND unblocked**: TREND regime now trades during NY close window (previously blocked)

### v10.1 — REVERSE Oscillation Fix + Range Noise Filter
- **REVERSE mode disabled in RANGE/NY_CLOSE**: Prevents false counter-trend entries in choppy conditions
- **REVERSE threshold raised**: Min reversal strength increased from 3 to 5 (reduces false positives)
- **3-cycle cooldown**: REVERSE mode has 3-bar cooldown after exit to prevent re-entry oscillation
- **RANGE + NEUTRAL noise filter**: Requires score≥4 before entering any trade in RANGE or NEUTRAL regimes

### GoldBasket_v4.1 — London Open Window
- **Window_7to9am added**: New trading window from 07:00–09:00 UTC capturing London open volatility

---

## Binance Trading Agent

### v9 — ATR-Based Risk Engine
- **ATR dynamic SL/TP**: Stop-loss and take-profit derived from live ATR (volatility-scaled, not fixed pips)
- **Volume momentum filter**: Trades blocked when volume is below 20-period moving average
- **Zero-ATR guard**: Protects against divide-by-zero when ATR collapses (flash crash protection)
- **Daily -$300 circuit breaker**: Agent pauses for 1 hour after daily loss exceeds $300
- **Daily P&L reset**: P&L tracking resets at 00:00 UTC daily

### v9.1 — Early Exit + Partial TP + Streak Protection
- **Early timeout exit**: Position closed at -0.3% when ≤30 seconds remain before max-hold timeout
- **Partial TP at 1×ATR**: 50% of position closed at first ATR target, stop-loss moved to breakeven
- **Leverage halved on -3 streak**: If agent loses 3 consecutive trades, leverage halved for next 3 trades
- **Daily stats on every log line**: P&L, WR%, streak appended to every tick-level log entry

---

## Market Intelligence System

- **Fear/Greed Index**: Real-time data from alternative.me API
- **BTC Dominance**: Pulled from CoinGecko public API
- **Alpaca H1 Trend**: 20-bar EMA trend from Alpaca market data feed
- **Binance 4H Macro**: 4H OHLCV + RSI from Binance public endpoint
- **Crypto News Sentiment**: Scored via CryptoCompare news API
- **Composite bias**: Aggregated BEAR / BULL / NEUTRAL signal fed into Binance signal scorer (±0.3 max score impact)
- **Log tag**: `mi:B/N/b` marker on every Binance tick line for bias transparency

---

## Infrastructure

### Automode v5 Fixes
- **GSD `--project-dir` → `--add-dir` flag fix**: Corrected broken GSD CLI invocation
- **PAI `is_pai_installed()` fix**: Fixed 555 silent task failures caused by incorrect install-check logic

### LLM Routing
- **All agents → NVIDIA NIM direct**: Removed OpenRouter dependency for all agents; now using direct NVIDIA API endpoints via `llm_routing.json`

### Firebase
- **Service account key configured**: Firebase Admin SDK credentials set up correctly
- **Project ID corrected**: Fixed from placeholder to `human-ai-6fed9`

### Log Consolidation
- **Unified logger**: `core/utils/log_consolidator.py` — single entry point for all agent logging
- **Log rotation**: 10MB max per file, 5 backup files
- **`show_logs.py` CLI**: Filter by agent, level, or date from command line
- **5 dead log files renamed `.dead`**: Identified and tombstoned inactive log references

### Codebase Cleanup
- **95 deadwood/stub files deleted**: Removed from `core/`, `agents/social/`, `scripts/` — no active references

### Dashboard (Mission Control)
- **Daily P&L tile**: Shows cumulative P&L for current UTC day
- **Video gen tile**: Displays recent video generation status
- **Live log streaming**: WebSocket-based live log tail in browser
- **Agent chips**: Color-coded agent status indicators
- **Chart.js 7-day chart**: Rolling 7-day P&L sparkline

### Video Pipeline
- **Folder structure**: Separate `trading/` and `christian/` content folders
- **77 videos renamed**: Consistent naming convention applied across existing library
- **MoviePy v2 fixes**: Updated deprecated API calls (VideoFileClip, concatenate_videoclips)
- **GDrive upload**: Automatic upload via rclone after render completes

### Knowledge Graph
- **Graphify rebuilt**: 9,589 nodes, 20,657 edges — fully regenerated from current codebase

---

## Prior Infrastructure Improvements (from earlier sessions)

### Agent System
- Completed `run_retrieval_loop()` in `agents/ai_agents.py` — was initialized but never executed
- Centralized YAML configuration via `configs/agent_config.yaml` + `core/utils/config_loader.py`
- Replaced scattered `print()` calls with structured logging throughout

### Health Monitoring
- **Unified Health Monitor**: `core/health/monitor.py` — CPU, memory, disk, services, logs, configs
- **Enhanced Swarm Health Check**: `core/utils/swarm_health_check.py` with JSON output support
- **Health tests**: `tests/health/test_unified_monitor.py`

---

## Files Modified/Added (2026-05-15 session)

### Trading Agents
- `agents/trading-agent/live_trading_ea.py` — EA v10.1
- `agents/trading-agent/live_trading_binance.py` — Binance v9.1
- `agents/trading-agent/market_intelligence.py` — live market intel system

### Infrastructure
- `core/orchestration/automode.py` — GSD/PAI fix, NVIDIA routing
- `core/utils/log_consolidator.py` — unified logger
- `scripts/show_logs.py` — log viewer CLI
- `apps/dashboard/monitoring_dashboard.py` — dashboard enhancements
- `scripts/produce_video.py` — MoviePy v2 + GDrive upload
- `llm_routing.json` — NVIDIA NIM direct endpoints
- `infrastructure/tools/graphify/` — knowledge graph rebuild

---

*Improvements through: 2026-05-15*
