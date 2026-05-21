import json
import sys

with open('infrastructure/configs/todo.json', 'r') as f:
    data = json.load(f)

# Define Phase 1 and 2 keywords that should be considered completed/archived
phase12_keywords = [
    "Swarms stabilized",
    "Browser-first navigation",
    "Dr. Claw integration",
    "Free-model guardrails",
    "GitHub sync",
    "Telegram verified",
    "Researcher evolution: YouTube synthesis",
    "dashboard-1",
    "Hybrid LLM Router Validation",
    "GenericAgent Integration",
    "Outcome Journal Skill",
    "Memory Bridge Implementation",
    "ConverterAgent",
    "OCRAgent",
    "Documentation-Scribe Agent",
    "Perplexity Browser Agent implemented",
    "Claude Browser Agent implemented",
    "Omni-Model LLM Router expanded to 4 models (Gemini, DeepSeek, Perplexity, Claude)",
    "Omni-Model Router testing and validation completed",
    "Update HybridLLMRouter to handle Omni-Model routing (DeepSeek, Gemini, Perplexity, Claude)",
    "Integrated Omni-Router into core Agent Swarm loop (AntFarm Orchestrator)",
    "Outcome Scribe: Automatic roadmap/readme updates triggered by Outcome Journal SUCCESS entries",
    "Autonomous Skill Mining Loop: Discovers and deploys new AgentSkills from trusted sources",
    "Kilo-Code Integration: Verified read/write/edit delegation",
    "Kilo-Code Application: Integrated into NativeWorker for autonomous implementation",
    "Memory Bridge: Implemented offline semantic distillation",
    "Document Intelligence: ConverterAgent with MarkItDown integration",
    "Document Intelligence: OCRAgent with Tesseract integration",
    "Path Purge: All hardcoded /home/ubuntu paths removed from core agents",
    "AntFarm Orchestrator: Updated to use consolidated NativeWorker and autonomous apply logic",
    "Integrated CryptoCompare API for market intelligence (news, sentiment, market data) in trading agent",
    "Completed symmetry tests for Hermes, Opencode, and openclaw agents",
    "Verified and improved converter agent functionality",
    "Removed kilo_code_agent.py as opencode is replacing it",
    "Reviewed all agents in human-ai/core for functionality",
    "Implement background consistency check between Supabase and Firebase",
    "Vector Memory Integration: Index repo Markdown and logs into a local ChromaDB",
    "dify-graphify-bridge-1: Create sync pipeline between Outcome Journal, Dify RAG, and Graphify KG - IMPLEMENTED: Sync pipeline script created at scripts/sync/dify_graphify_bridge.py that reads new entries from Outcome Journal, optionally enriches with Dify Brain, and writes to Graphify KG wiki.",
    "skill-exp-1: Develop advanced synthesis skills for ResearcherAgent - IMPLEMENTED: Advanced synthesis capabilities added to ResearcherAgent including synthesize_advanced, synthesize_narrative, synthesize_comparative, synthesize_argumentative, synthesize_multi_perspective, detect_contradictions, resolve_contradictions, assign_confidence_scores, and format_with_citations methods.",
    "worker-stab-1: Eliminate browser timeouts in NativeWorker via dynamic polling - FIXED: Replaced fixed timeouts with dynamic polling mechanism that waits for actual completion signals, eliminating unnecessary waiting and preventing timeout failures.",
    "legacy-data-1: Ingest historical chat data into Dify Brain (FINAL STEP) - COMPLETED: Created ingestion script at scripts/sync/ingest_legacy_chat.py that parses historical chat data and prepares it for ingestion into Dify Brain."
]

# Move archived items that are actually completed to completed list if they have details
# We'll keep the archived list as is for now, but we can promote some to completed if they have completion notes.

# For simplicity, we'll update the in_progress list to match current Phase 3 tasks from AnythingLLM review
new_in_progress = [
    {
        "content": "Visual State Verification: Implement Action-Screenshot-OCR loop for Navigator",
        "id": "visual-verification-loop",
        "assigned_to": "opencode",
        "status": "pending",
        "notes": [
            "Awaiting completion of API Purge"
        ]
    },
    {
        "content": "AntFarm 2.0: Integrate pytest/ruff static analysis gate",
        "id": "antfarm-static-analysis",
        "assigned_to": "opencode",
        "status": "pending",
        "notes": [
            "Awaiting completion of API Purge"
        ]
    },
    {
        "content": "GUI-First Trading: Transition price feeds to DOM/OCR extraction",
        "id": "gui-trading-transition",
        "assigned_to": "opencode",
        "status": "pending",
        "notes": [
            "High priority: Replace ccxt/requests with browser-first data fetching"
        ]
    },
    {
        "content": "Walk-Forward Optimization: Build automated strategy parameter tuner",
        "id": "walk-forward-opt",
        "assigned_to": "opencode",
        "status": "pending",
        "notes": [
            "Dependent on GUI-First Trading transition"
        ]
    },
    {
        "content": "E2E Proof: Execute GUI-First Dummy Task (Funding Rate Extraction)",
        "id": "e2e-gui-proof",
        "assigned_to": "Hermes",
        "status": "pending",
        "notes": [
            "Final validation of the entire new architectural mandate"
        ]
    },
    {
        "content": "Monitor and analyze hermes-autonomous.log for subagent execution details and failures",
        "id": "log-monitoring-1",
        "assigned_to": "opencode",
        "status": "pending",
        "notes": [
            "Part of Phase 3 orchestration and ecosystem monitoring"
        ]
    },
    {
        "content": "Modify and improve the swarm-optimizer skill",
        "id": "swarm-optimizer-improve",
        "assigned_to": "opencode",
        "status": "pending",
        "notes": [
            "Preparing for Phase 4: Optimization & Scale"
        ]
    },
    {
        "content": "Execute trading agent feature development (add technical indicators, unit tests)",
        "id": "trading-agent-features",
        "assigned_to": "opencode",
        "status": "pending",
        "notes": [
            "Part of Phase 3 ecosystem development"
        ]
    },
    {
        "content": "Tune subagent timeouts and verify task routing assignments",
        "id": "subagent-tuning-routing",
        "assigned_to": "opencode",
        "status": "pending",
        "notes": [
            "Optimizing Phase 3 orchestration"
        ]
    }
]

# Keep archived and completed as they are, but we might want to move some archived to completed if they have completion notes.
# For now, we'll just update in_progress and leave others.

data['in_progress'] = new_in_progress

# Write back
with open('infrastructure/configs/todo.json', 'w') as f:
    json.dump(data, f, indent=2)

print("Updated todo.json")
