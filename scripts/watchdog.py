import os
import subprocess
import logging
from pathlib import Path

LOG_FILES = [
    "/home/ubuntu/human-ai/autopilot.log",
    "/home/ubuntu/human-ai/logs/navigator_loop.log",
    "/home/ubuntu/human-ai/autodev.log"
]
ERROR_KEYWORDS = ["Error", "Exception", "SIGKILL", "Failed", "429", "fatal"]
DAEMON_CMD = "nohup /home/ubuntu/human-ai/run-autopilot.sh > /home/ubuntu/human-ai/autopilot.log 2>&1 &"

def check_daemon():
    try:
        output = subprocess.check_output(["ps", "aux"], text=True)
        if "run-autopilot.sh" not in output:
            print("⚠️ Autopilot daemon is dead. Restarting...")
            subprocess.Popen(DAEMON_CMD, shell=True)
            return False
    except Exception as e:
        print(f"Error checking daemon: {e}")
    return True

def scan_logs():
    found_errors = []
    for log_path in LOG_FILES:
        path = Path(log_path)
        if not path.exists(): continue
        
        # Scan only the last 50 lines to avoid old errors
        try:
            with open(path, 'r') as f:
                lines = f.readlines()[-50:]
                for line in lines:
                    if any(kw in line for kw in ERROR_KEYWORDS):
                        found_errors.append(f"[{path.name}] {line.strip()}")
        except Exception as e:
            print(f"Error reading {log_path}: {e}")
    return found_errors

if __name__ == "__main__":
    daemon_ok = check_daemon()
    errors = scan_logs()
    
    if not daemon_ok or errors:
        message = "🚨 Autopilot Watchdog Alert:\n"
        if not daemon_ok: message += "- Daemon was restarted\n"
        for err in errors: message += f"- {err}\n"
        
        # Use the notifier skill via shell
        try:
            # This assumes a simple shell wrapper for the notifier skill exists or uses a direct api call
            # For now, we'll write to a special file that the main agent checks during heartbeats
            with open("/home/ubuntu/human-ai/watchdog_alert.txt", "w") as f:
                f.write(message)
            print("Alert written to watchdog_alert.txt")
        except Exception as e:
            print(f"Failed to write alert: {e}")
