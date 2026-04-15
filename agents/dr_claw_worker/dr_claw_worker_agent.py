#!/usr/bin/env python3
"""
Human AI: Dr. Claw Worker Agent
Specialized worker agent that delegates complex coding tasks to the Dr. Claw daemon.
"""

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional
import requests

class DrClawWorker:
    def __init__(self):
        self.drclaw_binary = "/home/ubuntu/human-ai/venv/bin/drclaw"  # Path to installed CLI
        self.drclaw_server_url = "http://localhost:3001"  # Default dr-claw server port
        self.working_dir = os.getenv("WORK_DIR", "/home/ubuntu/human-ai")
        self.process = None

    async def start_server(self):
        """Start the Dr. Claw server if not already running."""
        # Check if server is already responding
        try:
            response = requests.get(f"{self.drclaw_server_url}/api/health", timeout=2)
            if response.status_code == 200:
                print("✅ Dr. Claw server is already running")
                return
        except:
            pass  # Server not running, we'll start it

        print("🚀 Starting Dr. Claw server...")
        # Start the server in the background
        self.process = subprocess.Popen(
            ["node", "/home/ubuntu/human-ai/dr-claw/server/index.js"],
            cwd="/home/ubuntu/human-ai/dr-claw/server",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait a bit for server to start
        await asyncio.sleep(3)
        print("✅ Dr. Claw server started")

    async def stop_server(self):
        """Stop the Dr. Claw server."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None
            print("🛑 Dr. Claw server stopped")

    async def execute_task(self, task_prompt: str) -> Dict[str, Any]:
        """
        Execute a task using the Dr. Claw CLI or API.
        Returns a dictionary with status and result.
        """
        await self.start_server()
        
        try:
            # Use the Dr. Claw CLI to execute the task
            # This assumes the CLI can take a task and return structured output
            cmd = [
                self.drclaw_binary,
                "task",
                "--prompt", task_prompt,
                "--output-format", "json",
                "--working-dir", self.working_dir
            ]
            
            print(f"🔧 Executing Dr. Claw task: {task_prompt[:100]}...")
            
            # Run the command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8').strip()
                print(f"❌ Dr. Claw task failed: {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg or "Unknown error",
                    "output": stdout.decode('utf-8').strip()
                }
            
            # Parse the JSON output
            output_str = stdout.decode('utf-8').strip()
            try:
                result = json.loads(output_str)
                print("✅ Dr. Claw task completed successfully")
                return {
                    "status": "success",
                    "result": result,
                    "output": output_str
                }
            except json.JSONDecodeError:
                # If not JSON, return as plain text
                return {
                    "status": "success",
                    "result": output_str,
                    "output": output_str
                }
                
        except Exception as e:
            print(f"❌ Error executing Dr. Claw task: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

async def main():
    """Test the Dr. Claw worker."""
    worker = DrClawWorker()
    try:
        result = await worker.execute_task("Create a simple Python script that prints 'Hello from Dr. Claw!'")
        print(f"Result: {result}")
    finally:
        await worker.stop_server()

if __name__ == "__main__":
    asyncio.run(main())