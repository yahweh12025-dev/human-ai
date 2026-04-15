#!/usr/bin/env python3
"""
Human AI: Ant Farm Orchestrator (The Queen)
Manages the specialized Squads (Writer, Reviewer, Developer) to execute complex tasks.
"""

import asyncio
import logging
from typing import Dict, Any

from agents.researcher.researcher_agent import HumanAIResearcher
from agents.ant_farm.writer.writer_agent import WriterAgent
from agents.ant_farm.reviewer.reviewer_agent import ReviewerAgent
from agents.ant_farm.developer.developer_agent import DeveloperAgent

class AntFarmOrchestrator:
    def __init__(self):
        self.logger = logging.getLogger("AntFarm")
        logging.basicConfig(level=logging.INFO)
        
        # Initialize the squad
        self.writer = HumanAIResearcher() # Researcher as the lead Writer
        self.reviewer = ReviewerAgent()
        self.developer = DeveloperAgent()
        
        print("👑 Ant Farm Orchestrator Initialized with Active Squad.")

    async def execute_pipeline(self, task: Dict[str, Any]):
        """
        Executes a task through the specialized agent pipeline.
        Pipeline: Task -> Writer -> Reviewer -> Developer -> Final Result
        """
        print(f"🐜 Starting Ant Farm Pipeline for task: {task.get('description', 'Unknown')}")
        
        # 1. WRITER PHASE
        print("✍️ Phase 1: Writer is researching and drafting...")
        draft = await self.writer.research(task.get('description'))
        
        # 2. REVIEWER PHASE
        print("🔍 Phase 2: Reviewer is checking quality...")
        review_result = await self.reviewer.review(draft)
        
        # 3. DEVELOPER PHASE
        if review_result["status"] == "pass":
            print("💻 Phase 3: Developer is implementing...")
            implementation = await self.developer.implement(draft)
        else:
            print("❌ Review failed. Returning to Writer.")
            return {"status": "failed", "reason": "Reviewer rejected the draft."}

        print("✅ Pipeline Complete!")
        return {"status": "success", "result": implementation}

async def main():
    orchestrator = AntFarmOrchestrator()
    test_task = {"description": "Create a landing page for a new AI product"}
    result = await orchestrator.execute_pipeline(test_task)
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
