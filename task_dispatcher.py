#!/usr/bin/env python3
"""
Human AI: Task Dispatcher
Routes tasks between Dr. Claw (Primary Worker) and OpenClaw (Fallback Orchestrator).
"""

import asyncio
import os
import json
from typing import Dict, Any
from agents.dr_claw_worker.dr_claw_worker_agent import DrClawWorker
from agents.ant_farm.orchestrator import AntFarmOrchestrator

class TaskDispatcher:
    def __init__(self):
        self.dr_claw = DrClawWorker()
        self.openclaw = AntFarmOrchestrator()

    async def dispatch(self, task: Dict[str, Any]):
        description = task.get('description', '').lower()
        
        # Define "Worker-Heavy" tasks (Coding, File Ops, Deep Analysis)
        worker_keywords = ['implement', 'code', 'script', 'build', 'create', 'fix', 'develop', 'refactor']
        
        if any(kw in description for kw in worker_keywords):
            print(f"🚀 Dispatching to Dr. Claw (Primary Worker): {description[:50]}...")
            result = await self.dr_claw.execute_task(task['description'])
            
            if result['status'] == 'success':
                print("✅ Dr. Claw completed the task successfully.")
                return result
            
            print(f"⚠️ Dr. Claw failed: {result.get('error')}. Falling back to OpenClaw...")
        else:
            print(f"🌐 Dispatching to OpenClaw (Orchestrator): {description[:50]}...")

        # Fallback to OpenClaw AntFarm Pipeline
        return await self.openclaw.execute_pipeline(task)

async def main():
    dispatcher = TaskDispatcher()
    test_task = {"description": "Implement a new Python utility for log parsing"}
    result = await dispatcher.dispatch(test_task)
    print(f"Final Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
