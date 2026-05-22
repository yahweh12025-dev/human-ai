# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The **Human-AI Project** is a self-evolving, autonomous multi-agent swarm for high-alpha trading,
deep-web research, and automated social media content. It combines a dual-brain trading architecture
(EA v10.1 for metals + Binance v11.1 for crypto) with autonomous content creation and a self-improving
agent loop via Automode v7.

Core agents:
- **OpenClaw**: Gateway coordinator managing inter-agent communication
- **Hermes**: High-reasoning architect for strategy design and orchestration
- **OpenCode**: Implementation engine for coding and refactoring
- **Social**: Video production and social media content (100+ videos produced)
- **GSD**: Phase automation agent (code-review, audit-fix, docs-update, codebase-map)
- **Researcher**: DeepSeek browser-based market research
- **Hermes Trade / OpenCode Trade**: Trading improvement loop agents

Trading engines:
- **EA Trader v11** (`agents/trading-agent/live_trading_ea.py`) — XAUUSD/XAGUSD/EURUSD/GBPUSD via MT5 file bridge.
  Start: `python3 liveea.py`. Prop-firm safe: 3% daily / 5% max drawdown / 0.05L hard cap.
  All-session adaptive: ASIAN min_score=7, LONDON/LONDON_NY/AFTER_NY min_score=5, ATR dead threshold=0.25.
- **Binance Scalper v11.1** (`agents/trading-agent/live_trading_binance.py`) — BTC/ETH/BNB/SOL/XRP/TRX/ADA demo futures.
  Start: `python3 startbinance.py`. Dynamic leverage up to 75x. MAX_HOLD_S=130s (data-proven profitable window).

The system integrates with:
- Alpaca API (market data + paper trading)
- Binance Demo Futures (CCXT) — crypto scalping
- MetaTrader 5 — metals/forex trading via file bridge
- DeepSeek (research via browser agent)
- OpenRouter + Groq + NVIDIA NIM (LLM routing)
- Camoufox (stealth browser automation)
- Supabase (self-hosted Docker + cloud — agent_backups, agent_logs)
- Firebase (file storage)
- GDrive via rclone (Obsidian vault + backup sync)
- Dify (RAG knowledge base)
- Graphify (knowledge graph)
- Obsidian (second brain at `data/obsidian/`)
- Postiz (social media publishing)
- **GSD** (Get Shit Done) — meta-prompting / phase automation via `core/gsd_integration.py`

## Repository Structure

```
human-ai/                    # Main project directory
│
├── automode.py              # Automode v7 — autonomous swarm controller
├── liveea.py                # EA launcher (delegates to scripts/ea/liveea.py)
├── startbinance.py          # Binance scalper launcher (nohup)
├── stopbinance.py           # Stop Binance scalper
├── stopea.py                # Stop EA + close MT5 positions
├── unified_tasks.json       # Unified task queue: pending/completed/failed
│
├── agents/                  # All agent code
│   ├── trading-agent/       # EA v11 + Binance v11.1 + strategies + MQ5 files
│   │   ├── live_trading_ea.py      # EA Trader v11 (XAUUSD/XAGUSD/EURUSD/GBPUSD)
│   │   ├── live_trading_binance.py # Binance Scalper v11.1 (BTC/ETH/BNB/SOL/XRP/TRX/ADA)
│   │   ├── deadman_switch.py       # Catastrophic drawdown liquidation
│   │   ├── ea/                     # MQ5 source (MasterMetalsEA_v56.mq5, etc.)
│   │   └── strategies/             # FreqTrade strategies
│   ├── social/              # media_generator, content_pipeline, post_scheduler
│   └── social_media_agent.py
│
├── core/                    # Core libraries + applications
│   ├── orchestration/       # Automode logic, task_dispatcher, trading loops
│   ├── agents/              # Core agent implementations (Hermes, etc.)
│   ├── apps/dashboard/      # Mission Control dashboard (port 10000)
│   ├── integrations/        # supabase_logger, dify_brain, graphify_bridge, mcp_bridge
│   ├── health/              # Health monitoring
│   └── utils/               # Shared utilities
│
├── apps/                    # Standalone applications
│   ├── dashboard/           # Monitoring dashboard (port 10000)
│   ├── postiz/              # Social media automation (Postiz)
│   └── alpha_integration/   # Alpha signal integration
│
├── data/                    # Runtime data (gitignored)
│   ├── feeds/               # ea_live_trades.jsonl, binance_live_trades.jsonl
│   ├── logs/                # All agent logs (data/logs/<agent>.log)
│   ├── media_output/        # 100+ videos + images (faithnexus/, itnexus_final/, etc.)
│   ├── obsidian/            # Obsidian second brain (synced to GDrive)
│   └── market_cache/        # Cached market intelligence (Alpaca, etc.)
│
├── docs/                    # Documentation
│   ├── ROADMAP.md           # Canonical roadmap
│   ├── roadmap.md           # Phase 3/4 operational roadmap
│   ├── TRADING_AGENTS_STATUS.md
│   ├── IMPROVEMENTS_SUMMARY.md
│   ├── pow/                 # Proof-of-work records (agent outputs)
│   └── task_archive/        # Archived automode tasks
│
├── scripts/                 # Operational scripts
│   ├── install.sh           # Portable bootstrap for fresh Linux instance
│   ├── ea/liveea.py         # EA autonomous launcher (full MT5 automation)
│   ├── produce_video.py     # Video generation CLI
│   ├── sync/                # Obsidian + GDrive sync, dify_graphify_bridge
│   └── system/              # Cloud backup (Supabase, Firebase, GDrive)
│
├── infrastructure/          # Runtime configs, node_modules, K8s, Terraform
│   └── configs/             # Runtime state files
│
├── config/                  # Configuration files
│   └── social_cron.yaml     # Social media posting schedules with timezone support
│
├── .env                     # Environment configuration (local, NOT committed)
└── requirements.txt         # Python dependencies
```

## Common Development Tasks

### Environment Setup
```bash
# Navigate to project
cd human-ai

# Create virtual environment (Python 3.11 recommended)
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Tests
```bash
# Run all tests with pytest
cd human-ai
pytest

# Run a specific test file
pytest tests/test_backtesting.py

# Run a specific test function
pytest tests/test_backtesting.py::test_backtest_basic

# Run with verbose output
pytest -v

# Run tests matching a pattern
pytest -k "test_binance"

# Run integration tests only
pytest tests/integration/

# Run agent tests
pytest tests/agents/
```

### Trading Bot Operations (FreqTrade-based)
```bash
# Show bot configuration
freqtrade show-config

# Run backtest
freqtrade backtesting --strategy YourStrategy --timerange 20240101-20250101

# Run with hyperopt
freqtrade hyperopt --strategy YourStrategy --epochs 100

# Start trading bot (paper/live)
freqtrade trade --strategy YourStrategy

# Show current trades
freqtrade status

# Stop bot gracefully
freqtrade stop

# Delete a trade
freqtrade delete-trade <trade_id>
```

### Trading Agent Operations
```bash
# Start EA Trader v10.1 (XAUUSD/XAGUSD via MT5)
python3 liveea.py

# Stop EA + close all MT5 positions
python3 stopea.py

# Start Binance Scalper v11.1 (BTC/ETH/BNB/SOL/XRP/TRX/ADA demo futures)
python3 startbinance.py

# Stop Binance scalper
python3 stopbinance.py
```

### Mission Control Dashboard
```bash
# Start Mission Control — real-time swarm monitor (port 10000)
python3 core/apps/dashboard/mission_control.py
# Access at http://localhost:10000
```

### Automode (Autonomous Swarm)
```bash
# Start OpenClaw manager (monitors and manages ALL automodes)
python3 core/orchestration/openclaw_manager.py

# Or run individual focused automodes
python3 scripts/autobinance.py    # Binance trading automation
python3 scripts/autoea.py         # EA MetaTrader 5 automation
python3 scripts/autosocial.py     # Social media / video automation
python3 scripts/autosync.py       # Backup / sync all integrations

# Full swarm automode
python3 automode.py               # All agents
python3 automode.py hermes        # Single agent
```

### Video Production
```bash
# Generate a trading video (TikTok/YouTube Shorts/Instagram Reels)
python3 scripts/produce_video.py --topic "XAUUSD analysis" --platform youtube_shorts --duration 45
python3 scripts/produce_video.py --topic "BTC signal" --platform tiktok --signal BUY
```

### Sync / Backup
```bash
# Full sync: Obsidian vault → GDrive
python3 scripts/sync/full_sync.py

# Backup Supabase to GDrive
bash scripts/backup_supabase_to_gdrive.sh
```

### Database & Data
```bash
# Verify all integrations (Supabase, OpenRouter, MT5, etc.)
python3 core/integrations/verify_all_integrations.py

# Download historical market data (FreqTrade)
freqtrade download-data --pairs BTC/USDT --timerange 20240101-20250101
```

## Architecture Notes

### Agent Communication
- Agents communicate via `agent_communication_protocol.py` using message passing
- The system uses a gateway pattern with OpenClaw as the central coordinator
- Cross-agent knowledge sharing enabled through `knowledge_sharing_system.py`


### Swarm Features
- **Self-Tasking**: Automode v6 injects fresh tasks from per-agent task banks when queue is low
- **Peer Review**: Every completed task spawns a REVIEW task assigned to another agent
- **Self-Improvement**: Hermes Trade → improvement_suggestions.json → OpenCode Trade applies changes
- **Failure Tracking**: Tasks permanently fail after 3 retries; stored in task_queue.failed
- **Dead-Man Switch**: `agents/trading-agent/deadman_switch.py` liquidates on catastrophic drawdown
- **Stealth Operations**: Browser automation uses Camoufox with randomized user agents
- **Knowledge Graph**: Dify (RAG) + Graphify + Obsidian vault form the swarm's memory

### Trading Engine (Dual-Brain)
- **EA v10.1** (XAUUSD/XAGUSD): 3-pillar signal (trend + RSI divergence + Bollinger structure),
  session-aware regimes (ASIAN/LONDON/NY), RANGE mean-reversion mode, prop-firm safe
- **Binance v11.1** (BTC/ETH/BNB/SOL): 10s ticks, 60s max hold, dynamic leverage (50%→75x max),
  partial TP at 0.30%, SL move to breakeven, TP2 at 0.60%
- **FreqTrade V9** strategy in `agents/trading-agent/strategies/freqtrade_v9.py`
- Multiple exchange support via CCXT; backtesting in `data/tests/`

### CI/CD & Infrastructure
- Adaptive CI/CD: `infrastructure/adaptive_cicd.yaml`, `cicd_pipeline.yaml`
- Docker containerization in `infrastructure/docker/`
- Kubernetes deployments in `infrastructure/k8s/`
- Terraform IaC in `infrastructure/terraform/`
- Self-healing deployment systems

### GSD Integration
- **gsd-opencode v1.38.5** installed at `~/.config/opencode/` — GSD for OpenCode
  Run: `npx gsd-opencode` or `gsd-opencode install --global`
- **pi-gsd** installed via `pi install npm:pi-gsd` — GSD for Pi
- Python wrapper: `core/gsd_integration.py` — `invoke_gsd_skill(skill_name, context)`
- Registered as `'gsd'` agent in `core/orchestration/automode.py` `_AGENT_TASK_BANK`
- Routes in `_execute_gsd_task()`: auto-selects skill from task description keywords
- GSD skills available: plan-phase, code-review, audit-fix, progress, map-codebase, docs-update, debug, validate-phase
- Logs to `data/logs/gsd_integration.log`

## Configuration Files

- `.env` - Environment variables (API keys, secrets) - **DO NOT COMMIT** — backed up to `gdrive:backups/env/`
- `config/social_cron.yaml` - Social media posting schedules with timezone support
- `REPO_METADATA.json` - Repository sync status
- `self_directed_task_log.json` - Task tracking
- `docs/BACKUP_POLICY.md` - GDrive backup policy (single obsidian sync, video org)

## YouTube / Postiz OAuth2

- Postiz self-hosted at `http://localhost:5000` (start: `bash scripts/start_postiz.sh`)
- YouTube OAuth2 Client ID: see `YOUTUBE_CLIENT_ID` in `.env`
- YouTube Client Secret: see `YOUTUBE_CLIENT_SECRET` in `.env`
- Authorized redirect URI: `http://localhost:4200/oauth2/callback/youtube`
- Set these in Google Cloud Console → OAuth2 Credentials → Authorized redirect URIs

## Key External Integrations

- **MetaTrader 5**: Live metals trading (XAUUSD/XAGUSD) via file-based bridge + MQ5 EA
- **Binance Demo Futures**: Crypto scalping (BTC/ETH/BNB/SOL) via CCXT
- **Alpaca API**: Market data cache (`data/market_cache/alpaca_*.json`) + paper trading
- **CCXT**: Cryptocurrency exchange connectivity (Binance, Kraken, OKX, Bybit, etc.)
- **DeepSeek**: Web research via browser agent (`scripts/run_deepseek_agent.py`)
- **OpenRouter**: LLM routing and model selection (GPT-4, Claude, Gemini, etc.)
- **Groq**: Fast inference for time-sensitive agent tasks
- **NVIDIA NIM**: Hosted PAI skills via `NVIDIA_API_KEY`
- **Camoufox**: Anti-detection browser automation (stealth-first)
- **Supabase**: Self-hosted Docker at localhost:3000; agent_backups + agent_logs tables
- **Firebase**: File storage for backups
- **GDrive (rclone)**: Obsidian vault + Supabase backup sync
- **Dify**: RAG knowledge base (`core/integrations/dify_brain.py`)
- **Graphify**: Knowledge graph (`scripts/sync/dify_graphify_bridge.py`)
- **Obsidian**: Second brain vault at `data/obsidian/ (canonical vault; ~/obsidian-vault symlinks here)
- **Postiz**: Social media publishing engine
- **Pollinations.ai**: Free image generation for social content

## Development Workflow

1. **Feature Development**: OpenCode agent handles implementation tasks
2. **Code Review**: Self-review and cross-agent verification
3. **Verification**: Cross-agent output verification ensures correctness
4. **Deployment**: Infrastructure automation handles CI/CD
5. **Monitoring**: Mission Control dashboard provides real-time visibility

## Important Notes

- All code changes undergo OpenCode self-review and cross-agent verification before deployment
- The system includes automated circuit breakers for trading protection
- Stealth-first approach for browser interactions (avoid bot detection)
- Knowledge persists in the Merkle Chain for auditability
- The repository evolves autonomously - expect structural changes over time

## Performance Testing

```bash
# Stress tests exist in tests/stress_test_master.py
# Trading-specific stress: trading_agent_stress_test_suite.py

# Backtesting validation
pytest tests/test_backtesting.py
pytest tests/test_freqai_backtesting.py

# Exchange connectivity tests
pytest tests/test_binance.py tests/test_kraken.py tests/test_bybit.py
```

## Troubleshooting

1. **Missing dependencies**: Verify Python 3.11 and reinstall from requirements.txt
2. **Database errors**: Check data/ directory permissions and .env configuration
3. **Agent communication failures**: Check logs/ directory and task_dispatcher.py status
4. **Dashboard not loading**: Port 10000 may be in use; check for conflicting services
5. **Exchange API errors**: Verify API keys in .env match exchange requirements

## Memory & State

- Long-term memories stored in `memory/MEMORY.md` and daily logs
- Agent sessions tracked in `core/sessions/`
- Performance metrics in `core/metrics/`
- State rollback capability via `state_rollback_manager.py`

## Recent Changes (May 2026)
- Obsidian vault cleaned: removed 48GB recursive repo mirror, now 2.9MB
- yfinance installed in .venv (was missing, causing synthetic candle data)
- EA ATR dead threshold: 0.60 → 0.25 (was blocking all LONDON trades)
- EA min_score: 5 → 4 for LONDON/LONDON_NY/AFTER_NY sessions
- GDrive: all 100 trading videos synced to gdrive:HumanAI/videos/trading/
- Numerai skeleton: agents/numerai/ (activate by adding NUMERAI_API_KEY to .env)
- SECURITY: .env and firebase-key.json were accidentally in Obsidian vault — now removed. Rotate API keys.
