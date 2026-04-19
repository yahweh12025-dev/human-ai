#!/bin/bash
# =============================================================================
# BASIC WATCHDOG HEALTH MONITOR
# =============================================================================

# Configuration
LOG_FILE="/home/ubuntu/human-ai/watchdog_health.log"
ALLOWED_USER_ID="8412298553"

# Load environment
if [[ -f "/home/ubuntu/human-ai/.env" ]]; then
    source "/home/ubuntu/human-ai/.env"
fi

# Telegram bot tokens
OPENCLAW_BOT_TOKEN="8785963819:AAEMPoEOJzjlbpLhWjuu_jKS9lgU0vGbKJM"
HERMES_BOT_TOKEN="8638235036:AAFWMPcA0rzu8PtpsxSz47OMwL8_V6evEJs"
SWARM_BOT_TOKEN="${SWARM_BOT_TOKEN:-}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    if [[ "$2" == "verbose" ]]; then
        echo "$1"
    fi
}

send_alert() {
    local message="$1"
    local type="$2"
    
    local emoji=""
    case "$type" in
        "info") emoji="ℹ️";;
        "warning") emoji="⚠️";;
        "error") emoji="❌";;
        "critical") emoji="🚨";;
    esac
    
    local formatted="${emoji} *Watchdog Alert*\n\n${message}"
    
    # Try bots in order: Swarm -> Hermes -> OpenClaw
    for token in "$SWARM_BOT_TOKEN" "$HERMES_BOT_TOKEN" "$OPENCLAW_BOT_TOKEN"; do
        if [[ -n "$token" && "$token" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
            url="https://api.telegram.org/bot${token}/sendMessage"
            data="chat_id=${ALLOWED_USER_ID}&text=$(printf '%s' "$formatted" | jq -sRr @uri)&parse_mode=MarkDown"
            
            if response=$(curl -s -X POST "$url" -d "$data" 2>/dev/null); then
                if echo "$response" | grep -q '"ok":true'; then
                    log "Alert sent via Telegram" "verbose"
                    return 0
                fi
            fi
        fi
    done
    
    log "Failed to send Telegram alert" "verbose"
    return 1
}

case "$1" in
    --test-alerts)
        send_alert "🧪 *Test Alert*\nWatchdog monitoring system is operational!\n\nTime: $(date)" "info"
        send_alert "🧪 *Test Warning*\nThis is a test warning" "warning"
        send_alert "🧪 *Test Error*\nThis is a test error" "error"
        echo "Test alerts sent"
        ;;
    *)
        echo "Usage: $0 [--test-alerts]"
        ;;
esac
