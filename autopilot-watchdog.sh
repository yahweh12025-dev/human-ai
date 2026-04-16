#!/bin/bash
# Autopilot Watchdog Shell Wrapper
# Only outputs on critical failure.

# Run the python watchdog
/home/ubuntu/human-ai/venv/bin/python3 /home/ubuntu/human-ai/scripts/watchdog.py

# Check if an alert file was created
if [ -f /home/ubuntu/human-ai/watchdog_alert.txt ]; then
    ALERT_MSG=$(cat /home/ubuntu/human-ai/watchdog_alert.txt)
    echo "🚨 CRITICAL ERROR DETECTED BY WATCHDOG:"
    echo "$ALERT_MSG"
    # Clean up alert file after notifying
    rm /home/ubuntu/human-ai/watchdog_alert.txt
fi
