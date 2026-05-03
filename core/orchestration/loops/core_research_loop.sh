#!/bin/bash
# Loop 1: Core Research & DeepSeek Recovery
while true; do
    echo "$(date): [CORE] Testing DeepSeek Agent..." >> /home/ubuntu/openclaw_core.log
    /home/ubuntu/human-ai/venv/bin/python3 /home/ubuntu/human-ai/test_agents.py >> /home/ubuntu/openclaw_core.log 2>&1
    sleep 1800
done
