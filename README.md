# 🤖 Human-AI Swarm v7

[![EA Trader](https://img.shields.io/badge/EA%20Trader%20v10.1-RUNNING-brightgreen)](agents/trading-agent/live_trading_ea.py)
[![Binance](https://img.shields.io/badge/Binance%20v11.1-RUNNING-brightgreen)](agents/trading-agent/live_trading_binance.py)
[![Automode](https://img.shields.io/badge/Automode%20v7-ACTIVE-blue)](core/orchestration/automode.py)
[![OpenClaw](https://img.shields.io/badge/OpenClaw%20Manager-ACTIVE-orange)](core/orchestration/openclaw_manager.py)
[![Context7](https://img.shields.io/badge/Context7%20MCP-INSTALLED-purple)](https://github.com/upstash/context7)

Autonomous multi-agent swarm for high-alpha trading, deep-web research, and social media content.

**Last updated: 2026-05-17** | EA v10.1 ($4,431) | Binance v11.1 ($4,497) | 19 videos on GDrive

## Quick Start (Fresh Instance)
```bash
curl -s https://raw.githubusercontent.com/yahweh12025-dev/human-ai/main/scripts/install.sh | bash
```
One command installs everything: Python 3.11, Node.js, Claude Code, GSD SDK, rclone, Docker, MT5/Wine, restores from GDrive backup.

## Agents

| Agent | Role | Script |
|-------|------|--------|
| **OpenClaw** | Master orchestrator — manages all automodes | `core/orchestration/openclaw_manager.py` |
| **Hermes** | Architect — strategy design, LLM orchestration | `core/agents/hermes/` |
| **OpenCode** | Implementation — code generation & refactoring | automode task bank |
| **Pi.dev** | Security — audits, verification, compliance | automode task bank |
| **Social** | Content — video production, FaithNexus, Postiz | `scripts/autosocial.py` |
| **PAI** | Research — ExtractWisdom, WorldThreatModel | `agents/pai_agent.py` |
| **Researcher** | Deep research — GPT Researcher + DeepSeek | `agents/researcher_agent.py` |

## Trading Engines

### EA Trader v10.1 (MetaTrader 5)
- Instruments: XAUUSD, XAGUSD, EURUSD, GBPUSD
- Session-aware: ASIAN/LONDON/LONDON_NY/NY_CLOSE/AFTER_NY
- Regimes: TREND/SCALP/RANGE/DEAD with ATR-adaptive parameters
- Prop-firm safe: 3% daily / 5% max drawdown / 0.05L hard cap
- Start: `python3 liveea.py`

### Binance Scalper v11.1 (Demo Futures)
- Coins: BTC/ETH/BNB/SOL/XRP/TRX/ADA (data-driven equity allocation)
- ATR-adaptive SL/TP with min threshold (prevents near-zero SL on low-vol coins)
- 130s optimal hold time (data-proven: only profitable bucket)
- ADA/ETH boosted equity (best performers), BTC/SOL reduced
- Start: `python3 startbinance.py`

## Automation Scripts

```
python3 core/orchestration/openclaw_manager.py  # Start OpenClaw (manages everything)
python3 scripts/autobinance.py                   # Binance trading automation
python3 scripts/autoea.py                        # EA trading automation
python3 scripts/autosocial.py                    # Social/video automation
python3 scripts/autosync.py                      # Backup/sync all integrations
python3 automode.py                              # Full swarm automode
```

## Integrations

| Service | Purpose | Config |
|---------|---------|--------|
| MetaTrader 5 (Wine) | EA trading | `.env MT5_LOGIN/PASSWORD` |
| Binance Demo Futures | Crypto scalping | `.env BINANCE_DEMO_ENDPOINT` |
| OpenRouter | LLM routing | `.env OPENROUTER_API_KEY` |
| NVIDIA NIM | Free LLM (deepseek-v4-flash) | `.env NVIDIA_API_KEY` |
| Dify | RAG knowledge base | `.env DIFY_API_KEY` |
| Supabase | Self-hosted DB | `localhost:3000` |
| Firebase | Firestore + backup | `.env FIREBASE_*` |
| GDrive (rclone) | Backups + videos | `gdrive:backups/ gdrive:videos/` |
| Postiz | Social media scheduling | `http://${POSTIZ_HOST}:4200` |
| Context7 MCP | Live API docs | `~/.claude/settings.json` |
| GPT Researcher | Deep research | `agents/researcher_agent.py` |

## GDrive Structure
```
gdrive:
├── backups/
│   ├── env/          ← .env secrets backup
│   ├── obsidian/     ← vault sync (rclone sync, no duplicates)
│   └── supabase/     ← DB dumps
└── videos/
    ├── christian/    ← FaithNexus scripture videos (4)
    └── trading/      ← XAUUSD + crypto signals (15)
```

## Architecture
- **Vault logging**: All agents write to `data/obsidian/` via `core/integrations/vault_logger.py`
- **Task queue**: `unified_tasks.json` — pending/completed/failed with auto-cleanup
- **Video dedup**: `data/media_output/VIDEO_INDEX.json` — tracks used Pexels IDs
- **OpenClaw manager**: Monitors all scripts, auto-restarts if down (60s poll)

## Docs
- [CLAUDE.md](CLAUDE.md) — Claude Code guidance
- [docs/BACKUP_POLICY.md](docs/BACKUP_POLICY.md) — Backup strategy
- [data/obsidian/index.md](data/obsidian/index.md) — Obsidian vault index
