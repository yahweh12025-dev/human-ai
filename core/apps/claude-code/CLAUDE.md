# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The **Human-AI Project** is a self-evolving, autonomous multi-agent swarm built on top of the FreqTrade framework. It combines high-alpha algorithmic trading with autonomous content creation via a dual-brain architecture:
- **OpenClaw**: Gateway coordinator managing inter-agent communication
- **Hermes**: High-reasoning architect for strategy design and orchestration
- **OpenCode**: Implementation engine for coding and refactoring
- **Pi.dev**: Guardian for security audits and verification

The system integrates with:
- Alpaca API (trading/data)
- DeepSeek (research)
- OpenRouter (LLM routing)
- Telegram (Telethon)
- Camoufox (stealth browser automation)

## Repository Structure

```
human-ai/                    # Main project directory
├── core/                    # Foundational libraries and systems
│   ├── agents/              # Core agent implementations
│   ├── api/                 # API endpoints (swarm_bridge.py)
│   ├── orchestration/       # Task dispatcher, execution loops
│   ├── health/              # Health monitoring systems
│   ├── integrations/        # External service integrations
│   ├── metrics/             # Metrics collection
│   ├── researcher/          # Research agent components
│   ├── sessions/            # Session management
│   ├── utils/               # Shared utilities
│   ├── agent_communication_protocol.py  # Inter-agent messaging
│   ├── knowledge_graph.py               # Knowledge representation
│   ├── knowledge_sharing_system.py      # Cross-agent learning
│   ├── memory_api_server.py             # Memory persistence
│   └── hardening_mod_*.py               # Security hardening modules
│
├── agents/                  # Top-level specialized agents
│   ├── browser/             # Browser automation agents
│   ├── crewai_workflows/    # CrewAI integration
│   ├── prompts/             # Agent prompt templates
│   ├── roles/               # Agent role definitions
│   ├── trading-agent/       # Trading-specific agents
│   └── *.py                 # Individual agent modules
│
├── apps/                    # Standalone applications
│   ├── dashboard/           # Monitoring dashboard (port 10000)
│   ├── postiz/              # Social media automation (Postiz)
│   ├── alpha_integration/   # Alpha signal integration
│   └── claude-code/         # Claude Code integration files
│
├── tests/                   # Comprehensive test suite (pytest)
│   ├── agents/              # Agent-specific tests
│   ├── integration/         # Integration tests
│   ├── health/              # Health check tests
│   └── test_*.py            # 100+ test files covering core functionality
│
├── infrastructure/          # Deployment and operations
│   ├── deploy/              # Deployment scripts
│   ├── docker/              # Docker configurations
│   ├── k8s/                 # Kubernetes manifests
│   ├── terraform/           # Infrastructure as code
│   ├── tools/graphify/      # Graph visualization tooling
│   ├── agent_workers/       # Worker configurations
│   └── *.py                 # Self-healing, auto-scaling, CICD systems
│
├── config/                  # Configuration files
│   └── social_cron.yaml     # Social media scheduling
│
├── data/                    # Data storage (outside git)
├── logs/                    # Centralized logging
├── docs/                    # Technical documentation
├── skills/                  # Agent skill definitions
├── knowledge/               # Knowledge base
├── workspace/               # Working files
├── validation/              # Validation reports (JSON)
├── verification/            # Verification scripts
├── scripts/                 # Utility scripts
├── research/                # Research outputs and reports
├── swarm/                   # Swarm coordination
├── security_audit/          # Security audit outputs
│
├── .env                     # Environment configuration (local, not committed)
├── requirements.txt         # Python dependencies
├── README.md                # Project overview
└── REPO_TREE.md             # Full repository tree (generated)
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

### Mission Control Dashboard
```bash
# The dashboard runs on port 10000 by default
# Access at http://localhost:10000
# Start via infrastructure/deploy scripts or directly:
python apps/dashboard/monitoring_dashboard.py
```

### Agent Operations
```bash
# OpenClaw gateway operations (example)
# Start the swarm coordinator
python core/orchestration/task_dispatcher.py

# Or use the infrastructure automation
python infrastructure/opencode_bot.py
python infrastructure/pidev_bot.py
```

### Database & Data
```bash
# The project uses SQLite for sentiment/signal tracking
# Database files are typically in data/ directory

# Download historical market data
freqtrade download-data --pairs BTC/USDT --timerange 20240101-20250101
```

## Architecture Notes

### Agent Communication
- Agents communicate via `agent_communication_protocol.py` using message passing
- The system uses a gateway pattern with OpenClaw as the central coordinator
- Cross-agent knowledge sharing enabled through `knowledge_sharing_system.py`
- Agent health monitored via `sub_agent_health_monitor.py`

### Swarm Features
- **Merkle Chain**: Immutable audit log of agent decisions via `knowledge_graph.py`
- **Adaptive Resource Allocation**: Dynamic workload distribution
- **Self-Healing**: Automated recovery via infrastructure/self_healing_*.py
- **Circuit Breaker**: Fail-safe trading protection (hardening modules)
- **Stealth Operations**: Browser automation uses Camoufox with randomized agents

### Trading Engine
- Built on FreqTrade with extended FreqAI capabilities
- Strategies use TA-Lib indicators and ML predictions
- Multiple exchange support via CCXT (Binance, Kraken, OKX, etc.)
- Backtesting with detailed analytics in tests/test_backtesting.py

### CI/CD & Infrastructure
- Adaptive CI/CD: `infrastructure/adaptive_cicd.yaml`, `cicd_pipeline.yaml`
- Docker containerization in `infrastructure/docker/`
- Kubernetes deployments in `infrastructure/k8s/`
- Terraform IaC in `infrastructure/terraform/`
- Self-healing deployment systems

## Configuration Files

- `.env` - Environment variables (API keys, secrets) - **DO NOT COMMIT**
- `config/social_cron.yaml` - Social media posting schedules with timezone support
- `REPO_METADATA.json` - Repository sync status
- `self_directed_task_log.json` - Task tracking

## Key External Integrations

- **Alpaca API**: Market data and trading execution
- **CCXT**: Cryptocurrency exchange connectivity
- **DeepSeek**: Web research via browser agent
- **OpenRouter**: LLM routing and model selection
- **Telethon**: Telegram bot integration
- **Camoufox**: Anti-detection browser automation
- **Postiz**: Social media content engine

## Development Workflow

1. **Feature Development**: OpenCode agent handles implementation tasks
2. **Code Review**: Pi.dev performs security and quality audits before merge
3. **Verification**: Cross-agent output verification ensures correctness
4. **Deployment**: Infrastructure automation handles CI/CD
5. **Monitoring**: Mission Control dashboard provides real-time visibility

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

## Claude Code Specific

This CLAUDE.md copy is stored in `apps/claude-code/` for Claude Code integration.
The primary CLAUDE.md resides at the repository root (`/home/yahwehatwork/CLAUDE.md`).
