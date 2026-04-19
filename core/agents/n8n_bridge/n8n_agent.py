#!/usr/bin/env python3
import os
import requests
import json
from typing import Dict, Any

class N8nAgent:
    def __init__(self):
        self.api_key = os.getenv("N8N_API_KEY")
        self.n8n_url = os.getenv("N8N_URL", "http://localhost:5678")

    async def trigger_workflow(self, workflow_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Triggers a specific n8n workflow and returns the result.
        """
        print(f"🌐 Triggering n8n workflow: {workflow_id}...")
        url = f"{self.n8n_url}/workflow/{workflow_id}/execute"
        headers = {
            "X-N8N-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ n8n workflow error: {e}")
            return {"status": "error", "error": str(e)}

async def main():
    agent = N8nAgent()
    print("✅ N8n Agent Initialized")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
