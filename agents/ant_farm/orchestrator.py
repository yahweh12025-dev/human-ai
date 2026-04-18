#!/usr/bin/env python3
"""
Human AI: Ant Farm Orchestrator (The Queen) - v2.1
Integrates Dify Knowledge Hub, Docker Sandbox, and Master Logging for high-fidelity R&D.
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

from utils.master_log import SwarmMasterLog

class AntFarmOrchestrator:
    def __init__(self):
        # Global Master Log for system-wide events
        self.master_log = SwarmMasterLog()
        
        # Local console logger
        self.console_logger = logging.getLogger("AntFarm")
        logging.basicConfig(level=logging.INFO)
        
        # Infrastructure
        self.brain = DifyBrain()
        self.sandbox = SandboxRunner()
        
        # The Squad
        self.researcher = HumanAIResearcher()
        self.developer = DrClawWorker() # Primary implementation engine
        self.reviewer = ReviewerAgent()

    async def execute_pipeline(self, task: Dict[str, Any]):
        # Handle both dictionary tasks and string tasks (for backward compatibility)
        if isinstance(task, str):
            # If task is a string, treat it as the description/goal directly
            goal = task
        elif isinstance(task, dict):
            # If task is a dictionary, get the description field
            goal = task.get("description", "Unknown Goal")
        else:
            # Fallback for other types
            goal = str(task)
        
        # Log to Master Log and Console
        self.master_log.log_event("AntFarm", "PIPELINE_START", f"Starting pipeline for: {goal}")
        self.console_logger.info(f"🚀 Starting High-Fidelity Pipeline for: {goal}")
        
        # 1. RETRIEVE: Check the Brain
        try:
            brain_context = self.brain.query(goal)
            self.master_log.log_event("AntFarm", "BRAIN_QUERY", f"Context retrieved for: {goal}")
            self.console_logger.info(f"🧠 Brain Context: {brain_context[:100]}...")
        except Exception as e:
            brain_context = f"Brain Query Error: {e}"
            self.master_log.log_event("AntFarm", "BRAIN_ERROR", str(e))
            self.console_logger.error(f"❌ Brain Error: {e}")
        
        # 2. RESEARCH: If brain context is insufficient, perform deep research
        if "No answer found" in brain_context or len(brain_context) < 50:
            self.console_logger.info("🔍 Brain insufficient. Triggering Deep Research...")
            self.master_log.log_event("AntFarm", "RESEARCH_START", f"Deep research triggered for: {goal}")
            research_results = await self.researcher.research(goal)
            context = research_results
        else:
            context = brain_context
            
        # 3. IMPLEMENT: Generate code via Dr. Claw (NativeWorker)
        self.console_logger.info("🛠️ Implementing solution via Dr. Claw...")
        self.master_log.log_event("AntFarm", "IMPLEMENTATION_START", f"Implementing solution for: {goal}")
        impl_result = await self.developer.execute_task(f"Implement the following based on context: {context}. Goal: {goal}")
        
        if impl_result['status'] != 'success':
            self.master_log.log_event("AntFarm", "IMPLEMENTATION_FAILURE", impl_result.get('error', 'Unknown error'))
            return {"status": "error", "error": "Implementation failed."}
            
        code = impl_result.get('output', '')
        
        # 4. VERIFY: Test in the Sandbox
        self.console_logger.info("🛡️ Verifying in Sandbox...")
        self.master_log.log_event("AntFarm", "VERIFICATION_START", f"Verifying code for: {goal}")
        rc, stdout, stderr = self.sandbox.run_code(code)
        
        if rc != 0:
            self.console_logger.error(f"❌ Sandbox failure: {stderr}")
            self.master_log.log_event("AntFarm", "VERIFICATION_FAILURE", stderr)
            # In a real loop, we would feed this back to the Reviewer/Developer
            return {"status": "verification_failed", "error": stderr, "code": code}
            
        self.console_logger.info(f"✅ Verified! Output: {stdout[:100]}")
        self.master_log.log_event("AntFarm", "VERIFICATION_SUCCESS", f"Code verified for: {goal}")
        
        # 5. REMEMBER: Index the verified solution back into the Brain
        try:
            self.brain.index_finding(
                content=f"Goal: {goal}\\nSolution: {code}\\nVerification: {stdout}",
                metadata={"title": f"Verified Solution: {goal}"}
            )
            self.master_log.log_event("AntFarm", "BRAIN_INDEX", f"Verified solution indexed for: {goal}")
        except Exception as e:
            self.console_logger.error(f"⚠️ Brain indexing failed: {e}")
            self.master_log.log_event("AntFarm", "BRAIN_INDEX_ERROR", str(e))
        
        return {
            "status": "success",
            "solution": code,
            "verification": stdout,
            "brain_updated": True
        }

if __name__ == "__main__":
    orch = AntFarmOrchestrator()
    asyncio.run(orch.execute_pipeline({"description": "Create a python script that calculates fibonacci numbers"}))
