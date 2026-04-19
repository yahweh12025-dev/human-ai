#!/bin/bash
# autopilot-watch.sh - Real-time Mirror for the Autonomous Swarm

SESSION_NAME="autopilot_mirror"
LOG_FILE="/home/ubuntu/human-ai/autodev.log"

# 1. Create the log file if it doesn't exist
touch $LOG_FILE

# 2. Start a detached tmux session if it doesn't exist
tmux has-session -t $SESSION_NAME 2>/dev/null

if [ $? != 0 ]; then
    echo "🚀 Starting Autopilot Mirror Session..."
    # Launch tmux and run a split view
    tmux new-session -d -s $SESSION_NAME "tail -f $LOG_FILE"
    tmux split-window -h "watch -n 60 'bash ~/.openclaw/workspace/skills/todo-management/scripts/todo.sh entry list'"
    tmux select-pane -t 0
fi

# 3. Attach to the session
echo "----------------------------------------------------------------------"
echo "📺 ATTACHING TO AUTOPILOT MIRROR"
echo "To EXIT and return to the terminal: Press [Ctrl+B] then [D]"
echo "----------------------------------------------------------------------"
tmux attach-session -t $SESSION_NAME
