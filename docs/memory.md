# Hermes Agent Memory Archive

This file contains the full persistent memory that was previously stored in the agent's working memory. It has been archived to reduce memory usage to target levels.

## Memory Contents (Archived)

### Core User Preferences
- User prefers persistent Chrome/Chromium profile at `~/.browser-profile/google` for Google account login
- User wants Claude.ai access for the researcher agent via Cloudflare bypass

### System Status
- Cloudflare bypass service: ACTIVE & OPERATIONAL
  - Location: `/home/yahwehatwork/CloudflareBypassForScraping`
  - Endpoint: `http://127.0.0.1:8000/cookies`
  - Function: Successfully retrieving `cf_clearance` cookies for Claude.ai
  - Verification: Service is responding with cookies

- Browser Profile Status:
  - Path: `/home/yahwehatwork/.browser-profile/google`
  - Status: Directory exists but may be locked by other processes when launching with persistent context

### Trading Agent
- Directory cleaned and pushed to GitHub (commit c2fb11d)
- Configured for Binance testnet execution
- Issue: Experiencing authentication issues with provided API keys

### Researcher Agent
- Currently DeepSeek-focused
- User desires Claude access via Cloudflare bypass
- Integrated with DeepSeek Browser Agent, OpenClaw Gateway, Supabase, and Graphify
- Uses persistent profiles and human-like behavior hardening

### Swarm Health Bot (@Swarm26_bot)
- Added `/save` command in `human-ai/core/agents/swarm_health_bot/swarm_health_bot.py`
- Saves current swarm state to `/home/ubuntu/human-ai/swarm_state_save.json` with timestamp, log status, and recent entries
- Help text updated to include: `/save - Save current swarm state to a file`

### Skills & Tools
- `json-config-patching` skill: Created for safely modifying JSON configuration files using unique context matching with Hermes patch tool
- Addresses challenge of modifying files like `openclaw.json` where simple string replacement could cause unintended changes due to duplicate patterns

### Technical Implementation
Cloudflare bypass integrated into:
1. Claude Browser Agent (`/home/yahwehatwork/human-ai/core/agents/claude/claude_agent.py`)
2. Perplexity Browser Agent (`/home/yahwehatwork/human-ai/core/agents/perplexity/perplexity_agent.py`)
3. DeepSeek Browser Agent (already had imports in researcher agent)

Integration pattern:
- Import CloudflareBypassManager from utils
- Fetch cookies and user agent for target URL
- Inject cookies into browser context via `add_cookies()`
- Optional user agent update for better bypass effectiveness

### Session History Notes
Previous sessions involved:
- Setting up autonomous AI agents and multi-agent workflows
- Configuring persistent browser profiles
- Testing Cloudflare bypass services
- Developing trading agent functionality
- Creating researcher agent with multi-platform search capabilities
- Implementing swap health bot commands
- Refactoring memory management systems

Last updated: $(date)