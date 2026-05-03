# 🗺️ Human-AI Swarm Roadmap

## Phase 1: Foundation & Stabilization ✅ (COMPLETED)
- [x] Core Agent Architecture (Researcher, Navigator, Developer).
- [x] Supabase Logging Integration.
- [x] Basic Sandbox Execution.
- [x] OpenClaw Gateway Connectivity.

## Phase 2: The "SQUAD" & High-Fidelity Loops ✅ (COMPLETED)
- [x] **AntFarm Orchestrator**: Implementation of the Retrieve $ightarrow$ Research $ightarrow$ Implement $ightarrow$ Verify loop.
- [x] **NativeWorker**: Transition to server-less implementation engine.
- [x] **Browser-First Mandate**: All agents routed through the browser (Playwright) for LLM access.
- [x] **Researcher Evolution**: Integrated YouTube transcript synthesis and hybrid routing.
- [x] **Hardened Sandbox**: Custom Docker images for dependency-free execution.
- [x] **Master Log System**: Global event aggregation for the entire swarm.

## Phase 3: Orchestration & Ecosystem 🚀 (IN PROGRESS)
- [x] **Hybrid LLM Routing**: Implement rate-aware switching between OpenCode and DeepSeek via browser (OpenCode for coding, DeepSeek for volume)
- [x] **Kilo Code Integration**: Replaced by `opencode` as the primary engine for autonomous code refactoring and high-fidelity feature implementation.
- [x] **Document Intelligence Suite**:
    - [x] Develop `ConverterAgent` for multi-format transformation (PDF, Word, PPTX, JSON $leftrightarrow$ TXT, MD).
    - [x] Develop `OCRAgent` for visual text extraction and layout analysis.
- [x] Integrate as a pre-processing layer for Researcher and Developer agents.
- [x] **Notebook LM Specialist Agent**: Create a browser-based agent that uses Google Notebook LM for document upload, summarization, comparison, and insight extraction.
- [x] **Memory Bridge Implementation**: Create a synchronization pipeline to distill "wisdom" and key decisions from Hermes' daily memory into the Swarm's global MEMORY.md
- [x] **Omni-Model Intelligence Layer**: 
    - Integrate browser-based Claude (Reasoning) with rate-limit handling.
    - Use LangChain as the orchestration bridge to standardize browser-LLM access.
- [ ] **Dify & Graphify Synergy**: Implement LangChain-based pipelines to route data between Dify (RAG) and Graphify (Knowledge Graph).
- [x] **Mission Control**: Implemented as replacement for Swarm Command Center - Centralized orchestration dashboard
- [ ] **Dify Knowledge Hub**: Finalize RAG integration and "Remember" phase for verified solutions.
- [ ] **n8n-mcp Integration**: Implement deterministic workflows for repetitive tasks.
- [ ] **Opencode Browser Integration**: Add OpenCode via browser-first automation for coding tasks
- [ ] **Omni-Channel Intelligence**: Refine the Adaptive Router for multi-modal input.

- [ ] **Obsidian Integration**: Integrate Obsidian for local knowledge management and memory enhancement
## Phase 4: Swarm Bot Testing & Lifecycle 🔬 (DEFERRED)
- [ ] **Swarm Telegram Bot Integration**: Create and configure @Swarm26_bot for inter-agent communication
- [ ] **Swarm Session Management**: 90% token usage reset mechanisms for swarm agents
- [ ] **Swarm Telegram Logging**: Dedicated logging and monitoring for bot interactions
- [ ] **Swarm Development Tracking**: Activity logging and progress tracking for swarm development
- [ ] **Security Audit & Lockdown**: Complete full repository secret scrub and verify token rotation

## Phase 5: Financial Intelligence & Trading (Future Consideration)
- [ ] **FinceptTerminal Integration**: Explore integrating the FinceptTerminal repository (https://github.com/Fincept-Corporation/FinceptTerminal) as a specialized financial data and trading analysis agent.
    *   This would involve assessing its capabilities for real-time market data, technical analysis, and trading signal generation.
    *   If compatible, it could be integrated as a specialized agent within the swarm for Phase 4 tasks related to financial analysis, trading strategy development, and market prediction.
    *   Integration would require evaluating its API, data formats, and compatibility with the swarm's browser-first mandate and Hybrid LLM Router.
    *   This is a placeholder for future investigation and is not part of the current active development cycle.

## 📝 Current Todo Queue


## Repository Organization (Updated 2026-04-19)
- **Agents**: Intelligence Layer
    - skills/: All agent brains.
    - core/: Core utilities.
    - tasks/: Task coordination.
- **System Support**
    - browser_profiles/: Browser profiles.
    - vault/: Secrets, keys, tokens.
    - state/: State files (cache, etc.).
    - logs/: System logs.
    - triage/: Failure analysis.
    - utils/: Utilities.
    - lib/: Libraries.
    - assets/: Frontend assets.
    - scripts, tools/: External utilities.
- **Data & Insights**
    - results/: Final results.
    - tests/: Tests.
    - obsidian/: Obsidian knowledge.
    - memory/: Daily logs.
- **Source of Truth**
    - README.md, MEMORY.md, etc.
- **Active Automation**
    - scripts/: Active scripts.
- **Legacy**: Legacy code and triage.

## Phase 3: Orchestration & Ecosystem 🚀 (STATUS UPDATE - 2026-04-19)
- [x] **AntFarm Orchestrator**: Implementation of the Retrieve $ Research $ Implement $ Verify loop.
- [x] **NativeWorker**: Transition to server-less implementation engine.
- [x] **Browser-First Mandate**: All agents routed through the browser (Playwright) for LLM access.
- [x] **Researcher Evolution**: Integrated YouTube transcript synthesis and hybrid routing.
- [x] **Hardened Sandbox**: Custom Docker images for dependency-free execution.
- [x] **Master Log System**: Global event aggregation for the entire swarm.
- [x] **Navigator Agent State-Machine**: Implemented the core architecture for multi-step goal tracking using an Action-Observation Loop.
- [x] **Action-Observation Loop for Navigator**: Built the Observe-Plan-Act-Evaluate cycle using the Hybrid LLM Router for reasoning.
- [x] **Hybrid LLM Routing**: Implement rate-aware switching between Gemini and DeepSeek via browser (Gemini for reasoning, DeepSeek for volume)
- [ ] **Kilo Code Integration**: Integrate Kilo Code as the primary engine for autonomous code refactoring and high-fidelity feature implementation
- [x] **Document Intelligence Suite**:
    - Develop ConverterAgent for multi-format transformation (PDF, Word, PPTX, JSON $leftrightarrow$ TXT, MD).
    - Develop OCRAgent for visual text extraction and layout analysis.
    - Integrate as a pre-processing layer for Researcher and Developer agents.
- [x] **Notebook LM Specialist Agent**: Create a browser-based agent that uses Google Notebook LM for document upload, summarization, comparison, and insight extraction.
- [ ] **Memory Bridge Implementation**: Create a synchronization pipeline to distill "wisdom" and key decisions from Hermes' daily memory into the Swarm's global MEMORY.md
- [x] **Omni-Model Intelligence Layer**: 
    - Integrate browser-based Perplexity (Search) and Claude (Reasoning) with rate-limit handling.
    - Integrate Mistral Free API for low-latency logic checks.
    - Use LangChain as the orchestration bridge to standardize browser-LLM access.
- [ ] **Dify & Graphify Synergy**: Implement LangChain-based pipelines to route data between Dify (RAG) and Graphify (Knowledge Graph).
- [x] **Mission Control**: Implemented as replacement for Swarm Command Center - Centralized orchestration dashboard
- [ ] **Dify Knowledge Hub**: Finalize RAG integration and "Remember" phase for verified solutions.
- [ ] **n8n-mcp Integration**: Implement deterministic workflows for repetitive tasks.
- [ ] **Gemini Browser Integration**: Add Google Gemini via browser-first automation (cookie-based auth like DeepSeek), vision-capable with rate-limit aware routing
- [ ] **Omni-Channel Intelligence**: Refine the Adaptive Router for multi-modal input.
