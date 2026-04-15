# 🗺️ Human-AI Project Roadmap & Agent Map

This document tracks the development state of the Human-AI agent swarm.

## 🤖 Agent Registry

| Agent | Status | Purpose | Primary Tool/Skill | Note |
| :--- | :--- | :--- | :--- | :--- |
| **Researcher** | 🟢 Stable | Deep web research & synthesis | `DeepSeekBrowserAgent` | Fully verified E2E with Supabase |
| **Super Agent** | 🟡 Beta | Orchestration & Delegation | `HumanAIResearcher` | Needs better routing logic |
| **Planner** | 🔴 Incomplete | High-level task decomposition | TBD | Needs structural definition |
| **Critic** | 🔴 Incomplete | Quality control & Fact-checking | TBD | Not yet integrated into pipeline |
| **Navigator** | 🟡 Beta | Complex UI interaction | `NavigatorSkills` | Auth-Flow & Data extraction implemented |
| **GitHub Scout** | 🟡 Beta | Repo discovery & analysis | `GitHub API` | Needs better filtering logic |
| **Repo Reviewer** | 🟡 Beta | Code quality & security audit | `GitHub API` | Lacks deep context integration |
| **Builder** | 🔄 Integrated | Code generation & testing | **OpenClaw Core** | Leveraging main agent for Phase 1 |
| **Comm-Bridge** | 🟡 Beta | External communication | `Supabase` / `Webhooks` | Basic connectivity only |
| **Messaging** | 🟡 Beta | User-facing alerts/chat | `Telegram` | Operational via Bot API |

## 🛠️ Skill Matrix

| Skill Name | Status | Purpose | Agent Dependency |
| :--- | :--- | :--- | :--- |
| **Advanced Scraper** | 🟢 Stable | Structured JSON extraction | Researcher, Navigator |
| **GitHub Intelligence** | 🟡 Beta | Repo analysis patterns | GitHub Scout, Repo Reviewer |
| **Cloud Vault** | 🟢 Stable | Secure Secret Management | All Agents |
| **Technical Synthesis** | 🟢 Stable | Professional report formatting | Researcher, Critic |
| **Navigator Skill** | 🔴 Pending | Multi-step web workflows | Navigator |

## 📈 Development Pipeline

### Phase 1: Foundation (Completed ✅)
- [x] GUI/XRDP stability.
- [x] DeepSeek Autonomous Login.
- [x] Supabase schema and RLS fix.
- [x] Basic Researcher end-to-end pipeline.
- [x] **Stateless Architecture**: Implemented Cloud Vault, State Sync, and Bootstrap recovery.
- [x] **Communication**: Telegram bot integration and pairing verified.

### Phase 2: Capability Expansion (Current 🚀)
- [x] **Technical Synthesis**: Implemented professional report generation.
- [ ] **Agent: Navigator**: Develop specialized skills for complex web interaction.
- [ ] **Agent: Critic**: Implement the "Fact-Check" loop.
- [ ] **GitHub Integration**: Link Repo Reviewer and GitHub Scout.

**Next Mission**: The Navigator Agent. Designing the core logic for the Navigator agent, focusing on its ability to use Playwright for multi-step, goal-oriented web navigation.

### Phase 3: Orchestration & Ecosystem (Upcoming 📅)
- [ ] **Omni-Channel Intelligence (Browser/API Hybrid)**: Implement a rotation logic that cycles between direct LLM APIs and Browser-based AI Chat interfaces (Gemini, Claude, Grok) to bypass rate limits and leverage specialized reasoning capabilities.
- [ ] **Antfarm Integration**: Transition to a "Squad" model (Writer, Reviewer, Developer pipelines).
- [ ] **Dify Knowledge Hub**: Connect the repo to a RAG-powered "Brain" for interactive querying via Telegram.

## 📝 Backlog & Technical Debt
- [ ] **Sandbox Environment**: Create a safe container for the `Builder` agent to run code.
- [ ] **Prompt Library**: Standardize system prompts across all agents for consistency.
- [ ] **API Key Rotation**: Implement secure secret management for all agent keys.
