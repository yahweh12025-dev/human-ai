---
name: Development Workflow
description: Feature dev, Pi.dev review, verification, deployment
type: project
---

The Human-AI development cycle is autonomous with human oversight:

1. **Feature Development**: OpenCode agent implements new features, refactors code, and handles repository changes using its code generation capabilities

2. **Code Review & Security**: Pi.dev (Guardian) performs:
   - Security audits and vulnerability scanning
   - Reasoning logic validation
   - Stealth/anti-detection protocol enforcement
   - Automated code quality checks via `hardening_mod_*.py` modules

3. **Cross-Agent Verification**: Multiple verification systems:
   - `cross_agent_output_verifier.py` validates inter-agent consistency
   - `cross_agent_verifier.py` ensures correctness across agent boundaries
   - Verification sync system tracks all validation results

4. **Deployment**: Infrastructure automation:
   - CI/CD pipelines (`infrastructure/adaptive_cicd.yaml`, `cicd_pipeline.yaml`)
   - Docker containerization and Kubernetes deployments
   - Self-healing deployment systems
   - Blue-green or canary deployments with rollback capability

5. **Monitoring**: Mission Control dashboard (port 10000) provides real-time visibility into agent tasks and system health

**Important**: No code reaches production without a "Pass" from Pi.dev. The system includes hard-coded circuit breakers for fail-safe trading protection.
