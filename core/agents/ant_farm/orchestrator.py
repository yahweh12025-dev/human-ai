import asyncio
import json
import shlex
from typing import Any, Dict


class AntFarmOrchestrator:
    def __init__(self, workflow: str = "feature-dev"):
        self.workflow = workflow

    async def execute_pipeline(self, task: Dict[str, Any]) -> Dict[str, Any]:
        description = task.get("description", "")
        proc = await asyncio.create_subprocess_exec(
            "antfarm",
            "workflow",
            "run",
            self.workflow,
            description,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        out = stdout.decode().strip() if stdout else ""
        err = stderr.decode().strip() if stderr else ""

        if proc.returncode != 0:
            return {"status": "error", "error": err or out, "task": description}

        return {
            "status": "routed",
            "target": "AntFarm",
            "workflow": self.workflow,
            "task": description,
            "output": out,
        }
