
import subprocess
import os
from typing import Dict, Any, Optional

class GenericAgentWrapper:
    """
    Wrapper for the GenericAgent framework to allow integration into the Swarm Orchestrator.
    """
    def __init__(self, generic_agent_path: str = "/home/ubuntu/human-ai/infrastructure/tools/GenericAgent"):
        self.path = generic_agent_path
        # Use ga.py as the primary entry point if main.py is not available
        self.entry_point = os.path.join(self.path, "ga.py")

    async def spawn(self, role: str, goal: str, constraints: str = "") -> Dict[str, Any]:
        """
        Spawns a GenericAgent instance as a background process.
        """
        print(f"🚀 [GenericAgent] Spawning agent: Role={role}, Goal={goal}")
        
        cmd = [
            "python3", 
            self.entry_point, 
            "--role", role, 
            "--goal", goal, 
            "--constraints", constraints
        ]
        
        try:
            # Use Popen to run as a background process so the orchestrator doesn't hang
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                cwd=self.path
            )
            return {
                "status": "spawned", 
                "pid": process.pid, 
                "role": role,
                "goal": goal
            }
        except Exception as e:
            print(f"❌ [GenericAgent] Spawn failed: {e}")
            return {"status": "error", "error": str(e)}

    async def close(self):
        # GenericAgent runs as independent processes, so close is a no-op 
        # unless we want to track and kill all spawned children.
        pass
