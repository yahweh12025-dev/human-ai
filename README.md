# 🧬 Human AI Swarm Architecture

This repository is evolving into a multi-agent autonomous swarm designed for deep research, rapid building, and seamless communication.

## 🏗️ Swarm Structure

### 1. The Super-Agent (`/agents/super_agent`)
The **Super-Agent** is the peak of the architecture. It has the ability to embody any of the specialized agents simultaneously, managing the context switch between researching, planning, and building to solve high-complexity problems.

### 2. Core Specialized Agents (`/agents`)
- **Researcher Agent (`/agents/researcher`)**: High-fidelity, account-based deep research (DeepSeek).
- **Navigator Agent (`/agents/navigator`)**: Anonymous, account-less high-speed web exploration.
- **Builder Agent (`/agents/builder`)**: Implementation, Aider integration, and system configuration.
- **Prompter Agent (`/agents/prompter`)**: Prompt optimization and swarm coordination.
- **Critic Agent (`/agents/critic`)**: Quality control and error elimination.
- **Planner Agent (`/agents/planner`)**: Strategic decomposition of complex goals.
- **GitHub Scout & Repo Reviewer**: External intelligence gathering.
- **Messaging Agents**: Remote interfaces for Telegram/WhatsApp.

### 3. Common Skills (`/skills`)
Shared toolsets used by all agents (e.g., `gmail_skill.py`, `file_conv_skill.py`, `github_intelligence.py`).

## ⚙️ Autonomous Infrastructure
The swarm is driven by **Specialized Background Loops** located in `/loops`:
- `core_research_loop.sh`: Constant testing and recovery of the DeepSeek agent.
- `error_resolution_loop.sh`: Triage and automated fixing of bugs.
- `skill_improvement_loop.sh`: Scouting GitHub for new capabilities.
- `feature_dev_loop.sh`: Turning templates/drafts into working code.

## 🔄 Interaction Flow
`Planner` $\to$ `Researcher/Navigator` $\to$ `Critic` $\to$ `Builder` $\to$ `Critic` $\to$ `Messaging`.

## 🚀 Portability & Cloud
Secrets and history are synced via the `CloudVaultManager` to Supabase. The entire system can be deployed to any instance using the `Infrastructure Vault`.
