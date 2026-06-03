# State: Human-AI Swarm

> **MACHINE-READABLE:** Updates after every phase completion.
> **HUMAN-READABLE:** Latest state summary below.

---

## Machine State

```json
{
  "version": "1.0",
  "updated": "2026-05-31T18:15:00Z",
  "phase": "Pi Consolidation",
  "milestone": "OpenCode Primary",
  "current_focus": "Vault consolidation + GSD operational",
  "runtime": {
    "opencode_version": "1.15.13",
    "gsd_version": "1.38.5",
    "gsd_path": "/home/yahweh1_2025/.opencode/get-shit-done"
  },
  "services": {
    "binance-trader-v12": {
      "status": "active",
      "user": "yahweh1_2025",
      "balance": "4114.92",
      "trade_count": 1826,
      "pnl_total": "-918.22"
    }
  },
  "vault": {
    "path": "/home/yahweh1_2025/obsidian-vault",
    "sync_status": "77-percent",
    "gdrive_mount": "~/mnt/gdrive",
    "last_sync": "2026-05-20T16:34:00Z"
  },
  "memory": {
    "memora": "active",
    "agentmemory": "active",
    "engram": "active"
  },
  "agents": {
  "opencode": { "role": "implementation/claude-absorbed", "status": "primary", "absorbed": ["claude", "pidev", "PAI", "antigravity"] },
  "hermes": { "role": "architect/coordinator/absorbing-Hermes", "status": "active" },
  "Hermes": { "role": "coordinator", "status": "being_absorbed_by_hermes" },
  "social": { "role": "content-creation-only", "status": "active", "controller": "hermes/opencode" }
  },
  "blockers": [],
  "decisions": [
    {
      "id": "D-01",
      "decision": "Use opencode as primary agent replacing pi.dev",
      "status": "committed"
    },
    {
      "id": "D-02",
      "decision": "Obsidian vault as single source-of-truth",
      "status": "committed"
    },
    {
      "id": "D-03",
      "decision": "GSD SDK: gsd-opencode v1.38.5 from npm",
      "status": "installed"
    },
    {
      "id": "D-04",
      "decision": "All paths must use /home/yahweh1_2025/",
      "status": "in-progress"
    }
  ]
}
```

---

## Human Summary

**Current phase:** Pi Consolidation into OpenCode
**Milestone:** OpenCode Primary Agent
**Active workstreams:**
1. GSD bootstrap complete — 33 agents, 88 commands, 35 templates (v1.38.5)
2. Vault consolidation in progress — absorbing Obsidian content into memora
3. Binance balance freshness — needs API verification
4. Notification cleanup — system-reminder spam investigation ongoing
5. Pi deprecation pending — requires full role coverage confirmation

**Services running:**
- `binance-trader-v12.service` — active, PID 309198, balance $4,114.92
- All paths now pointing to `/home/yahweh1_2025/human-ai/`

---
*Last updated: 2026-05-31 after GSD install and vault review*