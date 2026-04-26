# Skills Inventory

This file lists available skills that agents can load and use.

## claude-cloudflare-bypass
- **Category**: devops
- **Description**: Automates obtaining a Cloudflare clearance cookie for Claude using the CloudflareBypassForScraping repository and injects it into a Selenium session with a persistent Chrome profile. After running this skill, any Selenium (or Playwright) script that uses the same `--user-data-dir=/home/yahwehatwork/.browser-profile/google` will be able to access https://claude.ai/chat without encountering the Cloudflare "Just a moment…" challenge.
- **Location**: `devops/claude-cloudflare-bypass` (skill path relative to ~/.hermes/skills/)
- **Skill file**: `/home/yahwehatwork/.hermes/skills/devops/claude-cloudflare-bypass/SKILL.md`
- **How to use**: Load with `skill_view('claude-cloudflare-bypass')` or follow the steps in the skill to start the bypass server, fetch a cookie, and inject it into your persistent Chrome profile.

## How to load a skill
From within a Hermes session, you can load a skill to see its full content:
```
skill_view <skill-name>
```
Example:
```
skill_view claude-cloudflare-bypass
```

## Adding new skills
New skills are created with the `skill_manage` tool. See the skill `skill_manage` documentation for details.
