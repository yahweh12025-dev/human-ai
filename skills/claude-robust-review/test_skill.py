#!/usr/bin/env python3
"""
Test script to verify the claude-robust-review skill works correctly.
This tests both the hybrid router and Botasaurus fallback methods.
"""

import asyncio
import json
import sys
import os

# Add the human-ai directory to path
sys.path.insert(0, '/home/yahwehatwork/human-ai')

async def test_skill_components():
    """Test that all components of the skill can be imported and initialized."""
    print("🧪 Testing Claude Robust Review Skill Components")
    print("=" * 50)
    
    # Test 1: Check if hybrid router is available
    print("\n1. Testing Hybrid LLM Router availability...")
    try:
        from core.agents.hybrid_llm_router import HybridLLMRouter
        router = HybridLLMRouter()
        print("   ✅ HybridLLMRouter imported successfully")
        await router.close()
    except Exception as e:
        print(f"   ❌ Failed to import HybridLLMRouter: {e}")
    
    # Test 2: Check if Botasaurus is available
    print("\n2. Testing Botasaurus availability...")
    try:
        sys.path.insert(0, '/home/yahwehatwork/human-ai/botasaurus')
        sys.path.insert(0, '/home/yahwehatwork/.local/lib/python3.11/site-packages')
        from botasaurus.browser import browser, Driver
        print("   ✅ Botasaurus imported successfully")
    except Exception as e:
        print(f"   ❌ Failed to import Botasaurus: {e}")
    
    # Test 3: Check if trading agent file exists
    print("\n3. Testing trading agent file accessibility...")
    trading_agent_path = '/home/yahwehatwork/human-ai/agents/trading-agent/trading_agent.py'
    if os.path.exists(trading_agent_path):
        print(f"   ✅ Trading agent file found at {trading_agent_path}")
        # Try to read a small portion
        try:
            with open(trading_agent_path, 'r') as f:
                first_line = f.readline().strip()
                print(f"   📄 First line: {first_line[:50]}...")
        except Exception as e:
            print(f"   ⚠️  Could not read file: {e}")
    else:
        print(f"   ❌ Trading agent file NOT found at {trading_agent_path}")
    
    # Test 4: Check if skill scripts exist
    print("\n4. Testing skill script availability...")
    scripts = [
        '/home/yahwehatwork/human-ai/skills/claude-robust-review/scripts/seed_claude_session.py',
        '/home/yahwehatwork/human-ai/skills/claude-robust-review/scripts/claude_review_botasaurus.py',
        '/home/yahwehatwork/human-ai/skills/claude-robust-review/scripts/robust_claude_access.py'
    ]
    
    for script in scripts:
        if os.path.exists(script):
            print(f"   ✅ {os.path.basename(script)}")
        else:
            print(f"   ❌ {os.path.basename(script)} - NOT FOUND")
    
    print("\n" + "=" * 50)
    print("🧪 Component testing complete")

async def test_robust_access_with_dummy_prompt():
    """Test the robust access function with a simple, safe prompt."""
    print("\n🧪 Testing Robust Claude Access with Dummy Prompt")
    print("=" * 50)
    
    # Import the robust access function
    try:
        sys.path.insert(0, '/home/yahwehatwork/human-ai/skills/claude-robust-review/scripts')
        from robust_claude_access import robust_claude_access
        
        # Use a simple, non-controversial prompt that should work
        test_prompt = """
        Please provide a brief explanation of what a moving average is in trading,
        in no more than 3 sentences. This is a test to verify the Claude access
        system is working correctly.
        """
        
        print("📝 Sending test prompt to Claude...")
        print(f"   Prompt: {test_prompt[:100]}...")
        
        result = await robust_claude_access(test_prompt, "This is a system test.")
        
        print("\n📊 Result:")
        print(json.dumps(result, indent=2))
        
        if result.get("status") == "success":
            print("\n✅ Test PASSED - Claude access is working!")
            print(f"   Method used: {result.get('method', 'unknown')}")
            if result.get('fallback_used'):
                print("   ⚠️  Note: Fallback method was used")
        else:
            print("\n❌ Test FAILED - Claude access encountered issues")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"\n💥 Test script error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting Claude Robust Review Skill Tests")
    
    # Run component tests
    asyncio.run(test_skill_components())
    
    # Ask user if they want to run the live test
    print("\n" + "=" * 50)
    response = input("Do you want to run a live test with Claude? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        asyncio.run(test_robust_access_with_dummy_prompt())
    else:
        print("⏭️  Skipping live test. Remember to:")
        print("   1. Seed your Claude session with: export BROWSER_HEADLESS=false && python3 skills/claude-robust-review/scripts/seed_claude_session.py")
        print("   2. Then run tests with BROWSER_HEADLESS=true")
    
    print("\n🏁 Testing complete")