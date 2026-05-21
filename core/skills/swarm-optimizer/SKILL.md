---
name: swarm-optimizer
description: Analyzes swarm development patterns, identifies recurring failure modes, and suggests architectural improvements.
category: devops
version: 1.0.0
---

# Swarm Optimizer

The Swarm Optimizer is designed to transform raw log data into actionable architectural insights. It specializes in detecting "patterned failures" where the swarm repeats the same mistake across different tasks.

## Trigger Conditions
- High failure rate in a specific agent type (e.g., browser timeouts in NativeWorker).
- Recurring `IndentationError` or `SyntaxError` in generated scripts.
- Frequent `ask_user` calls for the same type of clarification.
- Pipeline stalls in the AntFarm orchestrator.

## Procedure

### 1. Log Aggregation
- Load `/home/ubuntu/human-ai/infrastructure/logs/master_log.json`.
- Filter by `type: "ERROR"` or messages containing "Error", "Exception", "Failed".
- Group errors by `source` (agent name) and `message` similarity.

### 2. Pattern Recognition
- **Temporal Correlation**: Do errors spike after specific system updates?
- **Role Correlation**: Are failures isolated to specific roles (e.g., `security_auditor`)?
- ** tool-use Correlation**: Do failures occur predominantly during a specific tool call (e.g., `code_run`)?

### 3. Insight Synthesis
- Categorize identified patterns:
    - **Infrastructure Flaw**: e.g., "Browser timeout due to lack of dynamic polling".
    - **Prompting Gap**: e.g., "LLM fails to strip leading whitespace in shell scripts".
    - **Logic Bug**: e.g., "Recursive loop in task delegation".

### 4. Recommendation Generation
- Propose specific fixes:
    - **Skill Patch**: Suggest updates to existing skills.
    - **Wrapper Fix**: Propose changes to `GenericAgentWrapper` or `AntFarm`.
    - **SOP Update**: Recommend changes to the system's operational procedures.

## Verification
- Run the proposed fix.
- Monitor `master_log.json` for the disappearance of the identified error pattern.
- Document the improvement in the Outcome Journal.

## Pitfalls
- **Noise Overload**: Avoid treating one-off anomalies as patterns. Require a minimum occurrence threshold (e.g., 3+ times) before flagging as a pattern.
- **Context Loss**: Ensure the error is analyzed with its preceding 10-20 log entries to understand the state leading to failure.
