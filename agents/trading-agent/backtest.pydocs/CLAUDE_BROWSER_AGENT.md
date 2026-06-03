# Claude Browser Agent

## Overview
The Claude Browser Agent is a browser-based agent for interacting with Claude.ai using a persistent Camoufox profile for login state and human-like behavior patterns. It replaces the previous desktop-based automation.

## Features
- Uses Camoufox (a privacy-focused Firefox fork) with persistent profile
- Utilizes Patchright/Playwright for browser automation
- Implements human-like typing, clicking, and stealth behaviors to avoid detection
- Navigates to Claude.ai and extracts responses intelligently
- Integrates with the Hybrid LLM Router for automatic task routing

## Components
1. **ClaudeBrowserAgent class** (`core/agents/claude/claudebrowser_agent.py`)
   - Initializes with a persistent Camoufox profile
   - Provides methods to start browser, ensure session, send prompts, and close
   - Uses human-like delays and interactions
   - Extracts Claude's response from the chat interface

2. **Master Seed Script** (`scripts/utility/masterseed_claude.py`)
   - Creates and maintains a persistent browser profile for Claude.ai
   - Requires one-time manual login to save session cookies and fingerprint
   - Profile stored at: `/home/yahwehatwork/human-ai/data/browser_profiles/claude/`

## Installation & Setup
1. Ensure dependencies are installed:
   ```bash
   pip install patchright playwright
   ```
   Camoufox should already be installed via the system.

2. Seed your Claude profile (run once):
   ```bash
   python3 scripts/utility/masterseed_claude.py
   ```
   - A Camoufox window will open
   - Log into Claude.ai using your Google account
   - Solve any CAPTCHAs if prompted
   - Close the browser window manually when done
   - Your session is now saved to the persistent profile

3. The agent is automatically integrated into the Hybrid LLM Router:
   - In `core/agents/hybrid_llm_router.py`, the `ClaudeBrowserAgent` is instantiated as `self.claude_agent`
   - When routing tasks to Claude, the router uses this agent

## Usage
### Direct Usage
```python
import asyncio
from core.agents.claude.claudebrowser_agent import ClaudeBrowserAgent

async def claude_task():
    agent = ClaudeBrowserAgent(headless=True)  # Set False to see automation
    try:
        await agent.start_browser()
        if await agent.ensure_session():  # Checks if logged in
            response = await agent.send_prompt("Explain quantum entanglement in simple terms")
            print(response)
        else:
            print("Session invalid - please re-run masterseed_claude.py")
    finally:
        await agent.close()

asyncio.run(claude_task())
```

### Via Hybrid LLM Router
The agent is used automatically when the router selects Claude for a task. No additional code is needed.

## Profile Location
Your seeded Claude profile is stored at:
```
/home/yahwehatwork/human-ai/data/browser_profiles/claude/
```
This directory contains cookies, localStorage, and browser fingerprint from your Google login session.

## Maintenance
- To refresh your session (if logged out or cookies expired):
  ```bash
  python3 scripts/utility/masterseed_claude.py
  ```
  Log in again and close the browser manually.

- The agent uses human-like behavior patterns:
  - Variable typing speeds (faster for words, slower for punctuation)
  - Human-like mouse movements for clicks
  - Randomized delays between actions
  - Stealth arguments to hide automation (webdriver override, plugin spoofing, etc.)

## Integration with Other Systems
- The ClaudeBrowserAgent is used by the HybridLLMRouter for task routing
- It can be used by any other agent or script that needs to interact with Claude.ai
- The agent follows the same interface as other browser agents (start_browser, ensure_session, send_prompt, close)

## Troubleshooting
- **Session Invalid**: Run the master seed script again to renew your profile
- **Element Not Found**: Claude.ai may have changed its DOM; update selectors in `claudebrowser_agent.py`
- **Timeouts**: Increase timeouts in the agent if needed (network or response delays)
- **Detection Issues**: Ensure Camoufox is up to date; the agent uses stealth features but updates may be needed

## Dependencies
- patchright
- playwright
- camoufox (should be available via system installation)

## Notes
- The agent defaults to headless=True for automation; set headless=False to watch the browser during testing
- Response extraction looks for Claude's message containers and cleans common disclaimers
- The agent is designed to work with the persistent profile created by the master seed script