---
name: env-request-manager
description: Controlled process for agents to request and receive new .env keys via a secure request log (to be approved by human or future agent).
metadata: {"openclaw":{"emoji":"🔑","requires":{"bins":[]}}}
user-invocable: true
---

# Env-Request Manager Skill

## What this skill controls
A secure system for agents to request new environment variables (e.g., API keys) that are then logged for approval.

The skill manages a request log where agents can submit requests for new .env keys. A human (or a future trusted agent) reviews the log and approves requests by adding the key to the actual .env file or a secure vault.

## Core Functionality
- Agents can submit a request for a new environment variable (e.g., "OPENAI_API_KEY") with a justification.
- Requests are logged to a secure, append-only log file with timestamp, agent ID, variable name, and justification.
- The skill does NOT grant the key directly; it only facilitates the request and logging process.
- A separate process (human or agent) reviews the log and fulfills approved requests by modifying the environment securely.

## How Agents Use This Skill
Agents do not call this skill directly to get keys. Instead:
1.  They use the skill to log a request for a needed key.
2.  They wait for the key to be provided via a secure channel (e.g., human adds it to .env, or a trusted agent provisions it).
3.  Once the key is available in the environment, the agent proceeds with its task.

## Files Managed
- Default request log: `/home/ubuntu/human-ai/logs/env_request_log.md`
- The skill only appends to this log; it never reads or modifies existing entries for security.
- The actual .env file (`/home/ubuntu/.openclaw/.env` or similar) is managed outside this skill for security.

## Security Notes
- This skill is designed to be **append-only** for the request log to prevent tampering.
- It never returns or exposes actual keys—it only facilitates the request process.
- The actual fulfillment of requests (adding keys to .env) must be done by a trusted entity (human or future agent) outside this skill's direct control to maintain security boundaries.

## Example Workflow
1.  Researcher agent needs a new API key for a tool.
2.  Researcher uses this skill to log a request: "Need OPENAI_API_KEY for GPT-4o access to improve paper summarization."
3.  The request is logged to `/home/ubuntu/human-ai/logs/env_request_log.md` with timestamp and agent ID.
4.  A human reviews the log periodically, approves the request, and adds the key to the actual .env file.
5.  The Researcher agent detects the key is now available in the environment and proceeds.

## Non-negotiable rules
1.  **Never return or expose actual keys**. This skill only logs requests.
2.  **The request log must be append-only**. Never modify or delete existing log entries.
3.  **Log entries must include**: timestamp, requesting agent ID, variable name requested, and justification.
4.  **Do not write to the actual .env file**. This is a security boundary.

## Commands (if applicable)
This skill is primarily designed to be used programmatically by agents via its Python interface, not as a CLI tool.

### Request Logging
- To log a request, an agent would call the skill's Python function:
  ```python
  await env_request_manager.log_request("OPENAI_API_KEY", "Need GPT-4o access for advanced reasoning tasks.")
  ```