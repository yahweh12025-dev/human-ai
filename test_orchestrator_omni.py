#!/usr/bin/env python3
"""
Integration test for AntFarmOrchestrator with Omni-Router
"""
import asyncio
import sys
import os

# Add necessary paths
sys.path.append('/home/ubuntu/human-ai')
sys.path.append('/home/ubuntu/human-ai/agents')

from agents.ant_farm.orchestrator import AntFarmOrchestrator

async def test_orchestrator_routing():
    print("🧪 Testing AntFarmOrchestrator Omni-Routing...")
    
    orch = AntFarmOrchestrator()
    
    # Task that should trigger Perplexity via the Omni-Router
    # (current events/latest news)
    task = {"description": "What are the latest breakthroughs in room-temperature superconductors as of this month?"}
    print(f"\n📝 Testing Research Task: {task['description']}")
    
    try:
        result = await orch.execute_pipeline(task)
        print(f"   Pipeline Result Status: {result['status']}")
        if result['status'] == 'success':
            print(f"   ✅ Pipeline completed successfully!")
    except Exception as e:
        print(f"   ❌ Pipeline failed: {e}")
    
    # Cleanup
    await orch.router.close()
    print("\n✅ Orchestrator test completed!")

if __name__ == "__main__":
    asyncio.run(test_orchestrator_routing())