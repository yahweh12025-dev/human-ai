#!/bin/bash
# Autodev: High-Velocity Autonomous Loop with Telegram Alerts

LOG_FILE="/home/ubuntu/human-ai/autodev.log"
ROADMAP_FILE="/home/ubuntu/human-ai/ROADMAP.md"
TELEGRAM_TOKEN="8306402529:AAHs_WPPZv1wsxDEIgU0P0Twc6PRm_8A_xA"
TELEGRAM_CHAT_ID="8412298553"

# Intervals in seconds
INTERVAL_HEARTBEAT=300   # 5 minutes
INTERVAL_HOURLY=600      # 10 minutes
INTERVAL_MAJOR=1200      # 20 minutes

send_telegram_alert() {
    local msg="$1"
    echo "[$(date)] 📢 Telegram Alert: $msg" >> $LOG_FILE
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
         -d "chat_id=${TELEGRAM_CHAT_ID}" \
         -d "text=🚨 *Human-AI Autopilot Alert* 🚨%0A%0A$msg" \
         -d "parse_mode=Markdown" > /dev/null
}

while true; do
    # Sync Plan and Todo Queue
    /home/ubuntu/human-ai/venv/bin/python3 /home/ubuntu/human-ai/plan_aggregator.py >> $LOG_FILE 2>&1
    
    CURRENT_TIME=$(date +%s)

    # 1. Health Check (Gateway)
    if ! pgrep -x "openclaw" > /dev/null; then
        send_telegram_alert "⚠️ OpenClaw Gateway is DOWN. Attempting restart..."
        openclaw gateway start >> $LOG_FILE 2>&1
        sleep 30
    fi

    # 2. Heartbeat (Every 20m)
    if (( CURRENT_TIME - LAST_HEARTBEAT >= INTERVAL_HEARTBEAT )); then
        echo "[$(date)] 💓 HEARTBEAT: Daemon is healthy." >> $LOG_FILE
        LAST_HEARTBEAT=$CURRENT_TIME
    fi

    # 3. Quick Scan (Every 1h)
    if (( CURRENT_TIME - LAST_HOURLY >= INTERVAL_HOURLY )); then
        echo "[$(date)] 🔍 HOURLY SCAN: Checking Roadmap..." >> $LOG_FILE
        LAST_HOURLY=$CURRENT_TIME
    fi

    # 4. Major Development (Every 2h)
    if (( CURRENT_TIME - LAST_MAJOR >= INTERVAL_MAJOR )); then
        echo "[$(date)] 🚀 MAJOR DEVELOPMENT CYCLE STARTING..." >> $LOG_FILE
        
        PROMPT="AUTONOMOUS_DEVELOPMENT_TRIGGER: Review /home/ubuntu/human-ai/ROADMAP.md. Identify the next pending task. Execute it fully. If a decision is needed, decide based on project goals. If a manual /approve or command is needed, log it to /home/ubuntu/human-ai/manual_actions/todo.log and proceed with other tasks if possible."
        
        # We use the openclaw command to trigger the loop
        openclaw agent --agent main --message "$PROMPT" --deliver >> $LOG_FILE 2>&1
        
        if [ $? -ne 0 ]; then
            send_telegram_alert "❌ Autonomous Cycle failed to trigger. Check logs at /home/ubuntu/human-ai/autodev.log"
        fi

        LAST_MAJOR=$CURRENT_TIME
    fi

    sleep 60
done
