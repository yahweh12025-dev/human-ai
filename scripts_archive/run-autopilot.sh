#!/bin/bash
# run-autopilot.sh - Manually trigger the autonomous cycle

LOG_FILE="/home/ubuntu/human-ai/autodev.log"
# UPDATED PROMPT: Explicitly instructs the agent to check the todo-management list
PROMPT="AUTONOMOUS_DEVELOPMENT_TRIGGER: 1. Check the todo-management list using 'todo.sh entry list'. 2. If pending tasks exist, pick the highest priority one and execute it. 3. Otherwise, review /home/ubuntu/human-ai/ROADMAP.md and identify the next pending goal. Execute it fully. 4. If a decision is needed, decide based on project goals. 5. If a manual /approve or command is needed, log it to /home/ubuntu/human-ai/manual_actions/todo.log and use the notifier skill to alert the user."

echo "🚀 Triggering Autonomous Cycle via System Event..."
openclaw system event --text "$PROMPT"

echo "📺 Streaming output (Press Ctrl+C to stop watching, the agent will keep working)..."
tail -f $LOG_FILE
