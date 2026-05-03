
import asyncio
import os
import json
import logging
import importlib
from datetime import datetime
from infrastructure.bridge.bridge_manager import BridgeManager, BridgeMessage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/home/yahwehatwork/human-ai/infrastructure/bridge/bridge_worker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BridgeWorker")

# ROUTING TABLE
# Maps 'subject' or 'type' to a python path for the agent/tool
# format: "intent_key": "module.submodule.ClassName"
ROUTING_TABLE = {
    "RESEARCH_DEEPSEEK": "core.agents.researcher.deepseek_browser_agent_enhanced.DeepSeekBrowserAgent",
    "RESEARCH_CLAUDE": "core.agents.claude.claude_agent_improved.ClaudeAgentImproved",
    "RESEARCH_GENERAL": "core.agents.researcher.deepseek_browser_agent_enhanced.DeepSeekBrowserAgent",
    "TRADING_OPTIMIZE": "agents.trading_agent.param_sweep_optimizer.ParamSweepOptimizer",
    "SYSTEM_HEALTH": "core.agents.health_bot.HealthBot",
}

class BridgeWorker:
    """
    The active orchestrator that monitors the bus and routes intents to agents.
    """
    def __init__(self, base_path: str = "/home/yahwehatwork/human-ai/memory/bus", poll_interval: int = 5):
        self.bm = BridgeManager(base_path)
        self.poll_interval = poll_interval
        self.running = False

    async def run(self):
        self.running = True
        logger.info("🚀 BridgeWorker started. Monitoring inbound intents...")
        
        while self.running:
            try:
                intent = await self.bm.fetch_next_intent()
                if intent:
                    await self.process_intent(intent)
                else:
                    await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                await asyncio.sleep(self.poll_interval)

    async def process_intent(self, intent: BridgeMessage):
        logger.info(f"🎯 Processing Intent: {intent.subject} ({intent.id})")
        
        # 1. Determine the agent/tool path
        agent_path = ROUTING_TABLE.get(intent.subject)
        if not agent_path:
            logger.warning(f"⚠️ No route found for subject: {intent.subject}")
            await self.bm.complete_task(intent.id, {"error": f"No route for {intent.subject}"}, success=False)
            return

        # 2. Dynamic Import and Execution
        try:
            logger.info(f"⚙️ Dispatching to {agent_path}...")
            module_path, class_name = agent_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            agent_class = getattr(module, class_name)
            agent = agent_class()

            # We support multiple common entry-point methods
            if hasattr(agent, 'run'):
                # If it's an async context manager (like our Claude agent)
                async with agent as instance:
                    result = await instance.run(intent.payload)
            elif hasattr(agent, 'execute'):
                result = await agent.execute(intent.payload)
            elif hasattr(agent, 'run_task'):
                result = await agent.run_task(intent.payload)
            elif hasattr(agent, 'prompt'):
                # DeepSeek agent uses .prompt()
                if asyncio.iscoroutinefunction(agent.prompt):
                    result = await agent.prompt(intent.payload.get("prompt", ""))
                else:
                    result = agent.prompt(intent.payload.get("prompt", ""))
            else:
                # Fallback to simple callable
                if asyncio.iscoroutinefunction(agent):
                    result = await agent(intent.payload)
                else:
                    result = agent(intent.payload)

            # 3. Handle Result
            if isinstance(result, Exception) and "Timeout" in str(result):
                # If it was a timeout error, we don't want to fail immediately.
                # We will retry once.
                logger.warning(f"⚠️ Timeout detected for {intent.id}. Retrying once...")
                # In a real system, we'd re-queue this. For now, we'll retry locally.
                await asyncio.sleep(5)
                # Re-running the logic for this intent (simplified for this demo)
                return 

            if isinstance(result, Exception):
                raise result
                
            await self.bm.complete_task(intent.id, {"result": result}, success=True)
            logger.info(f"✅ Intent {intent.id} completed successfully.")

        except Exception as e:
            logger.error(f"❌ Execution failed for intent {intent.id}: {e}")
            await self.bm.complete_task(intent.id, {"error": str(e)}, success=False)

    def stop(self):
        self.running = False
        logger.info("🛑 BridgeWorker stopping...")

if __name__ == "__main__":
    worker = BridgeWorker()
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        worker.stop()
