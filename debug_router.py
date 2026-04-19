#!/usr/bin/env python3
"""
Debug script for the Omni-Model LLM Router scoring
"""
import asyncio
import sys
import os

# Add the agents directory to the path
sys.path.append('/home/ubuntu/human-ai/agents')

from hybrid_llm_router import HybridLLMRouter

async def debug_scoring():
    print("🔍 Debugging Omni-Model LLM Router scoring...")
    
    # Initialize the router
    router = HybridLLMRouter()
    
    # Test task that was misrouted
    task = "Write a Python function to calculate fibonacci numbers"
    print(f"\n📝 Testing: '{task}'")
    
    # Show the scoring
    gemini, deepseek, perplexity, claude = router._assess_task_complexity(task)
    print(f"   Scores -> Gemini: {gemini}, DeepSeek: {deepseek}, Perplexity: {perplexity}, Claude: {claude}")
    
    # Show which keywords matched
    task_lower = task.lower()
    print(f"   Task (lower): {task_lower}")
    
    print("   Gemini keyword matches:", [kw for kw in router.gemini_favored_keywords if kw in task_lower])
    print("   DeepSeek keyword matches:", [kw for kw in router.deepseek_favored_keywords if kw in task_lower])
    print("   Perplexity keyword matches:", [kw for kw in router.perplexity_favored_keywords if kw in task_lower])
    print("   Claude keyword matches:", [kw for kw in router.claude_favored_keywords if kw in task_lower])
    
    # Show length and other heuristics
    print(f"   Length: {len(task)} (>{100}? {len(task) > 100}, <{30}? {len(task) < 30})")
    print(f"   Question marks: {task.count('?')}")
    print(f"   Code chars: {[c for c in ['{', '}', '()', ';', '==', '!='] if c in task]}")
    
    # Show final decision
    selected = await router._should_use_model(task)
    print(f"   Selected model: {selected}")
    
    # Cleanup
    await router.close()

if __name__ == "__main__":
    asyncio.run(debug_scoring())