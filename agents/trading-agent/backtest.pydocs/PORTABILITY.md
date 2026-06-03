# 🛠️ Infrastructure & Portability Guide

This project is designed for "Zero-Touch Deployment." You can migrate the entire swarm to any Linux/Mac/Windows instance using the Infrastructure Vault.

## 📦 The Infrastructure Vault (`/.infrastructure_vault`)
This hidden directory stores the blueprints of the system's background services. It contains:
- **Manifest**: A map of all required background scripts, cron jobs, and environment variables.
- **Loop Blueprints**: Copies of the `openclaw_multi_loop.sh` and `keep_openclaw_running.sh` to ensure the swarm starts automatically on a new machine.

## 🚀 Migration Procedure
To deploy this swarm on a new machine:
1. **Clone the Repo**: `git clone <repo_url>`
2. **Populate Secrets**: Copy your `.env` file (excluded from git) to the new instance.
3. **Initialize Vault**: Run a bootstrap script (to be developed) that reads `.infrastructure_vault/manifest.json` and:
   - Sets up the required directories.
   - Installs the Python venv and dependencies.
   - Configures the `crontab` for the autonomous loops.
   - Starts the OpenClaw Gateway.

## ☁️ Cloud-First Strategy
- **Logic**: Stored in GitHub.
- **Data/Findings**: Stored in Supabase.
- **Secrets & Vaults**: Synced via the `CloudVaultManager` to Supabase encrypted storage.
- **Session State**: Stored in Persistent Browser Profiles (syncable via the vault).
- **Orchestration**: Handled by the background loops, removing the need for an active SSH session.
