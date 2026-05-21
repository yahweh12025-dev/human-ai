# Tech Stack

**Last updated: 2026-05-15**

---

## Backend (Python 3.11)

- Primary language: Python 3.11
- Dependency management: pip / requirements.txt
- Agent architecture: Custom Python-based agents (Automode v5)

---

## Trading

- **MetaTrader 5**: XAUUSD / XAGUSD / EURUSD / GBPUSD live trading via file-based bridge + MQ5 EA (v10.1)
- **Binance Demo Futures**: 7-symbol scalping via CCXT (v9.1 — BTC/ETH/BNB/SOL/XRP/ADA/DOGE)
- **FreqTrade**: Strategy backtesting and live trading framework
- **Alpaca**: Market data cache (H1 trend feed) + paper trading

---

## LLM / AI

- **NVIDIA NIM (direct)**: Primary LLM provider for all agents — accessed directly via `NVIDIA_API_KEY`, no OpenRouter intermediary. Configured in `llm_routing.json`.
- **Groq**: Fast inference fallback
- **DeepSeek browser agent**: Web research tasks via `scripts/run_deepseek_agent.py`

---

## Market Intelligence

- **alternative.me**: Fear/Greed Index API
- **CoinGecko**: BTC dominance (public API)
- **Alpaca**: H1 candlestick trend data
- **Binance public API**: 4H OHLCV + RSI (no auth required)
- **CryptoCompare**: Crypto news sentiment scoring

---

## Browser Automation

- **Camoufox**: Stealth browser automation — anti-detection, randomized user agents, fingerprint spoofing
- Note: Playwright is NOT used. Camoufox is the standard browser automation layer.

---

## Dashboard / UI

- **Mission Control**: Python-based dashboard at port 10000
  - `apps/dashboard/monitoring_dashboard.py`
  - Features: daily P&L tile, live log streaming (WebSocket), agent status chips, 7-day Chart.js sparkline, video gen status
- **infrastructure/configs/**: Node.js config UI (Lucide React, shadcn)

---

## Database / Storage

- **Supabase**: Self-hosted Docker (localhost:3000) + cloud project — `agent_backups` + `agent_logs` tables
- **Firebase**: File/backup storage — project ID `human-ai-6fed9`, service account key configured
- **SQLite**: Local sentiment/signal tracking
- **GDrive (rclone)**: Obsidian vault + Supabase backup sync + video upload

---

## Knowledge / RAG

- **Dify**: RAG knowledge base (`core/integrations/dify_brain.py`)
- **Graphify**: Knowledge graph at `infrastructure/tools/graphify/` — 9,589 nodes, 20,657 edges
- **Obsidian**: Second brain vault at `data/obsidian/`

---

## Video Pipeline

- **MoviePy v2**: Video composition and editing (`scripts/produce_video.py`)
- **edge-tts**: Text-to-speech voiceover generation
- **Pexels API**: Stock footage sourcing
- **ffmpeg**: Video encoding and post-processing
- **GDrive upload**: Automatic rclone upload after render completes
- **Content channels**: `trading/` and `christian/` folder structure

---

## Social

- **Postiz**: Social media publishing engine (`apps/postiz/`)
- **config/social_cron.yaml**: Posting schedule with timezone support
- **Telethon**: Telegram bot integration

---

## Logging

- **Unified logger**: `core/utils/log_consolidator.py` — single entry point for all agent logging
- **Rotation**: 10MB max per file, 5 backup files kept
- **`show_logs.py` CLI**: `python3 scripts/show_logs.py --agent binance --level ERROR`
- **Log location**: `logs/` directory, one file per agent

---

## Automation

- **Automode v5** (`automode.py`): Autonomous swarm controller
  - Per-agent task banks with retry/failure tracking
  - GSD + PAI skill agents integrated
  - Self-improvement loop: hermes_trade → improvement_suggestions.json → opencode_trade
- **n8n**: Workflow automation (configured, not yet fully integrated)

---

## CI/CD / Infrastructure

- **Adaptive pipeline**: `infrastructure/adaptive_cicd.yaml`
- **Docker**: Supabase self-hosted, container definitions (`infrastructure/docker/`)
- **Kubernetes**: `infrastructure/k8s/` manifests
- **Terraform**: `infrastructure/terraform/` IaC
- **Self-healing scripts**: `infrastructure/self_healing_*.py`

---

## Environment Variables

See `.env` for the full list. Key variables:

| Variable | Purpose |
|----------|---------|
| `NVIDIA_API_KEY` | Primary LLM provider (NVIDIA NIM direct) |
| `BINANCE_TESTNET_API_KEY` / `BINANCE_TESTNET_SECRET` | Binance demo futures |
| `SUPABASE_URL` + `SUPABASE_KEY` | Cloud persistence |
| `ALPACA_API_KEY` + `ALPACA_SECRET_KEY` | Market data feed |
| `GROQ_API_KEY` | Fast inference fallback |
| `OPENROUTER_API_KEY` | Legacy routing (being phased out) |
| `FIREBASE_PROJECT_ID` | Firebase project: `human-ai-6fed9` |

---

## Setup

```bash
# Python dependencies
pip install -r requirements.txt

# Copy and fill in API keys
cp .env.example .env
nano .env
```
