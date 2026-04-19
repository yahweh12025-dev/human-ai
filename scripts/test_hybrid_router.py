#!/usr/bin/env python3
"""
Test script for the Hybrid LLM Router
"""
import asyncio
import os
import sys
sys.path.insert(0, '/home/ubuntu/human-ai')

from agents.hybrid_llm_router import HybridLLMRouter

async def test_router():
    print("🧪 Testing Hybrid LLM Router...")
    
    # Initialize router
    router = HybridLLMRouter(
        gemini_use_chrome_profile=False,  # Use swarm profile for stability
        deepseek_use_browser_profile=True,
        rate_limit_cooldown=60  # 1 minute cooldown for testing
    )
    
    try:
        # Test 1: Simple task (should favor DeepSeek)
        print("\n--- Test 1: Simple coding task ---")
        simple_task = "Write a Python function to add two numbers"
        result1 = await router.route_task(simple_task)
        print(f"Result: {result1['agent']} - {result1['status']}")
        if result1['status'] == 'success':
            print(f"Response preview: {result1['response'][:100]}...")
        
        # Test 2: Complex reasoning task (should favor Gemini)
        print("\n--- Test 2: Complex reasoning task ---")
        complex_task = "Explain the concept of quantum entanglement in simple terms, including its implications for quantum computing"
        result2 = await router.route_task(complex_task)
        print(f"Result: {result2['agent']} - {result2['status']}")
        if result2['status'] == 'success':
            print(f"Response preview: {result2['response'][:100]}...")
        
        # Test 3: Another simple task
        print("\n--- Test 3: Another simple task ---")
        another_simple = "What is 2+2?"
        result3 = await router.route_task(another_simple)
        print(f"Result: {result3['agent']} - {result3['status']}")
        if result3['status'] == 'success':
            print(f"Response preview: {result3['response'][:100]}...")
        
        # Show stats
        print("\n--- Router Statistics ---")
        stats = router.get_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await router.close()

if __name__ == "__main__":
    asyncio.run(test_router())
