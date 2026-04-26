#!/usr/bin/env python3
"""
Human AI: MCP Bridge - v1.0
Integrates n8n deterministic workflows into the swarm via Model Context Protocol (MCP).
Ensures that repetitive, high-reliability tasks are handled by n8n rather than LLMs.
"""

import os
import requests
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv('/home/yahwehatwork/human-ai/.env')

class MCPBridge:
    def __init__(self):
        self.n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL")
        self.mcp_api_key = os.getenv("MCP_API_KEY")
        self.enabled = True if self.n8n_webhook_url else False
        
        if not self.enabled:
            print("⚠️ MCP Bridge partially disabled: N8N_WEBHOOK_URL not configured.")

    def trigger_workflow(self, workflow_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Triggers a specific n8n workflow via MCP webhook.
        """
        if not self.enabled:
            return {"status": "error", "message": "MCP Bridge not enabled."}

        # Construct the webhook URL for the specific workflow
        url = f"{self.n8n_webhook_url}/{workflow_id}"
        
        headers = {
            "Authorization": f"Bearer {self.mcp_api_key}" if self.mcp_api_key else "",
            "Content-Type": "application/json"
        }
        
        try:
            print(f"⚙️ Triggering n8n workflow: {workflow_id}...")
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            return {
                "status": "success",
                "response": response.json() if response.text else "Workflow triggered successfully."
            }
        except Exception as e:
            print(f"❌ n8n Workflow Error: {e}")
            return {"status": "error", "message": str(e)}

    def get_workflow_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Polls n8n for the status of a specific execution.
        """
        if not self.enabled:
            return {"status": "error", "message": "MCP Bridge not enabled."}

        url = f"{self.n8n_webhook_url}/status/{execution_id}"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Status Poll Error: {e}")
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    bridge = MCPBridge()
    print(f"MCP Bridge Initialized. Enabled: {bridge.enabled}")
