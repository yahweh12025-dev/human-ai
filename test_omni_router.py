#!/usr/bin/env python3
"""
Test script for the Omni-Model LLM Router
"""
import asyncio
import sys
import os

# Add the agents directory to the path
sys.path.append('/home/ubuntu/human-ai/agents')

from hybrid_llm_router import HybridLLMRouter

async def test_router():
    print("🧪 Testing Omni-Model LLM Router...")
    
    # Initialize the router
    router = HybridLLMRouter()
    
    # Test tasks for each model type
    test_tasks = [
        ("What is the latest news about AI?", "perplexity"),  # Should favor Perplexity for search/news
        ("Explain quantum computing in simple terms", "gemini"),  # Should favor Gemini for explanation
        ("Write a Python function to calculate fibonacci numbers", "deepseek"),  # Should favor DeepSeek for code
        ("Create a nuanced analysis of the ethical implications of AI art", "claude"),  # Should favor Claude for nuanced analysis
    ]
    
    for task, expected_model in test_tasks:
        print(f"\n📝 Testing: '{task}'")
        print(f"   Expected: {expected_model}")
        
        # Test the model selection
        selected = await router._should_use_model(task)
        print(f"   Selected: {selected}")
        
        if selected == expected_model:
            print("   ✅ Correct!")
        else:
            print(f"   ⚠️  Expected {expected_model}, got {selected}")
    
    # Test statistics
    stats = router.get_stats()
    print(f"\n📊 Router Stats: {stats}")
    
    # Cleanup
    await router.close()
    print("\n✅ Router test completed!")

if __name__ == "__main__":
    asyncio.run(test_router())