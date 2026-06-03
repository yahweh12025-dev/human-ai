# Human-AI Swarm Roadmap

**Last updated: 2026-05-15** | Phase 4 Active

> Operational detail roadmap. See `docs/ROADMAP.md` for the canonical full version.

## Phase 3: Live Trading — COMPLETE

### EA Trader (MetalEA / XAUUSD + XAGUSD)
- [x] MetalEA compiled and installed in MT5 Experts folder
- [x] `python3 liveea.py` — automated: attaches to chart, enables AutoTrading, starts trading
- [x] `python3 stopea.py` — stops EA + closes all MT5 positions
- [x] EA v9 — internal signals only (Telegram integration removed in v9)
- [x] 0.01 base lots, 0.02 at PEAK hours (14-18 UTC) on XAUUSD
- [x] XAGUSD always 0.01 (capped by MAX_LOT)
- [x] Prop firm safe: 3% daily limit, 5% max drawdown, 0.05L hard cap
- [x] Weekend + daily break detection (21:55-22:05 UTC)
- [x] AutoTrading: checks log before clicking (never toggles OFF accidentally)

### Binance Scalper (BTC/ETH/BNB)
- [x] v7 — dynamic leverage (max 75x), proper equity sizing
- [x] $5 BTC / $3 ETH / $1.50-$2.00 alts per trade
- [x] TP1: 0.30% (close 50%) → SL to breakeven → TP2: 0.60%
- [x] 60s max hold — pure micro-scalp; 10s ticks
- [x] MIN_STRENGTH: 0.55, MAX_OPEN: 4
- [x] `startbinance.py` / `stopbinance.py` root launchers

### Automode & Social
- [x] v5 — infinite pending loop fixed; task_queue.failed for permanently-failed tasks
- [x] Trading loop: hermes_trade → improvement_suggestions.json → opencode_trade
- [x] pidev_monitor: auto-restarts trading agents if dead
- [x] Video pipeline: 88+ videos produced via `scripts/produce_video.py`
- [x] Social, PAI, GSD agents integrated

### Infrastructure
- [x] 6 root directories (agents, core, data, docs, infrastructure, scripts)
- [x] Self-hosted Supabase (Docker) with agent_backups + agent_logs tables
- [x] GitHub clean; .nojekyll; .claudeignore for 80%+ context savings
- [x] Obsidian vault at `data/obsidian/`, synced to GDrive via rclone
- [x] Dify RAG + Graphify knowledge graph bridge
- [x] Mission Control dashboard (port 10000)

---

## Phase 4: Optimisation — ACTIVE

### High Priority
- [ ] EA: review $5k account trades — tune MIN_SCORE per session regime
- [ ] Binance: verify $5/$3/$2 equity × dynamic leverage on demo-fapi
- [ ] Social media agent: wire Pollinations.ai posting schedule end-to-end
- [ ] Supabase: create agent_backups table in cloud project
- [ ] Firebase: enable Firestore public write rules

### Medium Priority
- [ ] EA: backtest peak-hours strategy on historical XAUUSD data
- [ ] FreqTrade V9: multi-timeframe confirmation (HTF trend filter)
- [ ] Dashboard: show Binance agent trades and P&L
- [ ] Dify & Graphify synergy: LangChain pipelines
- [ ] n8n-mcp integration for deterministic workflows

---

## Script Reference

| Command | Action |
|---------|--------|
| `python3 liveea.py` | Start EA Trader v9 (XAUUSD/XAGUSD) |
| `python3 stopea.py` | Stop EA + close all positions |
| `python3 startbinance.py` | Start Binance Scalper v7 |
| `python3 stopbinance.py` | Stop Binance scalper |
| `python3 automode.py` | Run autonomous swarm (all agents) |
| `python3 core/apps/dashboard/mission_control.py` | Dashboard (port 10000) |
| `python3 scripts/produce_video.py --topic "..." --platform tiktok` | Produce video |
| `python3 scripts/sync/full_sync.py` | Sync Obsidian to GDrive |
| `bash scripts/compile_ea.sh` | Recompile MetalEA MQ5 |
