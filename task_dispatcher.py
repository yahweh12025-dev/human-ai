#!/usr/bin/env python3
"""
Human AI: Task Dispatcher
Routes tasks between Dr. Claw, n8n, and OpenClaw.
"""

import asyncio
import os
import json
from typing import Dict, Any
from agents.dr_claw_worker.dr_claw_worker_agent import DrClawWorker
from agents.ant_farm.orchestrator import AntFarmOrchestrator
from agents.n8n_bridge.n8n_agent import N8nAgent

class TaskDispatcher:
    def __init__(self):
        self.dr_claw = DrClawWorker()
        self.n8n = N8nAgent()
        self.openclaw = AntFarmOrchestrator()

    async def dispatch(self, task: Dict[str, Any]):
        description = task.get('description', '').lower()
        
        # 1. DETErministic/Enterprise Tasks -> n8n
        # Keywords for workflows: "notify", "sync", "update database", "send email"
        n8n_keywords = ['notify', 'sync', 'update db', 'send email', 'workflow', 'enterprise']
        if any(kw in description for kw in n8n_keywords):
            print(f"⚙️ Dispatching to n8n (Deterministic Workflow): {description[:50]}...")
            # Assume a default workflow ID or extract it from the task
            workflow_id = task.get('workflow_id', 'default_research_sync')
            result = await self.n8n.trigger_workflow(workflow_id, task)
            if result['status'] != 'error':
                return result
            print(f"⚠️ n8n failed: {result.get('error')}. Falling back...")

        # 2. Worker-Heavy Tasks -> Dr. Claw
        worker_keywords = ['implement', 'code', 'script', 'build', 'create', 'fix', 'develop', 'refactor']
        if any(kw in description for kw in worker_keywords):
            print(f"🚀 Dispatching to Dr. Claw (Primary Worker): {description[:50]}...")
            result = await self.dr_claw.execute_task(task['description'])
            if result['status'] == 'success':
                return result
            print(f"⚠️ Dr. Claw failed: {result.get('error')}. Falling back...")

        # 3. General Reasoning/Research -> OpenClaw AntFarm
        print(f"🌐 Dispatching to OpenClaw (Orchestrator): {description[:50]}...")
        return await self.openclaw.execute_pipeline(task)

async def main():
    dispatcher = TaskDispatcher()
    # Test 1: Coding task
    print("\n--- Test 1: Coding ---")
    print(await dispatcher.dispatch({"description": "Implement a Python log parser"}))
    # Test 2: Workflow task
    print("\n--- Test 2: Workflow ---")
    print(await dispatcher.dispatch({"description": "Notify the team via Slack about the research result"}))
    # Test 3: Research task
    print("\n--- Test 3: Research ---")
    print(await dispatcher.dispatch({"description": "Research the current state of fusion energy"}))

if __name__ == "__main__":
    asyncio.run(main())
