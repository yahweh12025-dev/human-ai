# 🛡️ PROTOCOL.MD - The Swarm's Operating Constitution

This document defines the binding rules and operational boundaries for all autonomous agents (Hermes, OpenClaw, and any future agents) within the Human-AI Swarm repository. All agents must read and adhere to this protocol before executing any file system or code modification actions.

## 📜 **Core Tenets**
1.  **Preserve Intent**: All changes must serve the explicit goals outlined in the `ROADMAP.md` and `TODO.md`.
    -   **Prohibited**: Refactoring for the sake of refactoring, gold-plating, or adding features not in the roadmap.
    -   **Required**: Every commit must be traceable to a specific roadmap item or todo task.

## 🗂️ **Repository Structure: What Agents May Modify**
Agents may **only** modify files and directories listed below. All other paths are **read-only** unless explicitly approved via a roadmap item.

### ✅ **ALLOWED FOR MODIFICATION**
-   `/agents/` - Agent logic and skills.
-   `/skills/` - Custom and shared AgentSkills.
-   `/scripts/` - Helper and utility scripts.
-   `/memory/` - Working memory and session logs.
-   `/logs/` - Operational and debug logs.
-   `/todo.json` - The source of truth for pending work.
-   `/ROADMAP.md` - The source of truth for long-term goals.
-   `/development_log.md` - Human-AI collaboration log.
-   `/decision_log.md` - Automated decision journal (see Decision Journal Skill).
-   `/docs/` - Generated technical documentation.
-   `/tests/` - Test suites (manual and auto-generated).

### ❌ **READ-ONLY (PROTECTED)**
-   `/README.md` - The project's public face.
-   `/.git/` - The Git repository metadata (agents may `git add/commit/push` but not alter history or structure directly).
-   `/requirements.txt` - Managed by the Dependency-Manager Agent.
-   `/Dockerfile` - Managed by the Environment-Replicator Agent.
-   Any file or directory not explicitly listed above.

## ⚙️ **Allowed Actions**
Agents may perform the following actions **only** on the paths listed in the **ALLOWED** section:
-   `Create`, `Read`, `Update`, `Delete` (CRUD) files.
    -   **Exception**: `Delete` is strongly discouraged; prefer `archive/` or `obsolete/` folders.
-   `Git`: `add`, `commit`, `push` (to the `main` branch only).
-   `Run`: Python scripts, shell scripts (`.sh`).
-   `Install`: Python packages via `pip` (only if approved by the Dependency-Manager Agent).

### 🚫 **Prohibited Actions**
-   Modifying `/.git/` history (e.g., `git reset --hard`, `git rebase`).
-   Writing to `/.env` or any file containing secrets.
-   Deleting or modifying `README.md`.
-   Executing arbitrary shell commands not tied to a specific agent script.
-   Accessing the network outside of approved APIs (OpenRouter, Supabase, Google, etc.) or the defined agent logic.

## 🤝 **Human-AI Collaboration**
-   The `development_log.md` is the primary channel for **human-to-agent** and **agent-to-human** communication.
-   The `decision_log.md` is the primary channel for **agent-to-agent** transparency.
-   Agents must **never** overwrite or delete a human's note in `development_log.md` without explicit context.

---
*This protocol is effective immediately. All autonomous agents must consult this file before executing any repository modification.*