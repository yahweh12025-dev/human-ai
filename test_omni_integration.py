#!/usr/bin/env python3
"""
Integration test for the Omni-Model LLM Router with actual task execution
"""
import asyncio
import sys
import os

# Add the agents directory to the path
sys.path.append('/home/ubuntu/human-ai/agents')

from hybrid_llm_router import HybridLLMRouter

async def test_integration():
    print("🔧 Testing Omni-Model LLM Router integration...")
    
    # Initialize the router
    router = HybridLLMRouter()
    
    # Test a simple task that should work without complex browser interactions
    # We'll use a task that's likely to route to DeepSeek (coding) but keep it simple
    test_task = "What is 2+2?"
    print(f"\n📝 Testing simple task: '{test_task}'")
    
    try:
        result = await router.route_task(test_task)
        print(f"   Result: {result}")
        
        if result.get("status") == "success":
            print(f"   ✅ Success! Used {result.get('agent')} agent")
            print(f"   Response: {result.get('response', '')[:100]}...")
        else:
            print(f"   ❌ Error: {result.get('error')}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test statistics
    stats = router.get_stats()
    print(f"\n📊 Router Stats: {stats}")
    
    # Cleanup
    await router.close()
    print("\n✅ Integration test completed!")

if __name__ == "__main__":
    asyncio.run(test_integration())