# REPO REVIEWER AGENT (UPDATED)
# Goal: Analyze external repos AND maintain swarm health by removing deadwood.

import os
from pathlib import Path
from skills.openclaw_skill import OpenClawSkill

class RepoReviewerAgent:
    def __init__(self):
        self.ocl = OpenClawSkill()

    def analyze_repo(self, repo_url):
        print(f"Reviewing repository: {repo_url}")
        return ["suggested_function_1", "suggested_function_2"]

    async def cleanup_deadwood(self, file_path):
        """
        Analyzes a file to see if it's 'deadwood' (unused/obsolete) 
        and confirms with OpenClaw before deletion.
        """
        path = Path(file_path)
        if not path.exists():
            return False
        
        content = path.read_text()
        
        # Ask OpenClaw for a safety check
        prompt = (
            f"I am the RepoReviewerAgent. I found the following file: {file_path}\n"
            f"Content:\n{content}\n\n"
            "Is this file 'deadwood'? Does it affect any other agent, skill, or the swarm's core logic? "
            "Respond ONLY with 'DELETE' if it is safe to remove, or 'KEEP' if it is necessary."
        )
        
        decision = self.ocl.prompt_openclaw(prompt)
        
        if "DELETE" in decision.upper():
            print(f"🗑️ OpenClaw confirmed {file_path} is deadwood. Removing...")
            path.unlink()
            return True
        else:
            print(f"🛡️ OpenClaw advised to KEEP {file_path}.")
            return False

async def main():
    agent = RepoReviewerAgent()
    print("Repo Reviewer Agent active with Deadwood Cleanup capability.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
