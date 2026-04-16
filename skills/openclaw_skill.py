# OPENCLAW INTEGRATION SKILL
# Goal: Provide a standardized way for any agent to prompt OpenClaw using free models for self-improvement and coordination.

import os
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class OpenClawSkill:
    def __init__(self):
        self.url = os.getenv("OPENCLAW_URL", "http://localhost:18789")
        self.token = os.getenv("OPENCLAW_TOKEN", "")
        self.default_model = os.getenv("OLLAMA_MODEL", "deepseek-r1:14b")

    def prompt_openclaw(self, prompt, model=None, system_prompt="You are a helpful assistant part of the Human AI Swarm."):
        """
        Sends a prompt to the OpenClaw Gateway.
        Can be used by agents to ask for help with their own code or to coordinate with others.
        """
        target_model = model or self.default_model
        headers = {
            "Authorization": f"Bearer {self.token}", 
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }

        try:
            response = requests.post(f"{self.url}/api/chat", json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            result = response.json()
            return result.get('response', result.get('text', 'No response returned from OpenClaw.'))
        except Exception as e:
            return f"❌ OpenClaw Error: {str(e)}"

if __name__ == "__main__":
    print("OpenClaw Integration Skill Loaded. Agents can now access the Gateway for self-improvement.")
