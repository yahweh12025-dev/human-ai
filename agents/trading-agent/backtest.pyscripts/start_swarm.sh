#!/bin/bash
# Human-AI Swarm - Start All Services
# Usage: bash scripts/start_swarm.sh

PROJECT_ROOT="/home/yahwehatwork/human-ai"
cd "$PROJECT_ROOT"

echo "=========================================="
echo " Human-AI Swarm - Starting Services"
echo "=========================================="

# Load environment
export $(grep -v '^#' .env | xargs) 2>/dev/null

# 1. Start Mission Control (port 10000)
echo -n "  Mission Control... "
if lsof -i :10000 >/dev/null 2>&1; then
    echo "ALREADY RUNNING"
else
    nohup python3 core/apps/dashboard/mission_control.py > data/logs/mission_control.log 2>&1 &
    echo "STARTED (PID: $!)"
fi

# 2. Verify integrations
echo -n "  Integrations... "
python3 -c "
from core.integrations.verify_all_integrations import run_all_verifications
r = run_all_verifications()
s = r['summary']
print(f'{s[\"connected\"]} connected, {s[\"configured\"]} configured')
" 2>/dev/null

# 3. LLM Router check
echo -n "  LLM Router... "
python3 -c "
from core.llm_router import test_routing
test_routing()
" 2>/dev/null | grep -c "KEY_PRESENT" | xargs -I{} echo "{} agents configured"

echo ""
echo "=========================================="
echo " Services Ready"
echo "=========================================="
echo "  Dashboard: http://localhost:10000"
echo "  Auto Mode: python3 core/orchestration/automode.py"
echo "  Skills:    python3 skills/agent_skill_registry.py"
echo "=========================================="
