# Human-AI Swarm — GSD Roadmap

**Based on:** Obsidian vault `knowledge/docs/ROADMAP.md` + `agents/opencode/README.md` + `agents/pidev/SYSTEM_REVIEW.md`
**Last updated:** 2026-05-31

---

## Milestone: Pi Consolidation into OpenCode

### Phase 1: GSD Bootstrap & Path Repair
**Goal:** GSD fully operational under opencode, all paths pointing to `/home/yahweh1_2025/`
**Depends on:** Nothing
**Success Criteria:**
1. `gsd-opencode` v1.38.5 installed and verified (done)
2. `.planning/config.json` updated with correct paths
3. All GSD commands resolve in opencode runtime

Plans:
- [x] 01-01: Install gsd-opencode via `npx gsd-opencode@latest --local` (done)
- [x] 01-02: Verify 33 agents + 88 commands + 35 templates present (done)
- [ ] 01-03: Update `.planning/config.json` root path from `yahwehatwork` → `yahweh1_2025` (done)

### Phase 2: Vault Consolidation
**Goal:** All agent memory in Obsidian vault, backed up to GDrive, queryable via memora
**Depends on:** Phase 1
**Success Criteria:**
1. Memora contains semantic digest of all vault markdown
2. AgentMemory graph covers all agent entities
3. GDrive sync at 100% (heal from 77%)

Plans:
- [ ] 02-01: Absorb vault markdown into memora via `memora_memory_absorb`
- [ ] 02-02: Create AgentMemory entities for all agents (OpenCode, Binance, MT5, Hermes, Social, etc.)
- [ ] 02-03: Run `rclone sync` to heal GDrive drift
- [ ] 02-04: Verify vault completeness against pidev SYSTEM_REVIEW checklist

### Phase 3: Notification & Bug Fixes
**Goal:** Clean operational state — no spam, correct balance reporting
**Depends on:** Phase 2
**Success Criteria:**
1. No `<system-reminder>` spam after task completion
2. Binance balance reflects live API, not stale cache
3. Background task failures surfaced without flooding

Plans:
- [ ] 03-01: Identify notification source (opencode config vs platform)
- [ ] 03-02: Patch/disable post-completion notifications
- [ ] 03-03: Debug Binance balance freshness in `live_trading_binance.py`
- [ ] 03-04: Add balance staleness check (>30s old → force refresh)

### Phase 4: Consolidated Agent Pruning
**Goal:** Remove all references to retired agents (PAI, antigravity, pi.dev), consolidate leftover files into opencode. Social remains as content-only agent under Hermes/OpenCode.
**Depends on:** Phase 3
**Success Criteria:**
1. No antigravity or PAI references in opencode runtime, config, or vault
2. All retired agent content migrated/archived to `agents/_archive/`
3. GitHub repos and vault structure reflect active agents only

Plans:
- [ ] 04-01: Archive `agents/antigravity/` and any PAI directories → `agents/_archive/`
- [ ] 04-02: Audit `core/skills/*` for antigravity/PAI/pidev skills → migrate or retire
- [ ] 04-03: Remove antigravity/PAI/pidev hooks from `.opencode/` and vault config
- [ ] 04-04: Update GitHub repo structure to reflect active agents only
- [ ] 04-05: Document absorbed responsibilities in `agents/opencode/README.md`

### Phase 5: Hermes Absorbs Hermes
**Goal:** Merge Hermes coordinator role into Hermes. Final active roster: **opencode** (implementation) + **hermes** (architect + coordinator + social controller) + **social** (content-only).
**Depends on:** Phase 4
**Success Criteria:**
1. Hermes responsibilities (automode management, task routing, agent spawning) fully documented in Hermes
2. No Hermes_bot references in active code; archived to `agents/_archive/Hermes/`
3. Hermes README updated with absorbed Hermes coordination duties
4. GitHub repos renamed/archived: Hermes repo archived or merged into hermes
5. Social remains content-only, fully controlled by Hermes

Plans:
- [ ] 05-01: Document all Hermes responsibilities in `agents/hermes/README.md`
- [ ] 05-02: Archive `agents/Hermes/` → `agents/_archive/Hermes/`
- [ ] 05-03: Update automode/Hermes_manager.py callers to route through Hermes
- [ ] 05-04: Audit GitHub repos — archive Hermes-specific repos or merge into hermes
- [ ] 05-05: Verify vault docs reflect final roster: opencode, hermes, social

### Phase 6: Claude Deprecation
**Goal:** Remove all Claude references from active codebase. Claude fully absorbed into OpenCode. Final roster: **opencode** (implementation + absorbed Claude/Pi.dev/PAI/antigravity) + **hermes** (architect + coordinator, absorbing Hermes) + **social** (content-only).
**Depends on:** Phase 5
**Success Criteria:**
1. No `claude` CLI references in active Python code (replaced with `opencode` CLI)
2. No `core/apps/claude-code/` references in docs or config
3. `hybrid_llm_router.py` routes to opencode instead of Claude browser agent
4. All verification/docs files updated to reflect opencode instead of Claude

Plans:
- [ ] 06-01: Replace `claude` CLI calls in `core/gsd_integration.py` with `opencode` CLI
- [ ] 06-02: Update `core/agents/hybrid_llm_router.py` — remove Claude browser agent routing
- [ ] 06-03: Archive `core/apps/claude-code/` → `core/apps/_archive/claude-code/`
- [ ] 06-04: Update all docs/ verification files referencing Claude
- [ ] 06-05: Remove `core/skills/claude-robust-review/` or rebrand to opencode

---
## Progress

| Phase | Plans Complete | Status | Completed |
|-------|---------------|--------|-----------|
| 1. GSD Bootstrap | 1/3 | In progress | - |
| 2. Vault Consolidation | 0/4 | Not started | - |
| 3. Notification Fixes | 0/4 | Not started | - |
| 4. Agent Pruning (PAI/antigravity/pidev) | 0/5 | Not started | - |
| 5. Hermes Absorbs Hermes | 0/5 | Not started | - |
