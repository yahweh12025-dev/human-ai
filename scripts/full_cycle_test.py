import asyncio
import os
from core.agents.ant_farm.orchestrator import AntFarmOrchestrator

async def run_test():
    print("🚀 Starting End-to-End Integration Test...")
    orch = AntFarmOrchestrator()
    
    # Task: Create a simple helper utility in the repo to verify the full loop
    # Retrieve -> Research -> Implement (via Kilo-Code) -> Verify (Sandbox)
    task = {
        "description": "Create a new file at /home/yahwehatwork/human-ai/core/utils/swarm_health_check.py that contains a function 'check_system()' which prints 'System Healthy'. This will test the autonomous apply and verify loop."
    }
    
    print(f"Target Goal: {task['description']}")
    result = await orch.execute_pipeline(task)
    
    print("\n--- FINAL TEST RESULT ---")
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        print(f"Verification Output: {result.get('verification')}")
        print("✅ SUCCESS: The swarm autonomously researched, implemented, and verified the task.")
    else:
        print(f"❌ FAILURE: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(run_test())
