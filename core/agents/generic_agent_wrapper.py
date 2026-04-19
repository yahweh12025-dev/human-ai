
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

    def _sanitize_for_shell(self, text: str) -> str:
        """
        Sanitize text for shell execution by:
        1. Stripping leading and trailing whitespace
        2. Removing any leading whitespace from each line (to fix indentation issues)
        3. Ensuring the text is not empty
        """
        if not text:
            return ""
        # Split into lines, strip each line, and rejoin with newline
        lines = text.split('\n')
        stripped_lines = [line.lstrip() for line in lines]
        # Join and strip again to remove any trailing newline that might become leading
        result = '\n'.join(stripped_lines).strip()
        return result

    async def spawn(self, role: str, goal: str, constraints: str = "") -> Dict[str, Any]:
        """
        Spawns a GenericAgent instance as a background process.
        """
        print(f"🚀 [GenericAgent] Spawning agent: Role={role}, Goal={goal}")
        
        # Sanitize goal and constraints to fix indentation issues
        # Strip leading/trailing whitespace and normalize internal whitespace for shell commands
        sanitized_goal = self._sanitize_for_shell(goal) if role in ["security_auditor", "devops_engineer", "sre"] else goal.strip()
        sanitized_constraints = self._sanitize_for_shell(constraints) if role in ["security_auditor", "devops_engineer", "sre"] else constraints.strip()
        
        cmd = [
            "python3", 
            self.entry_point, 
            "--role", role, 
            "--goal", sanitized_goal, 
            "--constraints", sanitized_constraints
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
