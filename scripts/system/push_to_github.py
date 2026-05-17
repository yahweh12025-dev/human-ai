#!/usr/bin/env python3
import subprocess
import sys
import os
from datetime import datetime

def run_command(command, cwd=None):
    """Helper to run shell commands and return output"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            cwd=cwd
        )
        if result.returncode != 0:
            print(f"❌ Error running: {command}")
            print(f"Stderr: {result.stderr}")
            return False, result.stderr
        return True, result.stdout
    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        return False, str(e)

def push_updates():
    repo_dir = "/home/ubuntu/human-ai"
    
    if not os.path.exists(repo_dir):
        print(f"❌ Repository directory not found: {repo_dir}")
        return

    print(f"🚀 Starting push to GitHub for {repo_dir}...")

    # 1. Git Add
    print("📦 Staging changes...")
    success, output = run_command("git add .", cwd=repo_dir)
    if not success: return

    # 2. Git Commit
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"Auto-update: System cleanup and Human AI enhancements ({timestamp})"
    print(f"📝 Committing changes: {commit_message}")
    
    # Check if there are actually changes to commit
    status_success, status_output = run_command("git status --porcelain", cwd=repo_dir)
    if not status_output.strip():
        print("✨ No changes to commit. Everything is up to date.")
        return

    success, output = run_command(f'git commit -m "{commit_message}"', cwd=repo_dir)
    if not success:
        # If commit fails, it might be because of no changes, which we already checked,
        # but we'll handle it just in case.
        print("⚠️ Commit failed or no changes to commit.")
        return

    # 3. Git Push
    print("📤 Pushing to origin main...")
    success, output = run_command("git push origin main", cwd=repo_dir)
    if success:
        print("✅ Successfully pushed updates to GitHub!")
    else:
        print("❌ Push failed. Please check your git credentials/remote settings.")

if __name__ == "__main__":
    push_updates()
