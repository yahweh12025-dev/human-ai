#!/bin/bash
# Dashboard API Watchdog
# Ensures the API bridge stays alive for local testing and verification.

export PYTHONPATH=$PYTHONPATH:/home/ubuntu/human-ai
VENV_PATH="/home/ubuntu/human-ai/venv/bin/python3"
API_PATH="/home/ubuntu/human-ai/dashboard_api.py"

echo "🚀 Starting Swarm Command Center API Watchdog..."

while true; do
    echo "[$(date)] Starting API Server..."
    $VENV_PATH $API_PATH
    echo "[$(date)] API Server crashed or was killed. Restarting in 5 seconds..."
    sleep 5
done
