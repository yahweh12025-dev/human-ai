import time
import subprocess
import os
import sys
from datetime import datetime

# Path to the agent and the log we want to capture
AGENT_PATH = '/home/yahwehatwork/human-ai/agents/trading-agent/trading_agent.py'
PYTHON_EXE = '/home/yahwehatwork/human-ai/agents/trading-agent/venv/bin/python'
# UPDATED: Log to masterlog.md in agent-review
MASTER_LOG = '/home/yahwehatwork/human-ai/agents/trading-agent/agent-review/masterlog.md'
WORKDIR = '/home/yahwehatwork/human-ai/agents/trading-agent/'

def run_agent_with_logging():
    # Ensure the directory exists
    os.makedirs(os.path.dirname(MASTER_LOG), exist_ok=True)
    
    print(f"🚀 Starting Trading Agent for 30 minutes...")
    print(f"📝 Logging to: {MASTER_LOG}")
    
    # Start the agent as a subprocess with the correct working directory
    process = subprocess.Popen(
        [PYTHON_EXE, AGENT_PATH],
        cwd=WORKDIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    start_time = time.time()
    duration = 30 * 60 # 30 minutes
    
    # Open log in append mode
    with open(MASTER_LOG, 'a') as log_file:
        log_file.write(f"\n\n## Session Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write("Running for 30 minutes using Alpaca API...\n\n")
        
        try:
            while time.time() - start_time < duration:
                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        log_file.write(f"⚠️ Agent process terminated unexpectedly with code {process.returncode}\n")
                        break
                    continue
                
                log_file.write(line)
                log_file.flush()
        except KeyboardInterrupt:
            print("Stopping agent early...")
        finally:
            process.terminate()
            log_file.write(f"\n\n## Session End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write("Duration completed or process terminated.\n")
            log_file.flush()

if __name__ == '__main__':
    run_agent_with_logging()
