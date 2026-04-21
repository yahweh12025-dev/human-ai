# Human-AI Agent Swarm Roadmap

## Vision
A self-evolving, autonomous multi-agent system capable of continuous development, research, and self-optimization.

## Current Focus
- **Stability & Reliability**: Hardening browser-first LLM integrations (DeepSeek).
- **Security**: Repository secret scrubbing and token rotation.
- **Tooling**: Improving the Swarm Optimizer and Health Bot.

## Future Integrations
### Manus AI Integration
- **Goal**: Leverage Manus AI's advanced browser-based reasoning for high-complexity tasks.
- **Strategy**:
    - Implement `ManusBrowserAgent` leveraging the existing Playwright infrastructure.
    - Handle Google SSO authentication via persistent browser sessions.
    - **Credit Management**: Implement a usage tracker to respect daily credit limits.
    - **Routing**: Create a 'Complexity Router' to decide when to use DeepSeek (standard) vs Manus (complex).
- **Status**: Pending implementation.

## Architecture
- **Core Agents**: Located in `core/agents/`
- **Infrastructure**: Located in `infrastructure/`
- **Skills**: Located in `skills/`
