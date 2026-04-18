# 🚀 Human-AI Agent Swarm

A high-fidelity research and implementation engine designed for autonomous exploration and verified code generation.

## 🏗️ Architecture: The Hybrid Swarm
The system employs a multi-layered orchestration strategy:
- **Orchestrator (AntFarm)**: Manages the "Squad" pipeline (Retrieve $\rightarrow$ Research $\rightarrow$ Implement $\rightarrow$ Verify $\rightarrow$ Remember).
- **Implementation (NativeWorker)**: Direct LLM-to-Code generation using OpenRouter.
- **Verification (Docker Sandbox)**: All generated code is executed in an isolated container to prevent host damage.
- **Memory (Dify Brain)**: A RAG-powered knowledge hub for long-term context persistence.

## 🛠️ Installation & Setup
1. **Clone the repo**: `git clone <repo_url>`
2. **Environment**: Copy `.env.example` to `.env` and fill in your API keys.
3. **Dependencies**: Install via `pip install -r requirements.txt`.
4. **Infrastructure**: Ensure Docker is installed and running for the Sandbox.

## 🗺️ Roadmap
For a detailed view of the agent registry and current development milestones, please refer to [ROADMAP.md](./ROADMAP.md).

## 🛡️ Security
- **Secret Management**: Integration with Infisical for rotated keys.
- **Guardrails**: Strict enforcement of free-only models.
- **Isolation**: Code execution is strictly limited to a non-networked Docker sandbox.


## Recent Updates
- **2026-04-18**: Swarm verification successful

- **2026-04-18**: Implemented a fully autonomous Document Intelligence pipeline including Converter and OCR agents.

- **2026-04-18**: Successfully integrated GenericAgent into AntFarm Orchestrator