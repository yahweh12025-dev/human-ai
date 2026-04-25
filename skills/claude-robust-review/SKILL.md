---
name: claude-robust-review
category: devops
description: A robust method to access Claude.ai for tasks like code review, using the hybrid router as primary and a Botasaurus-powered agent as fallback to bypass Cloudflare.
triggers:
  - "cloudflare"
  - "Claude access failed"
  - "bypass Cloudflare"
  - "robust Claude access"
  - "Claude review fallback"
author: Hermes Agent
version: 1.0.0
---

# Robust Claude Access for Code Review

This skill provides a fallback mechanism for accessing Claude.ai when the primary method (hybrid router with Playwright-based Claude agent) fails due to Cloudflare protection or session issues.

## When to Use

Use this skill when you need to:
- Perform code reviews or analysis using Claude.ai
- The primary Claude access method is failing with Cloudflare challenges
- You want a reliable fallback that uses Botasaurus (known for effective Cloudflare bypass)
- You have already seeded a Claude session for the hybrid router (preferred) and/or for Botasaurus

## How It Works

1. **Primary Attempt**: Uses the existing hybrid LLM router to route the task to the ClaudeBrowserAgent (Playwright-based). This is fast if the session is fresh and not blocked by Cloudflare.
2. **Fallback Detection**: If the primary attempt fails with indicators of Cloudflare (timeout, challenge page, specific error messages), the skill automatically falls back to the Botasaurus-powered Claude agent.
3. **Botasaurus Fallback**: Uses Botasaurus with `bypass_cloudflare=True` to access Claude.ai, leveraging its proven effectiveness against Cloudflare protection.
4. **Session Reuse**: The Botasaurus agent attempts to reuse an existing seeded session. If none is found, it will guide the user to seed one (but ideally, the user has pre-seeded it).

## Prerequisites

1. **Hybrid LLM Router**: Must be configured and functional (already present in the system).
2. **Botasaurus**: Installed and available (verify with `pip list | grep botasaurus`).
3. **Seeded Claude Session** (for Botasaurus fallback): 
   - Run the seeding script once: `python3 /home/yahwehatwork/human-ai/skills/claude-robust-review/scripts/seed_claude_session.py`
   - This will open a browser for you to log into Claude.ai and solve any initial Cloudflare challenge.
   - After closing the browser, the session is saved for future headless use.

## Implementation Details

### Primary Method (Hybrid Router)
- Uses `HybridLLMRouter.route_task()` with keywords that trigger Claude selection (e.g., "review", "analyze", "optimize", "code").
- Relies on the existing `ClaudeBrowserAgent` which uses Playwright.

### Fallback Method (Botasaurus)
- Uses Botasaurus Driver with `bypass_cloudflare=True` in `google_get()`.
- Waits for the chat interface to load.
- Types the prompt and waits for response.
- Extracts the response from the chat interface.
- Includes timeout handling and response detection.

## Usage

This skill is designed to be used programmatically via the skill system or invoked directly through the provided scripts.

### Via Skill System (Recommended for Agents)
```python
# In your agent or task:
from hermes_tools import skill_view
skill_content = skill_view(name='claude-robust-review')
# Then execute the logic described in the skill (or delegate to a subagent that loads this skill)
```

### Direct Script Usage
```bash
# For testing or direct use:
python3 /home/yahwehatwork/human-ai/skills/claude-robust-review/scripts/claude_review_botasaurus.py \
    --prompt "Your review prompt here" \
    --trading-agent-path "/home/yahwehatwork/human-ai/agents/trading-agent/trading_agent.py"
```

## Seeding the Botasaurus Session (One-Time Setup)

Run the seeding script to create a persistent session for Botasaurus:

```bash
export BROWSER_HEADLESS=false  # Important: must be false for seeding
python3 /home/yahwehatwork/human-ai/skills/claude-robust-review/scripts/seed_claude_session.py
# Follow the prompts: log into https://claude.ai/chats, solve any Cloudflare challenge, then close the browser
export BROWSER_HEADLESS=true   # Set back to true for regular use
```

The session will be saved to `/home/yahwehatwork/.config/botasaurus/claude_session/` (or similar) and reused in subsequent headless runs.

## Error Handling and Logging

- The skill logs attempts and failures to help diagnose issues.
- If both primary and fallback fail, it returns a detailed error message including:
  - Primary error (from hybrid router)
  - Fallback error (from Botasaurus attempt)
  - Suggestions for resolution (e.g., "Try re-seeding the Botasaurus session")

## Customization

- Adjust timeouts in the Botasaurus script if needed for slower connections.
- Modify the Cloudflare detection strings in the primary failure check if Claude changes its challenge page.
- The skill can be extended to support other platforms (Gemini, Perplexity) with similar fallback logic.

## Example Workflow

1. User requests a code review of the trading agent.
2. Skill loads and tries hybrid router -> ClaudeBrowserAgent.
3. If Cloudflare challenge is detected (e.g., timeout waiting for chat input, or "Just a moment" in page title):
   - Skill switches to Botasaurus Claude agent.
   - Botasaurus loads the seeded session, navigates to Claude, types the prompt, waits for response.
   - Returns the review or an error if seeding is missing.
4. If both methods fail, returns a combined error report.

## Notes

- The primary method (hybrid router) is preferred for speed when it works.
- The fallback is slightly slower due to Botasaurus overhead but much more reliable against Cloudflare.
- Always ensure your Botasaurus session is seeded and not expired (Claude sessions may expire after inactivity).
- For frequent use, consider running the seeding script periodically to refresh the session.
