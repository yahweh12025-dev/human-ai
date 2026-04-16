import os
import re
import subprocess
from typing import List, Tuple

# Patterns for keys we want to protect
KEY_PATTERNS = {
    "OpenRouter": r"sk-or-v1-[a-zA-Z0-9]{64,}",
    "Google API": r"AIza[0-9A-Za-z-_]{35}",
    "Groq": r"gsk_[a-zA-Z0-9]{63}",
    "Infisical Token": r"st\.[a-zA-Z0-9\.]+",
    "Generic Secret": r"(?i)(api_key|secret|password|token)\s*[:=]\s*['\"]([a-zA-Z0-9_\-]{16,})['\"]"
}

def scan_for_leaks(directory: str = "/home/ubuntu/human-ai") -> List[Tuple[str, int, str]]:
    findings = []
    for root, _, files in os.walk(directory):
        # Skip git and venv folders
        if '.git' in root or 'venv' in root or '__pycache__' in root:
            continue
            
        for file in files:
            if file.endswith(('.env', '.json', '.py', '.md', '.sh', '.yaml')):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        for i, line in enumerate(f, 1):
                            for key_type, pattern in KEY_PATTERNS.items():
                                if re.search(pattern, line):
                                    findings.append((path, i, key_type))
                except Exception:
                    continue
    return findings

def report_leaks():
    leaks = scan_for_leaks()
    if not leaks:
        print("✅ No leaked keys found in the repository.")
        return
    
    print(f"⚠️ FOUND {len(leaks)} POTENTIAL LEAKS!")
    for path, line, key_type in leaks:
        print(f"📍 {path}:{line} -> {key_type}")
    
    # Write to the watchdog alert file for the system to notify the user
    with open("/home/ubuntu/human-ai/scripts/watchdog_alert.txt", "a") as f:
        f.write(f"SECURITY ALERT: {len(leaks)} leaked keys found in repository.\n")

if __name__ == "__main__":
    report_leaks()
