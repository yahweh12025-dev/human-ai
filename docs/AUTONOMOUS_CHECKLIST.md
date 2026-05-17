# ✅ Autonomous Health Checklist
*To be executed at the start of every Major Development Cycle.*

## 🔍 Stage 1: Infrastructure Audit
- [ ] **Gateway Health**: Is `openclaw` process running?
- [ ] **Autopilot Pulse**: Is the `agent-autopilot` heartbeat active in logs?
- [ ] **Resource Check**: Are CPU/RAM levels stable for Playwright?

## ⚠️ Stage 2: Error Triage
- [ ] **Error Log Scan**: Check `/home/ubuntu/human-ai/errors/` for new `.log` files.
- [ ] **Log Analysis**: Review `autodev.log` for "Unknown Command" or "RLS Violation" errors.
- [ ] **Resolution**: Fix any critical blockers before proceeding.

## 🔑 Stage 3: Vault & State Verification
- [ ] **Secret Access**: Can the agent retrieve a test key from the Cloud Vault?
- [ ] **Memory Sync**: Is the latest `memory/YYYY-MM-DD.md` synced to Supabase?
- [ ] **Todo Alignment**: Does the `todo-management` list reflect the current `ROADMAP.md`?

## 🌐 Stage 4: Deployment Readiness
- [ ] **Git Clean**: Are there any uncommitted changes in the workspace?
- [ ] **GitHub Sync**: Is the local `main` branch aligned with `origin/main`?
- [ ] **Backup**: Is the current `todo.db` backed up to the cloud?
