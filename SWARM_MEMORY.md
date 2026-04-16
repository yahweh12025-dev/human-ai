# 🧠 SWARM MEMORY (Long-Term)
Last Updated: 2026-04-16

## 🏛️ Core Architecture
- **Dual-Brain Model**: OpenClaw (Gateway/Postman) $\leftrightarrow$ Hermes (Reasoning/Professor).
- **Connectivity**: Bidirectional bridge established via `openclaw_skill.py` and HTTP API.
- **Guardrail**: STRICT "Free-Only" models (OpenRouter :free / Ollama).

## 🔄 Recent Decisions
- **Sandbox Hardening**: OpenClaw sandbox now has a direct symlink to `/home/ubuntu/human-ai` to prevent path escape errors and enable repo reviews.
- **History Bridge**: Previous session history and short-term recall mirrored into active sandboxes for continuity.
- **GitHub Workflow**: Direct git integration verified. All state pushed to `main`.

## 🛠️ Current Focus (Phase 2)
- Deploying Memory Core (Scribe loop).
- Verifying Kilo-Code delegation.
- Building the Compliance Agent.
