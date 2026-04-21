
import asyncio
import sys
import os
sys.path.append('/home/ubuntu/human-ai/core/agents/researcher')

from deepseek_browser_agent import DeepSeekBrowserAgent

async def test_browser_agent():
    agent = DeepSeekBrowserAgent()
    try:
        print("🧪 Testing DeepSeekBrowserAgent with hardened detection...")
        login_success = await agent.login()
        if not login_success:
            print("⚠️  Login check failed - this may be expected if no session exists")
            # Continue anyway to test prompt functionality
        
        # Test with a simple prompt first
        print("📝 Testing simple prompt...")
        response1 = await agent.prompt("Say hello in exactly 5 words.")
        print(f"Response: {response1}")
        
        # Test with a longer prompt to verify timeout handling
        print("📝 Testing longer prompt...")
        response2 = await agent.prompt("Explain quantum computing in 3 sentences.")
        print(f"Response: {response2[:100]}...")
        
        print("✅ Browser agent test completed successfully")
        return True
    except Exception as e:
        print(f"❌ Browser agent test failed: {e}")
        return False
    finally:
        await agent.close()

if __name__ == "__main__":
    result = asyncio.run(test_browser_agent())
    sys.exit(0 if result else 1)
