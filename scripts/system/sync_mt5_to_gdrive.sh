#!/bin/bash
LOG="/home/yahweh1_2025/human-ai/data/logs/mt5_sync.log"
MT5_DIR="/home/yahweh1_2025/mt5_node"
echo "[$(date)] Starting MT5 node sync..." >> "$LOG"
# Sync only root-level files (not trading_workspace/ - too large, owned by container user 911)
for f in "$MT5_DIR"/*; do
  [ -f "$f" ] && rclone copy "$f" "gdrive:backups/mt5_node/" --log-level INFO >> "$LOG" 2>&1
done
echo "[$(date)] MT5 node root files synced" >> "$LOG"
