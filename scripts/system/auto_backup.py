#!/usr/bin/env python3
"""
Automated backup system for Hermes, Obsidian vault, and human-ai repository.
"""
import os
import subprocess
from datetime import datetime
import sys

def main():
    HOME = os.path.expanduser("~")
    HERMES_DIR = os.path.join(HOME, ".hermes")
    OBSIDIAN_VAULT = os.path.join(HOME, "Documents", "Obsidian Vault")
    REPO_ROOT = "/home/yahwehatwork/human-ai"
    BACKUP_DIR = os.path.join(HOME, "backups")

    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}.tar.gz"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    sources = [HERMES_DIR, OBSIDIAN_VAULT, REPO_ROOT]

    excludes = [
        "--exclude=__pycache__",
        "--exclude='*.pyc'",
        "--exclude=node_modules",
        "--exclude=venv*",
        "--exclude=.git",
        "--exclude=*.log",
        "--exclude=logs/",
        "--exclude=session/",
        "--exclude=browser_profiles/",
        "--exclude=.browser-profile/",
        "--exclude=*.backup",
        "--exclude=*.bak",
        "--exclude=*.old",
        "--exclude=*.tmp",
        "--exclude=*.temp",
        "--exclude=*.swp",
        "--exclude=*.swo",
        "--exclude=*~",
        "--exclude=.env.backup*",
        "--exclude=.env.*",
        "--exclude=master_log.json",
        "--exclude=improvement.log",
        "--exclude=routing.log",
        "--exclude=researcher_login.log",
        "--exclude=autopilot.log",
        "--exclude=autodev.log",
    ]

    cmd = ["tar", "-czf", backup_path] + excludes + sources
    print("Running backup command:")
    print(" ".join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Backup completed successfully.")
        print(f"Backup saved to: {backup_path}")
        # Optionally, remove backups older than N days
        keep_days = 7
        now = datetime.now().timestamp()
        for filename in os.listdir(BACKUP_DIR):
            filepath = os.path.join(BACKUP_DIR, filename)
            if os.path.isfile(filepath) and filename.endswith(".tar.gz"):
                if os.path.getmtime(filepath) < now - keep_days * 86400:
                    os.remove(filepath)
                    print(f"Removed old backup: {filename}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Backup failed with return code {e.returncode}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
