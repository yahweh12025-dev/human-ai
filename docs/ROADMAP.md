# Human-AI Swarm Roadmap

**Last updated: 2026-05-18** | EA v11 ACTIVE | Binance v11.1 ACTIVE | GSD v1.42.2

---

## Current System Status (May 2026)
- EA Trader v11: XAUUSD/XAGUSD/EURUSD/GBPUSD via MT5 file bridge — ACTIVE
- Binance Scalper v11.1: BTC/ETH/BNB/SOL/XRP/TRX/ADA demo futures — ACTIVE
- Content pipeline: 100+ videos produced, auto-publish to GDrive wired
- Obsidian vault: 2.9MB (cleaned from 48GB recursive mirror — May 2026)
- GDrive: all videos synced to gdrive:HumanAI/videos/
- Numerai: skeleton pipeline added (agents/numerai/) — needs API key to activate
- Telegram signals: deferred, will wire in next phase

## Roadmap vs. Completion

### Phase 1 — Infrastructure ✅ Complete
- VPS: Ubuntu 22.04 on cloud ✅
- Supabase (PostgreSQL) running ✅
- Firebase backup ✅
- GDrive via rclone ✅
- Obsidian vault ✅

### Phase 2 — Trading Execution ✅ Complete
- EA v11 (XAUUSD/XAGUSD/EURUSD/GBPUSD): ACTIVE ✅
- Binance v11.1 (7 pairs): ACTIVE ✅
- Risk rules: 3% daily / 5% max DD / 0.05L cap ✅

### Phase 3 — Numerai 🔄 In Progress
- Skeleton built at agents/numerai/ ✅
- Needs: Numerai account + API key

### Phase 4 — Olas Prediction Markets ⏳ Planned
### Phase 5 — Content Flywheel 🔄 In Progress
- 100+ videos produced ✅
- Auto-publish hook wired (trade_content_hook.py) ✅
- Postiz integration: active
### Phase 6 — Agent Orchestration ✅ Complete (Automode v7)
### Phase 7 — Analytics 🔄 In Progress (Mission Control at :10000)
### Phase 8 — AI Stack ✅ Complete (OpenRouter/Groq/NVIDIA NIM)
### Phase 9 — Security 🔄 Partial (rotate API keys — .env was in Obsidian vault)
### Phase 10 — Scaling ⏳ Planned

---

## Phase 1: Foundation & Stabilization — COMPLETE

- [x] Core Agent Architecture (Hermes, OpenClaw, OpenCode, Pi.dev)
- [x] Supabase Logging Integration
- [x] Basic Sandbox Execution
- [x] OpenClaw Gateway Connectivity

---

## Phase 2: The "SQUAD" & High-Fidelity Loops — COMPLETE

- [x] AntFarm Orchestrator (Retrieve → Research → Implement → Verify loop)
- [x] NativeWorker (server-less implementation engine)
- [x] Browser-First Mandate (all agents routed through browser for LLM access)
- [x] Researcher Evolution (YouTube transcript synthesis + hybrid routing)
- [x] Hardened Sandbox (custom Docker images)
- [x] Master Log System (global event aggregation)

---

## Phase 3: Live Trading & Orchestration — COMPLETE

### EA Trader v10.1 (XAUUSD / XAGUSD / EURUSD / GBPUSD)
- [x] MetalEA compiled and installed in MT5 Experts folder
- [x] `liveea.py` — fully automated: attaches to chart, enables AutoTrading
- [x] `stopea.py` — stops EA + closes all MT5 positions
- [x] v9 — internal signals only (Telegram integration removed)
- [x] 3-pillar signal (trend + RSI divergence + Bollinger structure)
- [x] Session-aware regimes: ASIAN (22-07 UTC), LONDON (07-12), NY (13-21)
- [x] RANGE regime: mean-reversion mode, min_score=4
- [x] Prop-firm safe: 3% daily limit, 5% max drawdown, 0.05L hard cap
- [x] v10: H1 EMA bias filter, breakout score boost, EURUSD/GBPUSD added
- [x] v10.1: REVERSE oscillation fix, RANGE+NEUTRAL noise filter (score≥4)
- [x] GoldBasket_v4.1: Window_7to9am (London open 07:00–09:00 UTC)

### Binance Scalper v9.1 (BTC/ETH/BNB/SOL/XRP/ADA/DOGE)
- [x] v7 — dynamic leverage (max 75x), proper equity sizing ($5/$3/$2)
- [x] 7 symbols simultaneously on 10s ticks (added SOL, XRP, ADA, DOGE)
- [x] TP1: 0.30% (close 50%) → SL to breakeven → TP2: 0.60%
- [x] 60s max hold — pure micro-scalp
- [x] MIN_STRENGTH: 0.55, MAX_OPEN: 4
- [x] `startbinance.py` / `stopbinance.py` root launchers
- [x] v9: ATR-based SL/TP, volume filter, zero-ATR guard, daily circuit breaker
- [x] v9.1: early timeout exit, partial TP at 1×ATR, leverage halved on -3 streak
- [x] Live market intelligence: Fear/Greed, BTC dominance, Alpaca H1, Binance 4H, news sentiment

### Automode
- [x] v5 — infinite pending loop fixed, failure tracking, task.failed queue
- [x] Per-agent task banks: hermes, opencode, pi.dev, openclaw, researcher
- [x] Trading loop agents: hermes_trade, opencode_trade, pidev_monitor
- [x] Social, PAI, GSD agents integrated
- [x] Peer-review: every completed task spawns a REVIEW task
- [x] Self-improvement loop: hermes_trade → improvement_suggestions.json → opencode_trade

### Social Media & Video Pipeline
- [x] Video generation pipeline via `scripts/produce_video.py`
- [x] 88+ videos produced (TikTok, YouTube Shorts, Instagram Reels)
- [x] FaithNexus + ITNexus channels
- [x] Pollinations.ai image generation verified
- [x] `config/social_cron.yaml` posting schedule configured

### Infrastructure
- [x] 6 root directories (agents, core, data, docs, infrastructure, scripts)
- [x] Self-hosted Supabase (Docker) — agent_backups + agent_logs tables
- [x] Obsidian vault synced to `data/obsidian/` and GDrive via rclone
- [x] Dify RAG + Graphify knowledge graph bridge
- [x] Mission Control dashboard (port 10000)
- [x] GitHub clean; .nojekyll; .claudeignore reducing context 80%+
- [x] GSD + PAI agent integrations

---

## Phase 4: Optimisation — ACTIVE (2026-05-15)

### Completed in Phase 4 (2026-05-15)
- [x] EA v10: H1 bias filter, breakout boost, EURUSD/GBPUSD added
- [x] EA v10.1: REVERSE oscillation fix, RANGE noise filter
- [x] Binance v9: ATR-based SL/TP, volume filter, circuit breaker
- [x] Binance v9.1: partial TP, early exit, streak protection
- [x] Binance: SOL/XRP/ADA/DOGE added (7 symbols total)
- [x] Live market intelligence system (Fear/Greed + CoinGecko + Alpaca + Binance 4H + news)
- [x] NVIDIA NIM direct routing — all agents (OpenRouter removed)
- [x] Firebase log backup service: 30-min interval, 7 collections
- [x] Firebase: Supabase mirror (all 9 tables)
- [x] Log consolidation (unified logger + show_logs.py CLI)
- [x] Dashboard: daily P&L, video tile, live streaming, agent chips, 7-day chart
- [x] Video pipeline: MoviePy v2, GDrive upload, christian/trading folder split
- [x] Video scheduler: 4 videos/day, christian mode default, toggle via data/config/video_mode.json
- [x] Graphify rebuilt: 9,589 nodes, 20,657 edges
- [x] 95 deadwood files deleted
- [x] automode v5: GSD --project-dir → --add-dir fixed; PAI is_pai_installed() fixed (555 silent failures)
- [x] GSD updated to v1.42.2

### High Priority (Remaining)
- [ ] EA: backtest v10.1 on historical XAUUSD data — validate H1 filter impact
- [ ] Binance: live performance review after v9.1 runs 48h on demo-fapi
- [ ] Social: wire Postiz publishing schedule end-to-end (cron → Postiz)
- [ ] Supabase: create agent_backups table in cloud Supabase project (not just self-hosted)

### Medium Priority
- [ ] FreqTrade V9: multi-timeframe confirmation (HTF trend filter)
- [ ] Dify & Graphify synergy: LangChain pipelines routing data between RAG and knowledge graph
- [ ] n8n-mcp Integration: deterministic workflows for repetitive tasks

### Lower Priority
- [ ] Security Audit: complete full repository secret scrub + verify token rotation
- [ ] Swarm Development Tracking: activity logging and progress tracking dashboard
- [ ] FinceptTerminal Integration: evaluate as financial data agent

---

## Phase 5: Scale & Intelligence — PLANNED

### Agent Intelligence
- [ ] Hermes autonomous strategy generation: EA symbols + regime matrix → auto-proposed changes
- [ ] OpenCode self-patching: reads improvement_suggestions.json, applies, verifies, rolls back on regression
- [ ] Memory consolidation: LangChain + Dify pipeline for long-term agent learning

### Trading Scale
- [ ] EA live account: migrate from ICMarkets demo to funded prop account after 30-day demo validation
- [ ] Binance: expand to 10+ symbols with per-symbol ATR calibration
- [ ] FreqTrade V9 strategy live: multi-timeframe confirmation on paper account

### Infrastructure Scale
- [ ] Kubernetes deployment: move from nohup/Docker to K8s orchestration
- [ ] Multi-region failover: secondary cloud instance for EA redundancy
- [ ] Automated rebalancing: dynamic equity allocation between EA and Binance based on Sharpe ratio

### Content & Social
- [ ] Postiz full automation: cron → generate → review → publish without human touch
- [ ] 500 video milestone: trading/all + christian combined
- [ ] YouTube channel analytics integration: views/subs feedback loop to content generation

---

## Script Reference

| Command | Action |
|---------|--------|
| `python3 liveea.py` | Start EA Trader v10.1 (XAUUSD/XAGUSD/EURUSD/GBPUSD) |
| `python3 stopea.py` | Stop EA + close all MT5 positions |
| `python3 startbinance.py` | Start Binance Scalper v9.1 (7 symbols) |
| `python3 stopbinance.py` | Stop Binance Scalper |
| `python3 automode.py` | Run autonomous swarm |
| `python3 core/apps/dashboard/mission_control.py` | Mission Control (port 10000) |
| `python3 scripts/produce_video.py --topic "..." --platform tiktok` | Produce video |
| `python3 scripts/sync/full_sync.py` | Sync Obsidian to GDrive |
| `python3 core/integrations/verify_all_integrations.py` | Verify all integrations |
