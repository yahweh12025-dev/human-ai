
import asyncio
import sys
sys.path.insert(0, '/home/yahwehatwork/human-ai/agents/notebook_lm')

from agent import NotebookLMAgent

async def test_import():
    print("Testing NotebookLMAgent import...")
    agent = NotebookLMAgent(use_chrome_profile=True)
    print("Agent created successfully!")
    print(f"Use Chrome profile: {agent.use_chrome_profile}")
    print(f"Chrome profile path: {agent.chrome_profile_path}")
    print(f"Session path: {agent.session_path}")

if __name__ == "__main__":
    asyncio.run(test_import())
