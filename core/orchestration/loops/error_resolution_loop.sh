#!/bin/bash
# Loop 2: Error Resolution & Triage
while true; do
    echo "$(date): [ERROR] Running Triage..." >> /home/ubuntu/openclaw_errors.log
    /home/ubuntu/human-ai/venv/bin/python3 /home/ubuntu/human-ai/triage_errors.py >> /home/ubuntu/openclaw_errors.log 2>&1
    # If critical errors exist, the Builder agent is triggered to fix them
    sleep 900
done
