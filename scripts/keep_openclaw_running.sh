#!/bin/bash
# Script to ensure OpenClaw Gateway is running in the background
while true; do
    if ! pgrep -f "openclaw gateway" > /dev/null; then
        echo "$(date): OpenClaw not running. Starting..." >> /home/ubuntu/openclaw_watchdog.log
        openclaw gateway start
    fi
    sleep 60
done
