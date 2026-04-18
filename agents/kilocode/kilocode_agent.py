#!/usr/bin/env python3
"""
KiloCodeAgent Wrapper: Uses the KiloCode provider via Hermes CLI for high-fidelity code refactoring.
"""
import asyncio
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

class KiloCodeAgent:
    """Wrapper for KiloCode refactoring using the swarm's provider system."""

    def __init__(self, provider_id: str = "kilocode"):
        self.provider_id = provider_id

    async def refactor_code(self, goal: str, file_path: str, constraints: str = "") -> Dict[str, Any]:
        """
        Use KiloCode to refactor code. 
        Leverages the 'hermes chat -q' command to call the KiloCode provider.
        """
        if not os.path.exists(file_path):
            return {"status": "error", "error": f"File not found: {file_path}"}

        try:
            with open(file_path, 'r') as f:
                original_code = f.read()
        except Exception as e:
            return {"status": "error", "error": f"Failed to read file: {e}"}

        # Construct a prompt that forces the model to return ONLY the refactored code
        prompt = (
            f"### TASK: Refactor the following code.\n"
            f"### GOAL: {goal}\n"
            f"### CONSTRAINTS: {constraints}\n\n"
            f"### CODE TO REFACTOR:\n"
            f"```python\n{original_code}\n```\n\n"
            f"### INSTRUCTION: Return ONLY the refactored code. No explanations, no markdown blocks."
        )

        # Use 'hermes chat -q' for non-interactive single query
        cmd = [
            "hermes", 
            "chat",
            "-q", prompt,
            "--provider", self.provider_id,
            "-Q"  # Quiet mode for programmatic use
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                refactored_code = stdout.decode().strip()
                # Remove markdown backticks if the model included them
                if refactored_code.startswith("```"):
                    lines = refactored_code.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    refactored_code = "\n".join(lines).strip()

                return {
                    "status": "success",
                    "original_code": original_code,
                    "refactored_code": refactored_code,
                    "output": refactored_code
                }
            else:
                return {
                    "status": "error",
                    "error": f"KiloCode provider failed: {stderr.decode()}",
                    "original_code": original_code
                }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error during refactoring: {str(e)}",
                "original_code": original_code
            }

    async def close(self):
        pass

if __name__ == "__main__":
    import asyncio
    async def test():
        agent = KiloCodeAgent()
        test_file = "/tmp/test_kilo.py"
        with open(test_file, 'w') as f:
            f.write("def hello():\n    print('hello')")
        
        print(f"Testing KiloCodeAgent with {test_file}...")
        result = await agent.refactor_code(
            goal="Add type hints and docstring",
            file_path=test_file
        )
        print(json.dumps(result, indent=2))
    
    asyncio.run(test())
