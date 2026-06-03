#!/usr/bin/env bash
# Sync Obsidian vault to GDrive — single backup, no timestamped copies
# Policy: rclone sync (overwrites in place), never rclone copy with timestamps
# Schedule: every 6 hours via cron

VAULT_SRC="$HOME/human-ai/data/obsidian"
GDRIVE_DST="gdrive:backups/obsidian"
LOG="$HOME/human-ai/data/logs/obsidian_sync.log"

mkdir -p "$HOME/human-ai/data/logs"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Obsidian vault sync..." | tee -a "$LOG"

if ! rclone listremotes 2>/dev/null | grep -q "gdrive:"; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: gdrive remote not configured" | tee -a "$LOG"
    exit 1
fi

RCLONEIGNORE="$VAULT_SRC/.rcloneignore"
EXCLUDE_ARGS=(
    "--exclude" "**/__pycache__/**"
    "--exclude" "**/*.pyc"
    "--exclude" "**/.venv/**"
    "--exclude" "HumanAI/data/**"
    "--exclude" "HumanAI/agents/**"
    "--exclude" "HumanAI/core/**"
    "--exclude" "HumanAI/apps/**"
    "--exclude" "HumanAI/scripts/**"
    "--exclude" "HumanAI/infrastructure/**"
    "--exclude" "HumanAI/.env"
    "--exclude" "HumanAI/*.py"
    "--exclude" "HumanAI/*.log"
    "--exclude" "HumanAI/config/**"
)

if [ -f "$RCLONEIGNORE" ]; then
    EXCLUDE_ARGS+=("--exclude-from" "$RCLONEIGNORE")
fi

rclone sync "$VAULT_SRC" "$GDRIVE_DST" \
    "${EXCLUDE_ARGS[@]}" \
    --log-level INFO \
    2>&1 | tee -a "$LOG"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Vault sync complete → $GDRIVE_DST" | tee -a "$LOG"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: vault sync failed" | tee -a "$LOG"
    exit 1
fi
