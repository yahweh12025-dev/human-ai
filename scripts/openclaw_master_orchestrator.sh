#!/bin/bash
# Master Orchestrator to launch all specialized loops

# Stop old loops
pkill -f "core_research_loop.sh"
pkill -f "error_resolution_loop.sh"
pkill -f "skill_improvement_loop.sh"
pkill -f "feature_dev_loop.sh"

# Launch New Loops
nohup /home/ubuntu/human-ai/loops/core_research_loop.sh > /dev/null 2>&1 &
nohup /home/ubuntu/human-ai/loops/error_resolution_loop.sh > /dev/null 2>&1 &
nohup /home/ubuntu/human-ai/loops/skill_improvement_loop.sh > /dev/null 2>&1 &
nohup /home/ubuntu/human-ai/loops/feature_dev_loop.sh > /dev/null 2>&1 &

echo "🚀 All Swarm Loops launched in background."
