#!/bin/bash
# Script to run Nstbrowser agent with proper environment variables

# Set environment variables
export NST_AGENT_DIR="$HOME/.nst-agent"
export NST_TOKEN="8be46d89-2ac7-45b2-acb2-33fc6866e581"

# Run the agent
echo "Starting Nstbrowser agent..."
echo "Agent directory: $NST_AGENT_DIR"
echo "Token: $NST_TOKEN"
echo ""
"/home/yahwehatwork/.local/bin/agent"
