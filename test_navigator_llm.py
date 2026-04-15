import asyncio
import os
import json
import re
from pathlib import Path

from agents.navigator.navigator_agent import NavigatorAgent
async def test_navigator_llm():
    agent = NavigatorAgent()
    goal = "Search for OpenClaw on Google"
    await agent.run_goal_oriented_loop(goal=goal, max_steps=3)

if __name__ == "__main__":
    asyncio.run(test_navigator_llm())