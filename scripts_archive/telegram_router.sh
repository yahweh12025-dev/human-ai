#!/bin/bash
# Telegram Control Router for Human-AI Swarm

# This script is triggered by OpenClaw on every inbound message.
# It routes the message to the correct agent based on keywords.

MESSAGE="$1"
USER_ID="$2"

echo "[$(date)] Routing message: $MESSAGE from $USER_ID" >> /home/ubuntu/human-ai/routing.log

if [[ "$MESSAGE" == *"research"* ]]; then
    TOPIC=$(echo "$MESSAGE" | sed 's/.*research (on )*//i')
    echo "🚀 Routing to Researcher: $TOPIC" >> /home/ubuntu/human-ai/routing.log
    openclaw agent --agent main --message "TRIGGER_RESEARCH: $TOPIC"
elif [[ "$MESSAGE" == *"status"* ]]; then
    echo "📊 Routing to Status Check" >> /home/ubuntu/human-ai/routing.log
    openclaw agent --agent main --message "PROVIDE_SYSTEM_STATUS"
elif [[ "$MESSAGE" == *"autopilot"* ]]; then
    echo "🤖 Routing to Autopilot Control" >> /home/ubuntu/human-ai/routing.log
    /home/ubuntu/human-ai/run-autopilot.sh
fi
