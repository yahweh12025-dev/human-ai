#!/usr/bin/env bash
# Auto-heal OpenClaw gateway config and restart service

LOG_FILE="/home/ubuntu/human-ai/logs/gateway-healer.log"

log() {
    echo "[$(date -u +'%Y-%m-%d %H:%M:%S UTC')] $*" | tee -a "$LOG_FILE"
}

log "🔍 Detected invalid OpenClaw config – running doctor..."
openclaw doctor --fix >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    log "✅ Doctor completed successfully."
else
    log "❌ Doctor failed – check $LOG_FILE"
    exit 1
fi

log "🔁 Restarting OpenClaw gateway..."
openclaw gateway restart >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    log "✅ Gateway restarted successfully."
else
    log "❌ Gateway restart failed – check $LOG_FILE"
    exit 1
fi

log "✅ Heal cycle complete."