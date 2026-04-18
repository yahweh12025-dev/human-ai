
import asyncio
import sys
sys.path.insert(0, '/home/ubuntu/human-ai')
from agents.researcher.researcher_agent import DeepSeekBrowserAgent

async def test_browser_interaction():
    print("=== Testing DeepSeekBrowserAgent Browser Interaction ===")
    agent = DeepSeekBrowserAgent()
    
    try:
        print("1. Starting browser...")
        await agent.start_browser()
        print("   ✓ Browser started")
        
        print("2. Checking login/session...")
        logged_in = await agent.login()
        print(f"   Login status: {'✓ Logged in' if logged_in else '⚠️ Session may need login'}")
        
        print("3. Sending test prompt...")
        test_prompt = "Say 'Hello from Human-AI Swarm test' and nothing else."
        response = await agent.prompt(test_prompt)
        print(f"   Prompt sent: {test_prompt}")
        print(f"   Response received: {response[:100]}{'...' if len(response) > 100 else ''}")
        
        # Check if we got a reasonable response
        if response and len(response.strip()) > 0:
            print("   ✓ Got non-empty response")
        else:
            print("   ⚠️ Got empty response")
            
        print("4. Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"   ❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("5. Closing browser...")
        await agent.close()
        print("   ✓ Browser closed")

if __name__ == "__main__":
    result = asyncio.run(test_browser_interaction())
    if result:
        print("\n🎉 BROWSER INTERACTION TEST PASSED")
        sys.exit(0)
    else:
        print("\n💥 BROWSER INTERACTION TEST FAILED")
        sys.exit(1)
