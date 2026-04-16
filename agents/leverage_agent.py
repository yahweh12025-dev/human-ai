# LEVERAGE AGENT (CONCURRENCY ENGINE)
# Goal: Run multiple instances of an agent to produce a 'consensus' output.

import asyncio
from typing import List, Callable

class LeverageAgent:
    def __init__(self, agent_class, agent_init_args=None):
        self.agent_class = agent_class
        self.args = agent_init_args or {}

    async def run_parallel(self, task_fn: Callable, prompt: str, multiplier: int = 5):
        """
        Runs N instances of an agent simultaneously to gather diverse solutions.
        """
        print(f"🚀 Leveraging {multiplier}x instances of {self.agent_class.__name__}...")
        
        tasks = []
        for i in range(multiplier):
            agent_instance = self.agent_class(**self.args)
            tasks.append(task_fn(agent_instance, prompt))
            
        results = await asyncio.gather(*tasks)
        
        # Consensus logic: find the most common or highest quality result
        print(f"Gathered {len(results)} diverse perspectives. Synthesizing...")
        return results

async def main():
    # Example: Leverage the Navigator agent 5x to find the fastest URL
    # from agents.navigator.navigator_agent import NavigatorAgent
    # leverage = LeverageAgent(NavigatorAgent)
    # results = await leverage.run_parallel(lambda a, p: a.browse_and_extract(p), "https://example.com")
    print("Leverage Agent active (Parallel Execution Engine).")

if __name__ == "__main__":
    asyncio.run(main())
