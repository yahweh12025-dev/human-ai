# Human-AI Project: Autonomous Multi-Agent Swarm

[![GitHub](https://img.shields.io/badge/GitHub-Source-blue)](https://github.com/yahweh12025-dev/human-ai)
[![EA Trader](https://img.shields.io/badge/EA%20Trader%20v10.1-LIVE-green)](agents/trading-agent/live_trading_ea.py)
[![Binance Scalper](https://img.shields.io/badge/Binance%20v9.1-LIVE-green)](agents/trading-agent/live_trading_binance.py)
[![Automode](https://img.shields.io/badge/Automode%20v5-ACTIVE-blue)](automode.py)

**Last updated: 2026-05-15** | Phase 4 Active — GSD v1.42.2, EA v10.1 ($4,430.86), Binance v9.1 ($4,502.09), 88+ videos produced

The **Human-AI Project** is a self-evolving, autonomous multi-agent swarm for high-alpha trading,
deep-web research, and automated social media content. Two live trading agents run continuously with
verified real trade records. The swarm self-tasks, peer-reviews, and generates improvements without
human prompting.

---

## Quick Start (Fresh Linux Instance)

```bash
# Clone and bootstrap
git clone https://github.com/yahweh12025-dev/human-ai.git
cd human-ai
bash scripts/install.sh

# Then:
# 1. Edit API keys:  nano .env
# 2. Setup GDrive:   rclone config  (name remote 'gdrive')
# 3. Start EA:       python3 liveea.py
# 4. Start Binance:  python3 startbinance.py
# 5. Dashboard:      python3 core/apps/dashboard/mission_control.py
```

---

## Live Status (2026-05-15)

| Component | Version | Status | Notes |
|-----------|---------|--------|-------|
| EA Trader (XAUUSD/XAGUSD/EURUSD/GBPUSD) | v10.1 | **LIVE** | Balance $4,430.86 | trades=757 | streak=+5 |
| Binance Scalper (BTC/ETH/BNB/SOL/XRP/ADA/DOGE) | v9.1 | **LIVE** | Balance $4,502.09 | trades=5,533 | P&L +$16.93 today |
| Automode | v5 | **ACTIVE** | Self-tasking, peer-review, monitors both agents |
| Mission Control Dashboard | — | **Running** | http://localhost:10000 |
| Video Scheduler | — | **Active** | 4 videos/day, christian mode default |
| Firebase Backup | — | **Running** | 30-min interval, 7 collections |
| MCP Server | — | **Running** | port 8765 |
| Supabase (self-hosted) | — | **Connected** | localhost:3000, 9 tables |
| Obsidian Vault | — | **Synced** | `data/obsidian/` → gdrive:HumanAI/obsidian/ |
| GSD | v1.42.2 | **Active** | Phase automation |

---

## System Architecture

### Dual-Brain Trading Engine

```
MT5 (XAUUSD/XAGUSD/EURUSD/GBPUSD)     Binance Demo Futures (7 symbols)
     |                                           |
liveea.py                               startbinance.py
     |                                           |
agents/trading-agent/live_trading_ea.py   agents/trading-agent/live_trading_binance.py
  EA Trader v10.1                          Binance Scalper v9.1
  - 4 symbols: XAU/XAG/EUR/GBP             - 7 symbols: BTC/ETH/BNB/SOL/XRP/ADA/DOGE
  - H1 EMA bias filter (v10)               - 10s ticks, 60s max hold
  - Breakout score boost (v10)             - ATR-based SL/TP (v9)
  - REVERSE oscillation fix (v10.1)       - Volume filter + circuit breaker (v9)
  - Session-aware: ASIAN/LONDON/NY         - Partial TP + streak protection (v9.1)
  - Prop-firm: 3% daily / 5% drawdown     - Live market intelligence bias
  - Balance: $4,430.86 | trades: 757       - Balance: $4,502.09 | trades: 5,533
```

### Core Agents (Swarm Brain)

| Agent | Role | Entry Point |
|-------|------|------------|
| **Hermes** | High-reasoning architect; strategy design, roadmap review, trade analysis | `automode.py` |
| **OpenCode** | Code review, implementation, trading logic verification | `automode.py` |
| **Pi.dev** | Security guardian, compliance audit, gitignore verification | `automode.py` |
| **OpenClaw** | Gateway coordinator, integration health, task generation | `automode.py` |
| **Researcher** | Market research via DeepSeek browser agent | `automode.py` |
| **Social** | Video production, social media content, Postiz publishing | `automode.py` |
| **PAI** | Life OS skills: Research, ExtractWisdom, WorldThreatModel, RootCauseAnalysis | `automode.py` |
| **GSD** | Phase automation: code-review, audit-fix, docs-update, codebase-map | `automode.py` |
| **Hermes Trade** | Reads trading logs, generates improvement_suggestions.json | `automode.py` |
| **OpenCode Trade** | Applies auto_apply=true parameter improvements to trading agents | `automode.py` |
| **PiDev Monitor** | Watches liveea.py + live_trading_binance.py; restarts if dead | `automode.py` |

### Supporting Infrastructure

- **Mission Control** (`core/apps/dashboard/mission_control.py`) — Real-time swarm dashboard, port 10000
- **Automode v5** (`automode.py`) — Autonomous task execution, peer-review loop, failure tracking
- **Obsidian Vault** — Second brain at `data/obsidian/`, synced to GDrive via rclone
- **Supabase** — Self-hosted Docker, PostgREST API at localhost:3000
- **Firebase** — Log backup service (30-min interval, 7 collections: logs, daily_summaries, market_intel, supabase_mirror, system_snapshots, system_state, trading_state)
- **Dify** — RAG knowledge base with graphify pipeline
- **DeepSeek Browser Agent** — Research tasks via `scripts/run_deepseek_agent.py`

---

## Repository Structure

```
human-ai/
├── agents/                         # All agent code
│   ├── trading-agent/              # EA v10.1 + Binance v9.1 + strategies + MT5 MQ5
│   │   ├── live_trading_ea.py      # EA Trader v10.1 (XAUUSD/XAGUSD/EURUSD/GBPUSD)
│   │   ├── live_trading_binance.py # Binance Scalper v9.1 (7 symbols)
│   │   ├── ea/                     # MQ5 source files (MasterMetalsEA_v56.mq5, etc.)
│   │   ├── strategies/             # FreqTrade strategy implementations
│   │   └── trades/                 # Live trade feeds (mt5/, binance/)
│   ├── social/                     # Social media modules
│   │   ├── media_generator.py      # Video generation (TikTok/YT Shorts/Reels)
│   │   ├── content_pipeline.py     # Content creation pipeline
│   │   └── post_scheduler.py       # Posting scheduler
│   ├── pai_agent.py                # PAI skill wrapper (Research, ExtractWisdom, etc.)
│   ├── social_media_agent.py       # Social media orchestrator
│   └── macro_agent_xau_xag.py      # Macro market intelligence
│
├── core/                           # Core libraries + applications
│   ├── orchestration/              # automode.py, task_dispatcher.py, trading loops
│   ├── agents/                     # Core agent implementations
│   ├── apps/                       # Applications
│   │   └── dashboard/              # Mission Control (port 10000)
│   ├── integrations/               # External API bridges
│   │   ├── supabase_logger.py      # Supabase persistence
│   │   ├── dify_brain.py           # Dify RAG integration
│   │   ├── graphify_bridge.py      # Knowledge graph bridge
│   │   └── mcp_bridge.py          # MCP tool bridge
│   └── utils/                      # Shared utilities
│
├── data/                           # Runtime data (gitignored)
│   ├── feeds/                      # ea_live_trades.jsonl, binance_live_trades.jsonl
│   ├── logs/                       # All agent logs
│   ├── media_output/               # 88+ generated videos + images
│   ├── obsidian/                   # Obsidian second brain
│   └── market_cache/               # Cached market intelligence (Alpaca, etc.)
│
├── docs/                           # Documentation
│   ├── ROADMAP.md                  # Current roadmap (uppercase — canonical)
│   ├── roadmap.md                  # Phase 3/4 detail roadmap
│   ├── TRADING_AGENTS_STATUS.md    # Live agent status
│   ├── IMPROVEMENTS_SUMMARY.md     # System improvement history
│   ├── pow/                        # Proof-of-work records (agent outputs)
│   └── task_archive/               # Archived automode tasks
│
├── scripts/                        # Operational scripts
│   ├── install.sh                  # Portable bootstrap for fresh Linux instance
│   ├── ea/liveea.py                # EA autonomous launcher (called by root liveea.py)
│   ├── produce_video.py            # Video generation CLI
│   ├── sync/                       # Obsidian + GDrive sync
│   └── system/                     # Cloud backup (Supabase, Firebase, GDrive)
│
├── infrastructure/                 # Runtime configs, Docker, K8s, Terraform
│   └── configs/                    # Runtime state files
│
├── automode.py                     # Root launcher — Automode v5
├── liveea.py                       # Root launcher — delegates to scripts/ea/liveea.py
├── startbinance.py                 # Root launcher — starts Binance scalper via nohup
├── stopbinance.py                  # Stop Binance scalper gracefully
├── stopea.py                       # Stop EA + close all MT5 positions
├── unified_tasks.json              # Unified task queue for all agents
└── requirements.txt                # Python dependencies
```

---

## Common Operations

### Start / Stop Trading Agents

```bash
# Start EA Trader v10.1 (XAUUSD/XAGUSD/EURUSD/GBPUSD)
python3 liveea.py

# Stop EA + close all MT5 positions
python3 stopea.py

# Start Binance Scalper v9.1 (7 symbols)
python3 startbinance.py

# Stop Binance scalper
python3 stopbinance.py
```

### Automode (Autonomous Swarm)

```bash
# Run all agents in the self-tasking loop
python3 automode.py

# Run a specific agent only
python3 automode.py hermes
python3 automode.py opencode
python3 automode.py pai
```

### Dashboard

```bash
# Mission Control — real-time swarm monitor (port 10000)
python3 core/apps/dashboard/mission_control.py
# Access at http://localhost:10000
```

### Video Production

```bash
# Produce a video (default: christian mode, 4 videos/day scheduled)
python3 scripts/produce_video.py --topic "XAUUSD daily analysis" --platform youtube_shorts --duration 45
python3 scripts/produce_video.py --topic "BTC breakout signal" --platform tiktok --signal BUY

# Produce FaithNexus channel video
python3 scripts/produce_itnexus_video.py

# Switch video mode (christian / trading)
# Edit data/config/video_mode.json — set "mode": "christian" or "mode": "trading"
# christian = FaithNexus content (default)
# trading   = market analysis / XAUUSD / BTC content
# Output dirs: gdrive:HumanAI/videos/trading/all/ and gdrive:HumanAI/videos/christian/
# Current stats: trading/all=80 videos, christian=21 videos
```

### Sync / Backup

```bash
# Full sync: Obsidian vault → GDrive
python3 scripts/sync/full_sync.py

# Backup Supabase to GDrive
bash scripts/backup_supabase_to_gdrive.sh

# Sync Dify with knowledge graph
python3 scripts/sync/dify_graphify_bridge.py

# Firebase backup runs automatically every 30 minutes
# 7 collections: logs, daily_summaries, market_intel, supabase_mirror,
#                system_snapshots, system_state, trading_state
```

### Verification

```bash
# Verify all integrations
python3 core/integrations/verify_all_integrations.py

# Health check
python3 core/utils/swarm_health_check.py
```

---

## Technical Stack

| Category | Technologies |
|----------|-------------|
| **Languages** | Python 3.11, MQL5, TypeScript |
| **Trading** | MetaTrader 5 (MT5 file bridge), Binance Demo Futures (CCXT), FreqTrade, Alpaca |
| **LLM Routing** | NVIDIA NIM direct (nvidia/llama-3.3-nemotron-super-49b-v1) — all agents |
| **Media / Video** | Pollinations.ai (free images), SiliconFlow FLUX, scripts/produce_video.py |
| **Social** | Postiz (publishing), config/social_cron.yaml (schedule) |
| **Database** | Supabase (self-hosted Docker + cloud), Firebase, SQLite |
| **Knowledge** | Dify (RAG), Graphify (knowledge graph), Obsidian vault |
| **Sync** | rclone (GDrive), scripts/sync/, GitHub |
| **Automation** | Camoufox (stealth browser), Telethon (Telegram), n8n |
| **Monitoring** | Mission Control dashboard (port 10000) |
| **CI/CD** | Adaptive pipeline, self-healing scripts |

---

## Environment Setup

```bash
cp .env.example .env
nano .env   # Fill in API keys — see .env.example for full list
```

Key variables:
- `NVIDIA_API_KEY` — NVIDIA NIM direct (primary LLM for all agents)
- `BINANCE_TESTNET_API_KEY` / `BINANCE_TESTNET_SECRET` — Binance demo futures
- `SUPABASE_URL` + `SUPABASE_KEY` — Supabase cloud backup
- `ALPACA_API_KEY` + `ALPACA_SECRET_KEY` — market data + paper trading
- `FIREBASE_SERVICE_ACCOUNT` — Firebase backup service (project: human-ai-6fed9)
- `OPENROUTER_API_KEY` — optional fallback LLM routing

---

## Connected Services

| Service | Status | Purpose |
|---------|--------|---------|
| NVIDIA NIM | Connected | LLM routing — all agents (llama-3.3-nemotron-super-49b-v1) |
| Binance Demo Futures | Connected | Crypto scalping (7 symbols) |
| Alpaca | Connected | Market data + market intel feed |
| MetaTrader 5 | Connected | XAUUSD/XAGUSD/EURUSD/GBPUSD live trading |
| Supabase (self-hosted) | Connected | localhost:3000, 9 tables |
| Firebase | Running | Log backup service — 7 collections, 30-min interval |
| GDrive (rclone) | Configured | Obsidian vault + videos (gdrive:HumanAI/) |
| Obsidian | Synced | Second brain at data/obsidian/ |
| Dify | Configured | RAG knowledge base |
| n8n | Configured | Workflow automation |
| Postiz | Configured | Social media publishing |
| Telegram | Connected | Telethon bot integration |
| DeepSeek Browser | Active | Research via scripts/run_deepseek_agent.py |
| OpenRouter | Optional | Fallback LLM routing |

---

## Safety & Protocols

- **Stealth-First**: Browser interactions use Camoufox with randomized user agents
- **Audit-Locked**: No code deployed without Pi.dev verification (Pass report required)
- **Dead-Man Switch**: `agents/trading-agent/deadman_switch.py` — liquidates on catastrophic drawdown
- **Prop-Firm Safe**: EA enforces 3% daily limit, 5% max drawdown, 0.05L hard cap
- **Automode Fail-Safe**: Tasks permanently fail after 3 retries; max 3 consecutive agent failures before pause
- **Credential Protection**: All secrets in `.env`, enforced by `.gitignore`; zero committed keys
- **PROTOCOL.md**: Agents may only modify allowed paths; README.md is write-protected by protocol

---

## Roadmap Status

| Phase | Status | Key Items |
|-------|--------|-----------|
| Phase 1: Foundation | COMPLETE | Core agents, Supabase, OpenClaw gateway |
| Phase 2: SQUAD Loops | COMPLETE | AntFarm, NativeWorker, browser-first, hardened sandbox |
| Phase 3: Live Trading | COMPLETE | EA v9 live, Binance v7 live, Automode v3+, Mission Control |
| Phase 4: Optimisation | ACTIVE | EA v10.1, Binance v9.1, Firebase, market intel, GSD v1.42.2 |

### Phase 4 — Completed Items (2026-05-15)
- EA v10.1: H1 EMA bias, breakout boost, EURUSD/GBPUSD, REVERSE oscillation fix
- Binance v9.1: ATR SL/TP, volume filter, circuit breaker, partial TP, market intel
- Live market intelligence: Fear/Greed + CoinGecko + Alpaca + Binance 4H + news
- Dashboard: daily P&L tile, video tile, live log streaming, agent chips, 7-day chart
- Firebase: log backup service (30-min, 7 collections), Supabase mirror
- Video pipeline: christian/trading split, MoviePy v2, smart naming
- All agents → NVIDIA NIM direct (OpenRouter removed)
- GSD updated to v1.42.2
- automode v5: GSD/PAI bugs fixed (555 silent failures resolved)

### Phase 4 — Remaining
- EA: backtest v10.1 on historical XAUUSD — validate H1 filter impact
- Binance: live performance review after v9.1 runs 48h on demo-fapi
- Social: wire Postiz publishing schedule end-to-end (cron → Postiz)
- Supabase: create agent_backups table in cloud Supabase project

---

*This repository is a living organism. It evolves its own structure, logic, and agents through a continuous loop of Research → Implement → Verify → Remember. The swarm self-tasks 24/7 via Automode v5.*
