
import asyncio
import sys
sys.path.insert(0, '/home/ubuntu/human-ai')
from agents.researcher.researcher_agent import DeepSeekBrowserAgent

async def test():
    print("Testing DeepSeekBrowserAgent instantiation...")
    agent = DeepSeekBrowserAgent()
    print("Agent created.")
    # We won't actually start the browser in this test to avoid hanging
    # but we can check that the methods exist.
    print("Checking methods:")
    print(f"  start_browser: {hasattr(agent, 'start_browser')}")
    print(f"  login: {hasattr(agent, 'login')}")
    print(f"  prompt: {hasattr(agent, 'prompt')}")
    print(f"  close: {hasattr(agent, 'close')}")
    print("Test completed successfully.")

if __name__ == "__main__":
    asyncio.run(test())
