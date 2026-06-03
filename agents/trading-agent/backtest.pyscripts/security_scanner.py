import os
import subprocess
import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityScanner:
    """
    Automated security scanning system for checking vulnerabilities in 
    dependencies and code using static analysis tools.
    """
    def __init__(self, target_dir: str = "."):
        self.target_dir = target_dir
        self.scanners = {
            "bandit": "bandit -r {target} -f json",
            "safety": "safety check --json",
            "pip-audit": "pip-audit --format json"
        }

    def run_scanner(self, scanner_name: str) -> Dict[str, Any]:
        """Runs a specific security scanner and parses result."""
        cmd = self.scanners.get(scanner_name, "").format(target=self.target_dir)
        if not cmd:
            return {"error": "Scanner not found"}
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return {"scanner": scanner_name, "output": result.stdout, "exit_code": result.returncode}
        except Exception as e:
            return {"error": str(e)}

    def full_audit(self) -> List[Dict[str, Any]]:
        """Runs all configured scanners and aggregates reports."""
        reports = []
        for scanner in self.scanners:
            logger.info(f"Running {scanner}...")
            reports.append(self.run_scanner(scanner))
        return reports

if __name__ == "__main__":
    scanner = SecurityScanner(target_dir="/home/yahwehatwork/human-ai")
    # We'll run bandit as it's the most common static analyzer
    report = scanner.run_scanner("bandit")
    print(f"Security Scan Result: {report['output'][:500]}...")
