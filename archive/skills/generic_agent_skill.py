# GENERIC AGENT SKILL
# Goal: Provide the swarm with the ability to spawn general-purpose agents for ad-hoc tasks.

import os
import subprocess
from typing import Dict, Any
from skills.openclaw_skill import OpenClawSkill

class GenericAgentSkill(OpenClawSkill):
    def __init__(self):
        super().__init__()
        self.generic_agent_path = "/home/ubuntu/human-ai/tools/GenericAgent"

    def spawn_agent(self, role: str, goal: str, constraints: str = ""):
        \"\"\"
        Spawns a GenericAgent instance with a specific role and goal.
        \"\"\"
        print(f"🚀 Spawning GenericAgent: Role={role}, Goal={goal}")
        
        # This simulates the execution of the GenericAgent framework
        # In production, this would be a subprocess call to the GenericAgent core
        cmd = [
            "python3", 
            f"{self.generic_agent_path}/main.py", 
            "--role", role, 
            "--goal", goal, 
            "--constraints", constraints
        ]
        
        try:
            # We run it as a background process to avoid blocking the main swarm
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"status": "spawned", "agent_role": role}
        except Exception as e:
            return {"status": "error", "error": str(e)}

async def main():
    skill = GenericAgentSkill()
    print("GenericAgent Skill active. Ad-hoc agent spawning enabled.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
