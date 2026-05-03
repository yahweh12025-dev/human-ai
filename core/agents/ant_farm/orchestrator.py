#!/usr/bin/env python3
"""
Human AI: Ant Farm Orchestrator (The Queen) - v2.1
Integrates Dify Knowledge Hub, Docker Sandbox, and Master Logging for high-fidelity R&D.
"""

import asyncio
import logging
from typing import Dict, Any
from core.utils.dify_brain import DifyBrain
from core.utils.local_executor import LocalSafeExecutor
from core.agents.researcher.researcher_agent import HumanAIResearcher
from core.agents.ant_farm.writer.writer_agent import WriterAgent
from core.agents.critic.critic_agent import CriticAgent as ReviewerAgent
from core.native_worker import NativeWorker
from core.agents.generic_agent_wrapper import GenericAgentWrapper
from core.agents.converter_agent import ConverterAgent
from core.agents.ocr_agent import OCRAgent
from core.agents.hybrid_llm_router import HybridLLMRouter
from core.utils.storage_orchestrator import StorageOrchestrator
from core.utils.mcp_bridge import MCPBridge
from core.agents.notebook_lm_agent import NotebookLMAgent
from core.utils.storage_orchestrator import StorageOrchestrator


from core.utils.master_log import SwarmMasterLog

class AntFarmOrchestrator:
    def __init__(self):
        # Global Master Log for system-wide events
        self.master_log = SwarmMasterLog()
        
        # Local console logger
        self.console_logger = logging.getLogger("AntFarm")
        logging.basicConfig(level=logging.INFO)
        
        # Infrastructure
        self.brain = DifyBrain()
        self.sandbox = LocalSafeExecutor()
        
        # The Squad
        self.researcher = HumanAIResearcher()
        self.developer = NativeWorker() # Primary implementation engine
        self.reviewer = ReviewerAgent()
        self.generic_spawner = GenericAgentWrapper()
        self.router = HybridLLMRouter()
        self.notebook_lm = NotebookLMAgent()
        self.mcp_bridge = MCPBridge()

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
        
        # 1. RETRIEVE: Check the Brain and Supabase
        try:
            # First, check the Brain (Dify)
            brain_context = self.brain.query(goal)
            
            # Second, check the Supabase Storage for previously verified findings
            storage = StorageOrchestrator()
            supabase_findings = storage.retrieve_findings(goal)
            
            if supabase_findings:
                findings_text = "\n".join([f"- {f['content']}" for f in supabase_findings])
                brain_context += f"\n\nPreviously Verified Findings from Supabase:\n{findings_text}"
            
            self.master_log.log_event("AntFarm", "BRAIN_QUERY", f"Context retrieved for: {goal}")
            self.console_logger.info(f"🧠 Brain Context: {brain_context[:100]}...")
        except Exception as e:
            brain_context = f"Brain Query Error: {e}"
            self.master_log.log_event("AntFarm", "BRAIN_ERROR", str(e))
            self.console_logger.error(f"❌ Brain Error: {e}")
        
        # 2. RESEARCH: If brain context is insufficient, perform deep research
        # But first, check if we need to process documents/images via Converter/OCR agents
        needs_processing = (
            ".pdf" in goal.lower() or ".doc" in goal.lower() or ".pptx" in goal.lower() or
            ".png" in goal.lower() or ".jpg" in goal.lower() or ".jpeg" in goal.lower() or
            "extract text" in goal.lower() or "ocr" in goal.lower() or "convert" in goal.lower()
        )
        
        if needs_processing:
            self.console_logger.info("📄 Document/Image task detected. Activating pre-processing pipeline...")
            self.master_log.log_event("AntFarm", "PREPROCESS_START", f"Starting document/image processing for: {goal}")
            
            # Initialize processors
            converter = ConverterAgent()
            ocr_agent = OCRAgent()
            
            # Extract actual file paths from the goal or context
            # Look for paths ending in supported extensions
            file_paths = re.findall(r'(/home/yahwehatwork/human-ai/\S+?\.(?:pdf|docx|pptx|json|png|jpg|jpeg|bmp|tiff))', goal + " " + context)
            
            processed_context = ""
            for path in file_paths:
                self.console_logger.info(f"Processing file: {path}")
                ext = Path(path).suffix.lower()
                
                if ext in ['.pdf', '.docx', '.pptx', '.json']:
                    result_path = converter.convert(path)
                    if result_path:
                        with open(result_path, 'r', encoding='utf-8') as f:
                            processed_context += f"\n--- Content from {path} ---\n{f.read()}\n"
                elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
                    text = ocr_agent.extract_text(path)
                    if text:
                        processed_context += f"\n--- OCR Content from {path} ---\n{text}\n"
            
            # Clean up
            await converter.close()
            await ocr_agent.close()
            
            if not processed_context:
                processed_context = "No extractable content found in provided files. "
            
            # Now use this processed context for research
            if "No answer found" in brain_context or len(brain_context) < 50:
                self.console_logger.info("🔍 Brain insufficient after preprocessing. Triggering Omni-Routed Research...")
                self.master_log.log_event("AntFarm", "RESEARCH_START", f"Omni-routed research triggered for: {goal}")
                route_result = await self.router.route_task(f"Research and provide a detailed summary of: {goal}\n\nRelevant Context:\n{processed_context}")
                research_results = route_result.get('response', 'No results found')
                context = processed_context + " " + research_results
            else:
                context = processed_context + " " + brain_context
        elif "No answer found" in brain_context or len(brain_context) < 50:
            self.console_logger.info("🔍 Brain insufficient. Triggering Omni-Routed Research...")
            self.master_log.log_event("AntFarm", "RESEARCH_START", f"Omni-routed research triggered for: {goal}")
            route_result = await self.router.route_task(f"Research and provide a detailed summary of: {goal}")
            research_results = route_result.get('response', 'No results found')
            context = research_results
        else:
            context = brain_context
            
        # 3. IMPLEMENT: Determine if a specialized GenericAgent is needed
        if "spawn generic agent" in context.lower() or "specialized agent" in goal.lower():
            self.console_logger.info("🚀 Specialized task detected. Spawning GenericAgent...")
            self.master_log.log_event("AntFarm", "GENERIC_AGENT_START", f"Spawning GenericAgent for: {goal}")
            impl_result = await self.generic_spawner.spawn(
                role="Specialized Expert", 
                goal=f"Implement the following: {goal}. Context: {context[:500]}",
                constraints="Must produce a verifiable output in the swarm workspace"
            )
            # Since GenericAgent runs in background, we mark it as 'delegated'
            if impl_result['status'] == 'spawned':
                return {"status": "delegated", "agent_pid": impl_result['pid'], "message": "Task delegated to specialized GenericAgent"}
        else:
            self.console_logger.info("🛠️ Implementing solution via NativeWorker (Autonomous Mode)...")
            self.master_log.log_event("AntFarm", "IMPLEMENTATION_START", f"Implementing solution for: {goal}")
            
            # Trigger High-Fidelity Implementation (Generate + Apply via Kilo-Code)
            impl_result = await self.developer.execute_task(
                f"Implement the following based on context: {context}. Goal: {goal}",
                apply_changes=True
            )
        
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
        
        # 5. REMEMBER: Index the verified solution back into the Brain and Graph
        try:
            self.brain.index_finding(
                content=f"Goal: {goal}\\nSolution: {code}\\nVerification: {stdout}",
                metadata={"title": f"Verified Solution: {goal}"}
            )
            self.master_log.log_event("AntFarm", "BRAIN_INDEX", f"Verified solution indexed for: {goal}")
            
            # Sync to Graphify for relational intelligence
            from core.utils.graphify_bridge import GraphifyBridge
            bridge = GraphifyBridge()
            if bridge.enabled:
                bridge.bridge_dify_to_graph(goal)
                self.master_log.log_event("AntFarm", "GRAPH_SYNC", f"Relational data synced to Graphify for: {goal}")
                
        except Exception as e:
            self.console_logger.error(f"⚠️ Brain/Graph Indexing failed: {e}")
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
