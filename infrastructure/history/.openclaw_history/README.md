# 📜 OpenClaw History & Context Cache

This hidden directory stores the distilled essence of all conversations, decisions, and technical breakthroughs.

## 🎯 Purpose
To prevent "amnesia" during session restarts or token limit resets. Instead of re-reading the entire README or BOOTSTRAP, the agents load the latest **Cached Context** from here.

## 📂 Structure
- `/summaries`: Date-stamped summaries of chat sessions.
- `/decisions`: Log of "Why we did X instead of Y" to avoid repeating mistakes.
- `/context_cache`: The most recent "State of the Swarm" file used for instant bootstrapping.

## 🛡️ Security Protocol
**STRICT PROHIBITION:** The following must NEVER be written to this directory or pushed to GitHub:
- API Keys (OpenRouter, Groq, Google, etc.)
- Passwords/Credentials
- IP Addresses / Hostnames
- Personal Emails/Phone Numbers
- `.env` file contents

All sensitive data must be replaced with placeholders (e.g., `[API_KEY_HIDDEN]`).
