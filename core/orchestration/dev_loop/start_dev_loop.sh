#!/bin/bash
# Start the autonomous development loop if not already running

# PID file location
PID_FILE="/tmp/hermes_dev_loop.pid"
LOG_FILE="/home/yahwehatwork/human-ai/autonomous_dev/dev_loop.log"

# Function to start the loop
start_loop() {
    echo "🚀 Starting autonomous development loop at $(date)" >> "$LOG_FILE"
    cd /home/yahwehatwork/human-ai/autonomous_dev
    nohup python3 dev_loop_coordinator.py >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "✅ Development loop started with PID: $!" >> "$LOG_FILE"
}

# Check if PID file exists and process is running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "💓 Development loop is already running (PID: $PID)" >> "$LOG_FILE"
        exit 0
    else
        echo "⚠️  PID file exists but process is not running. Cleaning up." >> "$LOG_FILE"
        rm -f "$PID_FILE"
    fi
fi

# Start the loop
start_loop