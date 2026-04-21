#!/usr/bin/env python3
"""
Test script for the enhanced DeepSeek Browser Agent with session persistence improvements.
"""

import asyncio
import sys
import os
sys.path.append('/home/ubuntu/human-ai/core/agents/researcher')

from deepseek_browser_agent_enhanced import DeepSeekBrowserAgent

async def test_enhanced_agent():
    """Test the enhanced browser agent with session persistence."""
    print("🧪 Testing Enhanced DeepSeekBrowserAgent...")
    
    # Test 1: Basic initialization and login check
    print("\n--- Test 1: Initialization and Login Check ---")
    agent = DeepSeekBrowserAgent(keep_browser_open=False, alert_on_captcha=False)
    try:
        await agent.start_browser()
        login_result = await agent.login()
        print(f"Login result: {login_result}")
        
        if login_result:
            # Test 2: Simple prompt if logged in
            print("\n--- Test 2: Simple Prompt ---")
            response = await agent.prompt("Say 'Hello World' in exactly 2 words.")
            print(f"Response: {response}")
        else:
            print("⚠️ Not logged in. Skipping prompt test.")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await agent.close()
    
    # Test 3: Test with alert_on_captcha (non-interactive mode)
    print("\n--- Test 3: Testing with CAPTCHA Alert Mode ---")
    agent2 = DeepSeekBrowserAgent(keep_browser_open=True, alert_on_captcha=True)
    try:
        await agent2.start_browser()
        login_result2 = await agent2.login()
        print(f"Login result with alert mode: {login_result2}")
        
        if login_result2:
            print("✅ Successfully logged in with alert mode!")
            # Try a simple prompt
            response = await agent2.prompt("What is 2+2? Answer with just the number.")
            print(f"Math response: {response}")
        else:
            print("ℹ️ Either not logged in or CAPTCHA detected (as expected in alert mode)")
            
    except Exception as e:
        print(f"❌ Error during alert mode test: {e}")
    finally:
        # Don't close immediately to allow for potential manual intervention if needed
        await agent2.close()
        
    print("\n🏁 Enhanced agent testing completed.")

if __name__ == "__main__":
    asyncio.run(test_enhanced_agent())