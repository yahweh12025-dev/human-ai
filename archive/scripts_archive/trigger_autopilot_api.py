import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
S_URL = os.getenv("OPENCLAW_URL", "http://localhost:18789")
# We use a generic payload that the Gateway's internal router accepts
# targeting the 'main' session directly.

def trigger():
    print(f"🚀 Sending direct API trigger to {S_URL}...")
    
    payload = {
        "target": "main",
        "message": "AUTONOMOUS_DEVELOPMENT_TRIGGER: Review /home/ubuntu/human-ai/ROADMAP.md. Identify the next pending task. Execute it fully. If a decision is needed, decide based on project goals. If a manual /approve or command is needed, log it to /home/ubuntu/human-ai/manual_actions/todo.log and proceed with other tasks if possible."
    }
    
    try:
        # We try the two most common internal OpenClaw endpoints
        endpoints = ["/message/send", "/gateway/update/run"]
        for ep in endpoints:
            try:
                resp = requests.post(f"{S_URL}{ep}", json=payload, timeout=5)
                if resp.status_code == 200:
                    print(f"✅ Success via {ep}!")
                    return True
            except:
                continue
        
        print("❌ All API endpoints failed. Please check if the Gateway is running.")
        return False
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        return False

if __name__ == "__main__":
    trigger()
