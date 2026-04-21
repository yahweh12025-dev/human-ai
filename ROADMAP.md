# Human-AI Agent Swarm Roadmap

## Vision
A self-evolving, autonomous multi-agent system capable of continuous development, research, and self-optimization.

## Current Focus
- **Stability & Reliability**: Hardening browser-first LLM integrations (DeepSeek).
- **Security**: Repository secret scrubbing and token rotation.
- **Tooling**: Improving the Swarm Optimizer and Health Bot.

## Roadmap Phases

### Phase 1: Foundations & Core Stability
- [x] Establish core agent framework (AntFarm).
- [x] Implement Browser-First LLM routing (DeepSeek Browser Agent).
- [x] Establish secure sandbox environment for code execution.

### Phase 2: Capability Evolution
- [x] **Researcher Evolution**: Playwright browsing + YouTube synthesis.
- [ ] **Universal Self-Improvement**: Deploy `self_improvement` skill for autonomous loop.
- [ ] **Memory Core**: Implement Hermes-style context caching for faster reasoning.
- [ ] **Kilo-Code Integration**: Verify high-fidelity read/write/edit delegation.

### Phase 3: Enterprise Integration
- [ ] **n8n-mcp Integration**: Implement deterministic workflows for complex business logic.
- [ ] **Omni-Channel Intelligence**: Implement API/Browser rotation for robust access.
- [ ] **Dify Knowledge Hub**: Integrate RAG-based knowledge retrieval.

### Phase 4: The Ecosystem & Control
- [ ] **Knowledge Legacy**: Categorize and push past AI chat history/data to Supabase.
- [ ] **Control Center**: Build Dashboard GUI for agent and swarm control (Vercel connected).
- [ ] **Omni-Channel Output**: Integration with multiple messaging platforms.

## Future Integrations
### Manus AI Integration
- **Goal**: Leverage Manus AI's advanced browser-based reasoning for high-complexity tasks.
- **Strategy**:
    - Implement `ManusBrowserAgent` leveraging the existing Playwright infrastructure.
    - Handle Google SSO authentication via persistent browser sessions.
    - **Credit Management**: Implement a usage tracker to respect daily credit limits.
    - **Routing**: Create a 'Complexity Router' to decide when to use DeepSeek (standard) vs Manus (complex).
- **Status**: Pending implementation.
