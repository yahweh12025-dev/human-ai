---
name: Architecture Overview
description: Human-AI project architecture with 4 core agents
type: project
---

Human-AI is a multi-agent swarm built on FreqTrade with a dual-brain architecture:

**Four Core Agents:**
- **OpenClaw**: Gateway coordinator - manages inter-agent communication, session health, and sub-agent deployment
- **Hermes**: High-reasoning architect - responsible for strategy design, complex orchestration, and long-term memory
- **OpenCode**: Implementation engine - handles all coding tasks, repository refactoring, and feature development
- **Pi.dev**: Guardian and security layer - performs code reviews, validates reasoning logic, enforces stealth/anti-detection protocols

**Supporting Systems:**
- Merkle Chain for secure, traceable logging of agent decisions
- Knowledge graph and cross-agent learning system
- Adaptive resource allocation and workload balancing
- Self-healing infrastructure with circuit breakers
- Stealth-first browser automation via Camoufox

**Tech Stack:** Python, FreqTrade/FreqAI, CCXT, TA-Lib, FastAPI, SQLite, Next.js (dashboard)

All code changes must pass Pi.dev's verification before deployment.
