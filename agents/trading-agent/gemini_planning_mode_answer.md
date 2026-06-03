Gemini
About Gemini
Opens in a new window
Gemini App
Opens in a new window
Subscriptions
Opens in a new window
For Business
Opens in a new window
New chat
Conversation with Gemini
You said

What is the best plugin, skill, MCP server, or GitHub repository to install with Hermes Agent to enable a "planning mode" similar to Oh My OpenCode's planning mode for OpenCode? I need a structured way for the agent to create, review, and execute plans before taking action — with approval gates and step-by-step execution tracking.







Specifically:




1. Does Hermes already have built-in planning capabilities or a skill for this?




2. What MCP servers (e.g. agentmemory, sequential-thinking, etc.) best support planning workflows?




3. What GitHub repos or community plugins add planning mode to agentic frameworks?




4. Can you recommend a specific combination of tools to replicate Oh My OpenCode's planning experience inside Hermes?




5. Any tips on configuration — prompt templates, cron jobs, or skill chaining?

Google Search
Query successful
Try again without apps
Gemini said

Replicating the strict, text-gated planning mode of systems like Oh My OpenCode inside Hermes Agent requires moving away from pure conversational prompting and leaning heavily into harness engineering (Yang, 2026). Because Hermes Agent operates on an interactive loop governed by self-contained "Skills" and Model Context Protocol (MCP) servers (Küsters, 2026; Maloyan, 2026), you can implement a rigid state machine for planning, approval gates, and step execution.

Here is the breakdown of how to build and configure this exact setup.

1. Built-in Planning Capabilities in Hermes

Hermes Agent does not have an out-of-the-box, hard-coded "planning mode" state machine. By default, it relies on its base LLM to handle intent parsing and tool routing dynamically (Huang, 2026). However, Hermes' architectural core is its Self-Evolving Skill framework (Zhan, 2026). It uses markdown-based procedural files (SKILL.md) paired with executable code scripts to teach itself how to behave (Zhan, 2026).  

To get a planning mode, you must explicitly package planning as a core Skill that intercepts user instructions before they hit the general shell tool.

2. Top MCP Servers to Support Planning

To guarantee that the agent adheres to step-by-step execution tracking and state boundaries, you should plug the following MCP servers into Hermes:

sequential-thinking (Anthropic / Community): Forces the agent to break down tasks into explicit, sequential sub-steps. It prevents the model from rushing to a final conclusion by enforcing a cycle of thought, refinement, and revision before any environmental action is executed.

agentmemory or Memory MCP: Vital for maintaining the state of the plan. Because planning across long-horizon tasks can easily saturate the context window, a dedicated memory server allows Hermes to track [Pending], [Executing], [Verified], and [Failed] step states persistently outside its active short-term context (Yang, 2026).

3. GitHub Repos & Community Plugins

To enforce the governance, side-effect boundaries, and human-in-the-loop approvals found in advanced coding harnesses, look at these open-source integrations:

nousresearch/hermes-agent: The foundational repository where you will register your planning skills.

MOSS ([github.com/maloyan/sleeper-channels](https://github.com/maloyan/sleeper-channels) / arxiv:2605.22794): While MOSS is designed for source-level self-evolution, its core architecture details how to hook into the Hermes shell and inject robust verification gates and user-consent-gated loops (Cai, 2026).

OpenClaw / OpenClaw Hooks: Hermes and OpenClaw share highly parallel runtime abstractions (Cai, 2026). Utilizing structural webhook setups or middleware hooks allows you to freeze the agent's execution loop during a plan transition until an external approval is received.

4. Recommended Stack to Replicate "Oh My OpenCode"

To mirror OpenCode's strict three-phase pipeline (Plan Create → Review/Gate → Tracked Execution), deploy this combination:

[User Input] ──> [Hermes Agent System Prompt Constraint]
                         │
                         ▼
             [Skill: planning_orchestrator]
                         │
       ┌─────────────────┴─────────────────┐
       ▼                                   ▼
[MCP: sequential-thinking]       [MCP: agentmemory]
(Drafts & Refines Steps)       (Persists Plan State)
       │
       ▼
[Human Approval Gate] ──(Rejected)──> Redraft Plan
       │
   (Approved)
       ▼
[Skill: step_executor] ──> Modifies Files / Runs Tools


Orchestrator: Hermes Agent (nousresearch/hermes-agent).

State Logic: A custom planning_orchestrator Skill.

Reasoning Engine: The sequential-thinking MCP server.

Tracking Database: Local JSON/SQLite managed via an agentmemory MCP server.

5. Configuration Tips: Prompt Templates & Skill Chaining

To enforce the planning mode without the agent "breaking character" or skipping gates, configure a dedicated Skill workflow rather than relying on standard system prompts (Zhan, 2026).

A. The Orchestration Skill (skills/planning_mode/SKILL.md)

Create a persistent skill file in your Hermes workspace. This acts as a procedural adapter that binds the agent's behavior (Yang, 2026):  

Markdown
# Skill: Strict Planning Mode

## Trigger
Trigger this skill whenever a user submits a complex task, multi-file code modification, or explicitly requests a plan.

## Core Protocol
You are forbidden from calling standard bash, file_edit, or network tools until a plan has achieved an `APPROVED` state from the user.

## Operational Steps
1. Call `sequential_thinking` to break the request into individual, deterministic steps.
2. Format the output into a structured Plan Table (id, description, dependencies, state).
3. Save the plan to memory using the memory tool.
4. Present the plan to the user with an explicit blockquote asking for confirmation: 
   > **PLAN WAITING FOR APPROVAL:** Please reply with "APPROVED" to execute, or provide feedback to modify.
5. Halt execution. Do not assume approval.

B. Skill Chaining for Step-by-Step Execution

Once the user enters "APPROVED", you must chain the orchestrator to a strict tracking loop. Instruct Hermes to execute exactly one step at a time, modifying the memory state after each action:

Fetch & Lock: Read the plan table from memory. Identify the lowest-indexed [Pending] step.

Execute: Execute only the tool calls required for that specific step.

Verify: Run a self-check or verification call (e.g., compile the code, check file existence).

Update: Update the step status to [Verified] or [Failed] via your memory server.

Loop/Halt: If a step fails, halt and ask for intervention. If it succeeds, loop back to step 1.

C. Hardening the Approval Gate via Shell Wrapper

Because LLMs can occasionally suffer from "paraphrase laundering" or accidentally execute commands they shouldn't (Maloyan, 2026), the safest way to enforce the approval gate is to intercept commands at the harness level.

If you are running Hermes Agent inside a Docker container, configure a light shell alias or middleware script wrapper around your execution terminal. This wrapper checks for an APPROVED=true flag in a local .plan_status file before allowing any destructive CLI commands to execute on the host machine.

References

Cai, Q. (2026). MOSS: Self-Evolution through Source-Level Rewriting in Autonomous Agent Systems. arXiv preprint arXiv:2605.22794.

Huang, C. H. (2026). WSInsight: a cloud-native, agent-callable platform for single-cell whole-slide pathology. bioRxiv.

Küsters, A. (2026). Trusted but not trustworthy: a conceptual analysis of AI agent risks in the metaverse and EU policy responses. Frontiers in Virtual Reality, 7.

Maloyan, N. (2026). Sleeper Channels and Provenance Gates: Persistent Prompt Injection in Always-on Autonomous AI Agents. International Journal of Open Information Technologies.

Yang, C. (2026). A Survey of Agent Skills: Toward Procedural Infrastructure for LLM Agents. Preprints.org.

Zhan, Z. (2026). Auto-Policy, not Auto-Skill: Compiled Agent Skills for the Physical World. OpenReview.

Sources




Tools
Flash

Gemini is AI and can make mistakes.