import os
import re
from pathlib import Path

class ComplianceAgent:
    def __init__(self, log_path="/home/ubuntu/openclaw_swarm.log"):
        self.log_path = log_path

    def audit_logs(self):
        if not os.path.exists(self.log_path):
            return "❌ Log file not found."

        violations = []
        with open(self.log_path, "r") as f:
            for line in f:
                # Look for model patterns in logs (e.g., "model: google/gemini-pro")
                match = re.search(r"model: ([^\s,]+)", line)
                if match:
                    model_name = match.group(1)
                    if not (model_name.endswith(":free") or "ollama" in model_name.lower()):
                        violations.append(f"Paid model detected: {model_name} in line: {line.strip()}")

        if not violations:
            return "✅ COMPLIANT: All detected models are free."
        
        return "❌ VIOLATION:\n" + "\n".join(violations)

if __name__ == "__main__":
    agent = ComplianceAgent()
    print(agent.audit_logs())
