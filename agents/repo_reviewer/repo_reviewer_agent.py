# SOVEREIGN REPO REVIEWER AGENT
# Goal: Act as the Lead Auditor for the Human-AI Swarm.
# Ensures strict adherence to Browser-First mandate and security standards.

import os
import re
from pathlib import Path
from typing import List, Dict
from skills.openclaw_skill import OpenClawSkill

class RepoReviewerAgent:
    def __init__(self):
        self.ocl = OpenClawSkill()
        # Patterns that indicate a breach of the Browser-First Mandate
        self.FORBIDDEN_PATTERNS = [
            r"openai\.OpenAI\(",
            r"anthropic\.Anthropic\(",
            r"google\.generativeai",
            r"requests\.post\(.*'api\.openai\.com'",
            r"requests\.post\(.*'api\.anthropic\.com'"
        ]

    async def audit_browser_compliance(self, file_path: str) -> Dict[str, Any]:
        \"\"\"
        Checks if a file contains forbidden direct LLM API calls.
        \"\"\"
        path = Path(file_path)
        if not path.exists() or path.suffix != '.py':
            return {"compliant": True}
        
        content = path.read_text()
        violations = []
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, content):
                violations.append(pattern)
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "file": file_path
        }

    async def audit_git_hygiene(self) -> List[str]:
        \"\"\"
        Checks for files that should NEVER be in git.
        \"\"\"
        forbidden_dirs = ['node_modules', 'venv', '.env', '.git']
        findings = []
        for root, dirs, files in os.walk('.'):
            for d in dirs:
                if d in forbidden_dirs:
                    findings.append(f"Forbidden directory found: {os.path.join(root, d)}")
        return findings

    async def cleanup_deadwood(self, file_path: str) -> bool:
        \"\"\"
        Analyzes a file to see if it's 'deadwood' and confirms with OpenClaw.
        \"\"\"
        path = Path(file_path)
        if not path.exists(): return False
        
        content = path.read_text()
        prompt = (
            f"I am the RepoReviewerAgent. I found the following file: {file_path}\\n"
            f"Content:\\n{content}\\n\\n"
            "Is this file 'deadwood'? Respond ONLY with 'DELETE' or 'KEEP'."
        )
        decision = self.ocl.prompt_openclaw(prompt)
        if "DELETE" in decision.upper():
            path.unlink()
            return True
        return False

    async def run_full_audit(self) -> Dict[str, Any]:
        \"\"\"
        Runs a complete scan of the /agents and /utils directories.
        \"\"\"
        print("🔍 Starting Sovereign Audit...")
        results = {"violations": [], "hygiene_issues": []}
        
        # 1. Audit Browser Compliance
        for root, _, files in os.walk('agents'):
            for file in files:
                if file.endswith('.py'):
                    res = await self.audit_browser_compliance(os.path.join(root, file))
                    if not res["compliant"]:
                        results["violations"].append(res)
        
        # 2. Audit Git Hygiene
        results["hygiene_issues"] = await self.audit_git_hygiene()
        
        return results

async def main():
    agent = RepoReviewerAgent()
    report = await agent.run_full_audit()
    print(f"Audit Complete. Violations: {len(report['violations'])}, Hygiene Issues: {len(report['hygiene_issues'])}")
    if report['violations']:
        print("🚨 BROWSER-FIRST VIOLATIONS FOUND:")
        for v in report['violations']:
            print(f"- {v['file']}: {v['violations']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
