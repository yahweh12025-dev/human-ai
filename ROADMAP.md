# 🗺️ Human-AI Project Roadmap & Agent Map (Updated)

This document tracks the development state of the Human-AI agent swarm.

## 🤖 Agent Registry

| Agent | Status | Purpose | Primary Tool/Skill | Note |
| :--- | :--- | :--- | :--- | :--- |
| **Researcher** | 🟢 Stable | Deep web research & synthesis | `DeepSeekBrowserAgent` | Upgrade: YouTube Summarization + Playwright Browsing |
| **Super Agent** | 🟢 Stable | Orchestration & Delegation | `AntFarmOrchestrator` | Pipeline integrated: Writer $\rightarrow$ Reviewer $\rightarrow$ Developer |
| **Planner** | 🔴 Incomplete | High-level task decomposition | TBD | Needs structural definition |
| **Critic** | 🟢 Stable | Quality control & Fact-checking | `CriticAgent` | Fully integrated into AntFarm pipeline as Reviewer. |
| **Navigator** | 🟢 Stable | Complex UI interaction | `NavigatorSkills` | Multi-step web workflows implemented and verified |
| **GitHub Scout** | 🟡 Beta | Repo discovery & analysis | `GitHub API` | Needs better filtering logic |
| **Repo Reviewer** | 🟡 Beta | Code quality & security audit | `GitHub API` | Lacks deep context integration |
| **Builder** | 🔄 Integrated | Code generation & testing | **OpenClaw Core** | Leveraging main agent for Phase 1 |
| **Comm-Bridge** | 🟡 Beta | External communication | `Supabase` / `Webhooks` | Basic connectivity only |
| **Messaging** | 🟡 Beta | User-facing alerts/chat | `Telegram` | Operational via Bot API |
| **OCR Agent** | 🔴 Pending | Multi-format document extraction | `OCR-Core` | PDF, Word, PPTX $\rightarrow$ Text/MD/JSON |
| **Compliance Agent** | 🔴 Pending | Guardrail & Model Enforcement | `Compliance-Check` | Strict "Free-Only" model & Procedure audit |
| **Messenger Agent** | 🔴 Pending | Info Synthesis & Inter-Agent Relay | `Context-Bridge` | Summarizes data for hand-off between agents |
| **Doctor Agent** | 🔴 Pending | Error Resolution & File Healing | `Fix-It-Core` | Resolves output errors or corrupts files |

### 🚀 Future Agent Pipeline (Drafts/Templates)

#### 📱 Social Media Super-Agent
*Goal: Fully autonomous content lifecycle management.*
- **Content Planner**: Research trends, schedule posts, define themes.
- **Content Creator**: Generate text, images, and video scripts.
- **Content Reviewer**: Quality check, brand alignment, and fact-checking.
- **Content Uploader**: Automated posting via API/Playwright.
- **Analysis Agent**: Track engagement, sentiment, and iterate on strategy.

#### 📈 Trading Super-Agent
*Goal: Fully autonomous financial trading and strategy evolution.*
- **Strategy Researcher**: Analyze news, market trends, and find new alpha.
- **Signal Generator**: Apply 3+ distinct strategies to generate trade signals.
- **Backtesting Agent**: Verify signals against historical data.
- **Middle-Layer Reviewer**: Analyze backtest results vs live performance.
- **Trade Executor (Builder)**: Code/Control MT4/5 or Playwright-based browser trading.

## 🛠️ Skill Matrix

| Skill Name | Status | Purpose | Agent Dependency |
| :--- | :--- | :--- | :--- |
| **Advanced Scraper** | 🟢 Stable | Structured JSON extraction | Researcher, Navigator |
| **GitHub Intelligence** | 🟡 Beta | Repo analysis patterns | GitHub Scout, Repo Reviewer |
| **Cloud Vault** | 🟢 Stable | Secure Secret Management | All Agents |
| **Technical Synthesis** | 🟢 Stable | Professional report formatting | Researcher, Critic |
| **Self-Improvement** | 🔄 Implementing | Autonomous skill/prompt iteration | All Agents (Hermes, OpenClaw, Swarm) |
| **Enhanced Memory** | 🔴 Pending | Context caching & iterative refinement | All Agents |
| **YouTube Summarizer**| 🔴 Pending | Transcript extraction & synthesis | Researcher / Specialized Agent |

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
- [x] **Agent: Navigator**: Develop specialized skills for complex web interaction.
- [x] **Agent: Critic**: Implement the "Fact-Check" loop.
- [x] **GitHub Integration**: Link Repo Reviewer and GitHub Scout.
- [x] **Model Guardrail**: Strictly enforced free-only models across Gateway and Agents.
- [x] **Infrastructure**: Installed and configured `claw-code` CLI with OpenRouter integration.
- [ ] **Researcher Evolution**: Implement Playwright-level browsing and YouTube synthesis.
- [ ] **Universal Self-Improvement**: Deploy `self_improvement` skill to all swarm agents.
- [ ] **Memory Core**: Implement Hermes-style context caching and refinement for all agents.

### Phase 3: Orchestration & Ecosystem (Upcoming 📅)
- [ ] **Enterprise Security (Infisical)**: Migrate secrets, implement dual-phase rotation.
- [ ] **n8n-mcp Integration**: Implement MCP bridge to n8n for deterministic workflows.
- [ ] **Omni-Channel Intelligence**: Rotation logic between APIs and Browser AI.
- [x] **Antfarm Integration**: Transition to a "Squad" model.
- [ ] **Dify Knowledge Hub**: Connect repo to RAG-powered "Brain".
- [ ] **Swarm Dashboard**: Complete Vercel-deployed GUI for remote swarm control.
- [ ] **Core Support Agents**: Deploy OCR, Compliance, Messenger, and Doctor agents.

### Phase 4: Autonomous Super-Agents (Future 🌌)
- [ ] **Social Media Swarm**: Deploy 5-agent content pipeline.
- [ ] **Trading Swarm**: Deploy research $\rightarrow$ backtest $\rightarrow$ execute pipeline.
- [ ] **End-to-End Security Audit**: Full audit from Repo $\rightarrow$ Vercel $\rightarrow$ API.

## 📝 Backlog & Technical Debt
- [ ] **Sandbox Environment**: Create a safe container for the `Builder` agent.
- [ ] **Prompt Library**: Standardize system prompts across all agents.
- [ ] **API Key Rotation**: Implement secure secret management for all agent keys.
