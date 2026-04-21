#!/bin/bash
# OpenClaw Autonomous Mode - RESILIENT VERSION
LOG_FILE="/home/ubuntu/openclaw_auto_loop.log"
REGULAR_INTERVAL=900
HOURLY_INTERVAL=3600

log_message() {
    local message="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $message" >> "$LOG_FILE"
    echo "[$timestamp] $message"
}

log_message "🚀 OpenClaw Autonomous Mode Started - Resilient Version"

last_regular_cycle=0
last_hourly_update=0

while true; do
    current_time=$(date +%s)
    if [[ $((current_time - last_regular_cycle)) -ge $REGULAR_INTERVAL ]]; then
        log_message "🔄 Starting Cycle - Triage → Fix → Test → Push"
        
        # Triage - Check root then archive
        if [ -f "/home/ubuntu/human-ai/triage_errors.py" ]; then
            /home/ubuntu/human-ai/venv/bin/python3 /home/ubuntu/human-ai/triage_errors.py >> "$LOG_FILE" 2>&1 || log_message "⚠️ Triage had issues"
        elif [ -f "/home/ubuntu/human-ai/scripts_archive/triage_errors.py" ]; then
            /home/ubuntu/human-ai/venv/bin/python3 /home/ubuntu/human-ai/scripts_archive/triage_errors.py >> "$LOG_FILE" 2>&1 || log_message "⚠️ Triage had issues"
        else
            log_message "⚠️ triage_errors.py not found anywhere - skipping"
        fi
        
        # Tests - Check root then archive
        if [ -f "/home/ubuntu/human-ai/test_agents.py" ]; then
            /home/ubuntu/human-ai/venv/bin/python3 /home/ubuntu/human-ai/test_agents.py >> "$LOG_FILE" 2>&1 || log_message "⚠️ Tests had issues"
        elif [ -f "/home/ubuntu/human-ai/scripts_archive/test_agents.py" ]; then
            /home/ubuntu/human-ai/venv/bin/python3 /home/ubuntu/human-ai/scripts_archive/test_agents.py >> "$LOG_FILE" 2>&1 || log_message "⚠️ Tests had issues"
        else
            log_message "⚠️ test_agents.py not found anywhere - skipping"
        fi
        
        # Continuous Improvement
        if [ -f "/home/ubuntu/human-ai/continuous_improvement.py" ]; then
            /home/ubuntu/human-ai/venv/bin/python3 /home/ubuntu/human-ai/continuous_improvement.py >> "$LOG_FILE" 2>&1 || log_message "⚠️ Improvement had issues"
        else
            log_message "ℹ️ Continuous improvement script not found - skipping"
        fi
        
        # Sync
        if cd /home/ubuntu/human-ai && git add . && git commit -m "Auto-loop improvement: $(date)" && git push origin main >> "$LOG_FILE" 2>&1; then
            log_message "✅ GitHub sync completed successfully"
        else
            log_message "❌ GitHub sync had issues"
        fi
        
        last_regular_cycle=$current_time
        log_message "😴 Sleeping for 15 minutes..."
    fi
    
    if [[ $((current_time - last_hourly_update)) -ge $HOURLY_INTERVAL ]]; then
        log_message "📊 Hourly Status Update: $(date)"
        last_hourly_update=$current_time
    fi
    sleep 30
done
