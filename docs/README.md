# Human-AI Swarm — Documentation

**Last updated: 2026-05-15**

---

## Key Documents

| File | Description |
|------|-------------|
| [ROADMAP.md](ROADMAP.md) | Project phases, milestones, current priorities |
| [TRADING_AGENTS_STATUS.md](TRADING_AGENTS_STATUS.md) | EA v10.1 + Binance v9.1 current status |
| [TECH_STACK.md](TECH_STACK.md) | Full technology stack reference |
| [IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md) | All improvements by session |
| [AGENT_COMMUNICATION.md](AGENT_COMMUNICATION.md) | Inter-agent messaging protocol |
| [API_REFERENCE.md](API_REFERENCE.md) | API endpoint reference |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development workflow and standards |
| [PROTOCOL.md](PROTOCOL.md) | Swarm operation protocols |
| [SWARM_MEMORY.md](SWARM_MEMORY.md) | Persistent swarm memory notes |
| [core_audit_20260515.md](core_audit_20260515.md) | Core codebase audit (2026-05-15) |
| [repo_consolidation_20260515.md](repo_consolidation_20260515.md) | Repo cleanup log (2026-05-15) |

---

## Directory Structure

```
docs/
├── 1.Trading Metals/           # MT5 EA strategy documents (consolidated)
├── api/                        # API documentation
├── cronjobs/                   # Cron job documentation
├── obsidian/                   # Obsidian vault notes
├── plans/                      # Planning documents
├── security_audit/             # Security audit outputs
├── social/                     # Social media agent docs
├── specs/                      # Technical specifications
├── task_archive/               # Archived task logs
├── templates/                  # Document templates
├── verification/               # Verification reports
├── archive/
│   ├── pow_20260515/           # 944 POW files archived 2026-05-15
│   └── pow_pre_20260515/       # 1,555 older POW files
└── pow/                        # Current proof-of-work outputs (empty after archival)
```

---

## Trading Agent Quick Reference

| Agent | Version | Symbols | Status |
|-------|---------|---------|--------|
| EA Trader | v10.1 | XAUUSD, XAGUSD, EURUSD, GBPUSD | RUNNING |
| Binance Scalper | v9.1 | BTC, ETH, BNB, SOL, XRP, ADA, DOGE | RUNNING |
| Automode | v5 | — | RUNNING |

---

## Recent Changes (2026-05-15)

- EA upgraded to v10.1 (H1 bias, multi-symbol, REVERSE fix)
- Binance upgraded to v9.1 (ATR risk, market intelligence, 7 symbols)
- 944 POW files archived from docs/pow/
- 1,555 older POW files archived from docs/pow/archive/
- 6 duplicate trading strategy docs removed from root (kept in 1.Trading Metals/)
- 5 root-only compact docs consolidated into 1.Trading Metals/
- TECH_STACK.md updated (NVIDIA NIM direct, market intel, video pipeline, Firebase)
- ROADMAP.md updated (Phase 4 completed items)
