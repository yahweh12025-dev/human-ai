---
name: Ports & Services
description: Mission Control dashboard on port 10000 and other services
type: reference
---

**Primary Services:**
- Mission Control Dashboard: `http://localhost:10000`
  - Real-time visibility into agent tasks and system health
  - Start with: `python apps/dashboard/monitoring_dashboard.py`

**Memory API Server:** Runs with the core system; provides persistence layer for agent memories

**Agent Communication:** Inter-agent messaging via `agent_communication_protocol.py` on internal event bus

**Database:** SQLite typically in `data/` directory:
- Sentiment & signal tracking
- Historical trade data
- Knowledge base storage

**Log Collection:** All agent logs flow to `logs/` with structured tagging for audit trails

**Check ports in use:**
```bash
# If dashboard fails to start on port 10000
lsof -i :10000
# or
netstat -tulpn | grep 10000
```

**Service startup order:**
1. Memory API server (persistence layer)
2. Task dispatcher (`core/orchestration/task_dispatcher.py`)
3. Individual agents as needed
4. Dashboard (port 10000)
