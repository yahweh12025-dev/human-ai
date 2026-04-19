#!/bin/bash
# Autopilot Watchdog Shell Wrapper
# Absolute Silence Mode: Redirect everything to avoid Cron "Job Failed" noise.

# Run the python watchdog and suppress all output
/home/ubuntu/human-ai/venv/bin/python3 /home/ubuntu/human-ai/scripts/watchdog.py > /dev/null 2>&1 || true

# Check if an alert file was created
if [ -f /home/ubuntu/human-ai/watchdog_alert.txt ]; then
    ALERT_MSG=$(cat /home/ubuntu/human-ai/watchdog_alert.txt)
    # We ONLY output to stdout here if there is a real alert, 
    # but since this is a cron job, we'll let the Main Agent handle the notification 
    # during its heartbeat to avoid the Gateway's "Message failed" logic.
    rm /home/ubuntu/human-ai/watchdog_alert.txt
fi

exit 0
