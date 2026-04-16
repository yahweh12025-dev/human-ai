#!/usr/bin/env python3
"""
Human AI: Ant Farm Orchestrator (The Queen) - v2.0
Integrates Dify Knowledge Hub and Docker Sandbox for high-fidelity R&D.
"""

import asyncio
import logging
from typing import Dict, Any
from utils.dify_brain import DifyBrain
from utils.sandbox_runner import SandboxRunner
from agents.researcher.researcher_agent import HumanAIResearcher
from agents.ant_farm.writer.writer_agent import WriterAgent
from agents.critic.critic_agent import CriticAgent as ReviewerAgent
from agents.ant_farm.developer.developer_agent import DeveloperAgent
from agents.dr_claw_worker.dr_claw_worker_agent import NativeWorker as DrClawWorker

class AntFarmOrchestrator:
    def __init__(self):
        self.logger = logging.getLogger("AntFarm")
        logging.basicConfig(level=logging.INFO)
        
        # Infrastructure
        self.brain = DifyBrain()
        self.sandbox = SandboxRunner()
        
        # The Squad
        self.researcher = HumanAIResearcher()
        self.developer = DrClawWorker() # Primary implementation engine
        self.reviewer = ReviewerAgent()

    async def execute_pipeline(self, task: Dict[str, Any]):
        goal = task.get('description', 'Unknown Goal')
        self.logger.info(f"🚀 Starting High-Fidelity Pipeline for: {goal}")
        
        # 1. RETRIEVE: Check the Brain
        brain_context = self.brain.query(goal)
        self.logger.info(f"🧠 Brain Context: {brain_context[:100]}...")
        
        # 2. RESEARCH: If brain context is insufficient, perform deep research
        if "No answer found" in brain_context or len(brain_context) < 50:
            self.logger.info("🔍 Brain insufficient. Triggering Deep Research...")
            research_results = await self.researcher.research(goal)
            context = research_results
        else:
            context = brain_context
            
        # 3. IMPLEMENT: Generate code via Dr. Claw
        self.logger.info("🛠️ Implementing solution via Dr. Claw...")
        impl_result = await self.developer.execute_task(f"Implement the following based on context: {context}. Goal: {goal}")
        
        if impl_result['status'] != 'success':
            return {"status": "error", "error": "Implementation failed."}
            
        code = impl_result.get('output', '')
        
        # 4. VERIFY: Test in the Sandbox
        self.logger.info("🛡️ Verifying in Sandbox...")
        rc, stdout, stderr = self.sandbox.run_code(code)
        
        if rc != 0:
            self.logger.error(f"❌ Sandbox failure: {stderr}")
            # In a real loop, we would feed this back to the Reviewer/Developer
            return {"status": "verification_failed", "error": stderr, "code": code}
            
        self.logger.info(f"✅ Verified! Output: {stdout[:100]}")
        
        # 5. REMEMBER: Index the verified solution back into the Brain
        self.brain.index_finding(
            content=f"Goal: {goal}\\nSolution: {code}\\nVerification: {stdout}",
            metadata={"title": f"Verified Solution: {goal}"}
        )
        
        return {
            "status": "success",
            "solution": code,
            "verification": stdout,
            "brain_updated": True
        }

if __name__ == "__main__":
    orch = AntFarmOrchestrator()
    asyncio.run(orch.execute_pipeline({"description": "Create a python script that calculates fibonacci numbers"}))
