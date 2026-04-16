# SOVEREIGN REPO REVIEWER AGENT (RECURSIVE VERSION)
# Goal: Full-spectrum audit of the Human-AI Swarm repository.
# Identifies legacy deadwood, security leaks, and architectural inconsistencies.

import os
import re
from pathlib import Path
from typing import List, Dict, Any
from skills.openclaw_skill import OpenClawSkill

class RepoReviewerAgent:
    def __init__(self):
        self.ocl = OpenClawSkill()
        # Patterns that indicate a breach of the Browser-First Mandate
        self.FORBIDDEN_PATTERNS = [
            r"openai\.OpenC",
            r"anthropic\.Anthropic\(",
            r"google\.generativeai",
            r"requests\.post\(.*'api\.openai\.com'",
            r"requests\.post\(.*'api\.anthropic\.com'"
        ]

    async def analyze_file_purpose(self, file_path: str) -> Dict[str, Any]:
        \"\"\"
        Determines if a file is legacy, active, or a draft.
        \"\"\"
        path = Path(file_path)
        if not path.exists() or path.suffix not in ['.py', '.sh', '.json', '.md']:
            return {"status": "ignored"}
        
        try:
            content = path.read_text(errors='ignore')
            # Check for Browser-First violations first
            violations = [p for p in self.FORBIDDEN_PATTERNS if re.search(p, content)]
            
            # Ask OpenClaw to categorize the file
            prompt = (
                f"Audit this file: {file_path}\\n"
                f"Content snippet (first 500 chars):\\n{content[:500]}...\\n\\n"
                "Categorize this file as: 'ACTIVE', 'DRAFT', or 'LEGACY'. "
                "If 'LEGACY', explain why it should be moved to archive/."
                "Respond in format: CATEGORY | REASON"
            )
            decision = self.ocl.prompt_openclaw(prompt)
            
            return {
                "file": file_path,
                "category": decision.split('|')[0].strip().upper() if '|' in decision else "UNKNOWN",
                "reason": decision.split('|')[1].strip() if '|' in decision else decision,
                "violations": violations
            }
        except Exception as e:
            return {"file": file_path, "status": "error", "error": str(e)}

    async def run_full_recursive_audit(self) -> List[Dict[str, Any]]:
        \"\"\"
        Crawl the entire repository and generate a comprehensive audit report.
        \"\"\"
        print("🔍 Starting Recursive Sovereign Audit of /home/ubuntu/human-ai...")
        full_report = []
        
        # Folders to ignore during the audit
        ignore_list = ['.git', 'venv', 'node_modules', '__pycache__', 'archive', '.infrastructure_vault']
        
        for root, dirs, files in os.walk('/home/ubuntu/human-ai'):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_list]
            
            for file in files:
                file_path = os.path.join(root, file)
                result = await self.analyze_file_purpose(file_path)
                if result.get("category") == "LEGACY" or result.get("violations"):
                    full_report.append(result)
        
        return full_report

async def main():
    agent = RepoReviewerAgent()
    report = await agent.run_full_recursive_audit()
    
    print(f"\\n--- 🛡️ SOVEREIGN AUDIT REPORT ---")
    print(f"Found {len(report)} items requiring attention.\\n")
    
    for item in report:
        status = "🚨 VIOLATION" if item.get("violations") else "🗑️ LEGACY"
        print(f"[{status}] {item['file']}")
        print(f"Reason: {item['reason']}")
        if item.get("violations"):
            print(f"Patterns: {item['violations']}")
        print("-" * 40)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
