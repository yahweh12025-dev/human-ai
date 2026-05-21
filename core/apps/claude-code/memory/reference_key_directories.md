---
name: Key Directories
description: Quick reference for core/, agents/, apps/, tests/
type: reference
---

**Core Infrastructure:**
- `core/` - Foundational libraries, agents, orchestration, API endpoints
- `core/agents/` - Core agent implementations (researcher, health, utils)
- `core/orchestration/` - Task dispatcher and execution loops
- `core/api/swarm_bridge.py` - API bridge for external communication

**Agents:**
- `agents/` - Top-level specialized agents (browser, crewai_workflows, trading-agent)
- `agents/trading-agent/` - Trading-specific logic and execution
- `agents/browser/` - Browser automation using Camoufox
- `agents/prompts/` - Agent prompt templates
- `agents/roles/` - Agent role definitions

**Applications:**
- `apps/dashboard/` - Mission Control monitoring dashboard (port 10000)
- `apps/postiz/` - Social media automation (Postiz framework)
- `apps/alpha_integration/` - Alpha signal processing
- `apps/verification_dashboard/` - Verification results UI

**Testing:**
- `tests/` - Comprehensive pytest suite with 100+ test files
- `tests/agents/` - Agent-specific tests
- `tests/integration/` - Integration tests
- `tests/health/` - Health check tests

**Infrastructure:**
- `infrastructure/docker/` - Container configurations
- `infrastructure/k8s/` - Kubernetes manifests
- `infrastructure/terraform/` - Infrastructure as code
- `infrastructure/deploy/` - Deployment scripts

**Configuration & Data:**
- `config/` - Configuration files (social_cron.yaml)
- `data/` - Data storage (SQLite, market data)
- `logs/` - Centralized agent-tagged logging
- `docs/` - Technical documentation
