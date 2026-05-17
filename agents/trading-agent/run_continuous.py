import time
import subprocess
import os
import sys
from datetime import datetime

# Path to the agent and the log we want to capture
AGENT_PATH = '/home/yahwehatwork/human-ai/agents/trading-agent/trading_agent.py'
PYTHON_EXE = '/home/yahwehatwork/human-ai/agents/trading-agent/venv/bin/python'
MASTER_LOG = '/home/yahwehatwork/human-ai/agents/trading-agent/agent-review/masterlog.md'
WORKDIR = '/home/yahwehatwork/human-ai/agents/trading-agent/'

def run_agent_continuously():
    # Ensure the directory exists
    os.makedirs(os.path.dirname(MASTER_LOG), exist_ok=True)
    
    print(f"🚀 Starting Trading Agent in CONTINUOUS mode...")
    print(f"📝 Logging to: {MASTER_LOG}")
    
    while True:
        print(f"Launching agent process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
        
        # Start the agent as a subprocess with the correct working directory
        process = subprocess.Popen(
            [PYTHON_EXE, AGENT_PATH],
            cwd=WORKDIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        with open(MASTER_LOG, 'a') as log_file:
            log_file.write(f"\n\n## Continuous Session Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            try:
                while True:
                    line = process.stdout.readline()
                    if not line:
                        if process.poll() is not None:
                            log_file.write(f"⚠️ Agent process terminated unexpectedly with code {process.returncode}. Restarting in 10 seconds...\n")
                            break
                        continue
                    
                    log_file.write(line)
                    log_file.flush()
            except KeyboardInterrupt:
                print("Manual stop signal received. Terminating agent...")
                process.terminate()
                log_file.write(f"\n\n## Manual Stop: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                sys.exit(0)
            except Exception as e:
                log_file.write(f"Unexpected error in monitor loop: {e}\n")
        
        # Brief cooldown before restarting to prevent rapid-fire crash loops
        time.sleep(10)

if __name__ == '__main__':
    run_agent_continuously()
