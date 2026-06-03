#!/bin/bash
LOG="/home/yahweh1_2025/human-ai/data/logs/obsidian_sync.log"
VAULT="/home/yahweh1_2025/obsidian-vault"
echo "[$(date)] Starting sync..." >> "$LOG"
rclone sync "$VAULT" gdrive:backups/obsidian --log-level INFO >> "$LOG" 2>&1
if [ $? -eq 0 ]; then
    echo "[$(date)] Sync completed successfully" >> "$LOG"
else
    echo "[$(date)] ERROR: Sync failed!" >> "$LOG"
fi
