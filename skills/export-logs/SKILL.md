---
name: export-logs
description: Exports chat session prompts and responses to the Telegram master log for archival and review.
metadata: {"openclaw":{"emoji":"📤","requires":{"bins":[]}}}
user-invocable: true
---

# Export Logs Skill

## What this skill does
Exports the current chat session's prompts and responses (as available in the agent's context or session history) to the Telegram master log (`/home/ubuntu/.openclaw/logs/telegram.log`) by writing a formatted entry to the OpenClaw commands log that is automatically picked up by the Telegram log monitor.

## How it works
1.  The skill formats the chat session data (user prompts and agent responses) into a readable markdown or text format.
2.   It creates a JSONL log entry with:
        -   `"action": "chat-export"`
        -   `"source": "telegram"` (critical for the monitor script to pick it up)
        -   `"timestamp": ISO 8601 UTC timestamp`
        -   `"chat_export": formatted string of the chat session`
3.   This line is appended to `/home/ubuntu/.openclaw/logs/commands.log`.
4.   The `telegram_log_monitor.sh` script (which runs periodically) detects new content in the commands log, filters for lines containing "telegram", and appends them to `/home/ubuntu/.openclaw/logs/telegram.log`.
5.   As a result, the exported chat session appears in the Telegram master log.

## Usage
This skill is designed to be invoked by the agent when a user sends the `/export-logs` command to the OpenClaw Telegram bot (`@hermesagent26_bot`).

When the agent receives `/export-logs`, it should:
1.  Invoke the `export-logs` skill.
2.   The skill writes the export to the commands log.
3.   The monitor script copies it to the telegram log.
4.   The user can then verify the export by checking `/home/ubuntu/.openclaw/logs/telegram.log` or by being notified that the export is complete.

## Example Output in Telegram Master Log
After running this skill, the Telegram master log (`/home/ubuntu/.openclaw/logs/telegram.log`) will contain entries like:
```
2026-04-19T15:45:00Z - CHAT EXPORT START
User: Hey. I just came online. Who am I? Who are you?
Agent: Hey. I just came online. Who am I? Who are you?
User: I am Cdreamer. You are an AI assistant helping me with my research swarm.
Agent: Thank you, Cdreamer. I'm here to assist with the swarm's autonomous development.
...
2026-04-19T15:45:00Z - CHAT EXPORT END
```

## Implementation Notes
-   The skill accesses the current session's chat history from available context or session storage.
-   If full history is not available, it exports what is accessible (e.g., recent messages from memory files or session context).
-   The export is designed to be human-readable and suitable for archival or review.
-   This skill does not send a Telegram message directly; it relies on the existing log monitoring pipeline.
-   To notify the user that the export is complete, the agent can send a separate confirmation message via its normal Telegram response mechanism.

## Files Written
-   Appends to: `/home/ubuntu/.openclaw/logs/commands.log` (which is monitored to populate `/home/ubuntu/.openclaw/logs/telegram.log`)

## Safety
-   Only appends to the log file; never modifies or deletes existing entries.
-   Does not expose sensitive information unless it is already part of the chat session.
-   Designed to be idempotent and safe to run multiple times.