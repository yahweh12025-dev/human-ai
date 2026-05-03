import os
import re
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv
from core.utils.sandbox_runner import SandboxRunner

load_dotenv('/home/yahwehatwork/human-ai/.env')

class DoctorAgent:
    def __init__(self):
        self.error_dir = "/home/yahwehatwork/human-ai/errors/"
        self.sandbox = SandboxRunner()

    async def scan_for_errors(self) -> List[Dict[str, Any]]:
        """Scans the errors directory for recent crash logs."""
        if not os.path.exists(self.error_dir):
            return []
            
        errors = []
        for file in os.listdir(self.error_dir):
            if file.endswith(".log"):
                path = os.path.join(self.error_dir, file)
                with open(path, 'r') as f:
                    content = f.read()
                    # Basic pattern to find the last traceback
                    traceback = re.findall(r"Traceback \(most recent call last\):.*", content, re.DOTALL)
                    if traceback:
                        errors.append({
                            "file": file,
                            "error": traceback[-1],
                            "context": content[-1000:]
                        })
        return errors

    async def attempt_fix(self, error_data: Dict[str, Any]) -> bool:
        """Tries to analyze the error and apply a fix to the corresponding file."""
        print(f"🩺 Doctor analyzing error in {error_data['file']}...")
        # In a full implementation, this would use an LLM to generate a diff.
        # For v0.1, we will just log the attempted fix.
        return False

async def main():
    doc = DoctorAgent()
    errors = await doc.scan_for_errors()
    print(f"Found {len(errors)} errors. Ready to heal.")

if __name__ == "__main__":
    asyncio.run(main())
