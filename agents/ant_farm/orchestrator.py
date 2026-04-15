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
from agents.critic.critic_agent import CriticAgent as ReviewerAgent
from agents.ant_farm.developer.developer_agent import DeveloperAgent
from agents.dr_claw_worker.dr_claw_worker_agent import DrClawWorker

class AntFarmOrchestrator:
    def __init__(self):
        self.logger = logging.getLogger("AntFarm")
        logging.basicConfig(level=logging.INFO)
        
        # Initialize the squad
        self.writer = HumanAIResearcher() # Researcher as the lead Writer
        self.reviewer = ReviewerAgent()
        self.developer = DeveloperAgent()
        self.dr_claw_worker = DrClawWorker()
        
        print("👑 Ant Farm Orchestrator Initialized with Active Squad and Dr. Claw Worker.")

    async def execute_pipeline(self, task: Dict[str, Any]):
        """
        Executes a task through the specialized agent pipeline.
        Pipeline: Task -> Writer -> Reviewer -> Developer -> Final Result
        """
        print(f"🐜 Starting Ant Farm Pipeline for task: {task.get('description', 'Unknown')}")
        
        # 1. WRITER PHASE
        print("✍️ Phase 1: Writer is processing the input...")
        # If the task description looks like structured data (starts with '['), use synthesize
        task_desc = task.get('description', '')
        if task_desc.strip().startswith('['):
            draft = await self.writer.synthesize(task_desc)
        else:
            draft = await self.writer.research(task_desc)
        
        # 2. REVIEWER PHASE
        print("🔍 Phase 2: Reviewer is checking quality...")
        review_result = await self.reviewer.review(draft)
        
        # 3. DEVELOPER PHASE
        if review_result["status"] == "pass":
            print("💻 Phase 3: Developer is implementing...")
            # Check if this is a coding task suitable for Dr. Claw Worker
            task_desc_lower = draft.get('content', '').lower() if isinstance(draft, dict) else str(draft).lower()
            coding_keywords = ['implement', 'code', 'script', 'function', 'class', 'create', 'build', 'develop', 'write', 'program', 'application', 'website', 'api', 'database']
            
            if any(keyword in task_desc_lower for keyword in coding_keywords):
                print("🤖 Delegating to Dr. Claw Worker for specialized code execution...")
                implementation = await self.dr_claw_worker.execute_task(str(draft))
            else:
                print("💻 Using standard Developer Agent...")
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
