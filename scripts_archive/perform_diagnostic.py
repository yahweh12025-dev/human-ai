import os
import subprocess
import shutil

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def diagnostic():
    print("--- SYSTEM DIAGNOSTIC START ---")
    
    # 1. Check OpenClaw
    print("\n[1] Checking OpenClaw...")
    out, err, code = run_cmd("openclaw status")
    print(f"Status: {'OK' if code == 0 else 'FAIL'}\nOutput: {out}\nError: {err}")
    
    # 2. Check Python/Venv
    print("\n[2] Checking Python Environment...")
    out, err, code = run_cmd("/home/ubuntu/human-ai/venv/bin/python3 --version")
    print(f"Version: {out if code == 0 else 'FAIL'}\nError: {err}")
    
    # 3. Check SQLite/Todo
    print("\n[3] Checking Todo Database...")
    out, err, code = run_cmd("sqlite3 /home/ubuntu/human-ai/todo.db '.tables'")
    print(f"Tables: {out if code == 0 else 'FAIL'}\nError: {err}")
    
    # 4. Check Playwright
    print("\n[4] Checking Playwright...")
    out, err, code = run_cmd("/home/ubuntu/human-ai/venv/bin/python3 -m playwright --version")
    print(f"Version: {out if code == 0 else 'FAIL'}\nError: {err}")

    # 5. Check Directory Structure
    print("\n[5] Checking Directory Structure...")
    dirs = ["/home/ubuntu/human-ai/agents", "/home/ubuntu/human-ai/logs", "/home/ubuntu/human-ai/outputs", "/home/ubuntu/human-ai/session"]
    for d in dirs:
        exists = os.path.exists(d)
        print(f"{d}: {'EXISTS' if exists else 'MISSING'}")

    print("\n--- DIAGNOSTIC COMPLETE ---")

if __name__ == "__main__":
    diagnostic()
