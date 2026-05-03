import os
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv

class DifyBrain:
    def __init__(self):
        load_dotenv('/home/ubuntu/human-ai/.env')
        self.api_key = os.getenv("DIFY_API_KEY")
        self.dataset_id = os.getenv("DIFY_DATASET_ID")
        self.base_url = os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1")
        
    def query(self, query: str) -> str:
        """Queries the Dify Knowledge Base for existing information."""
        if not self.api_key:
            return "Error: DIFY_API_KEY not configured."
            
        print(f"🧠 Querying Brain: {query[:50]}...")
        url = f"{self.base_url}/chat-messages"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "inputs": {},
            "query": query,
            "response_mode": "blocking",
            "user": "human-ai-swarm"
        }
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json().get('answer', "No answer found in the brain.")
        except Exception as e:
            return f"Brain Query Error: {e}"

    def index_finding(self, content: str, metadata: Dict[str, Any]):
        """Indexes a research finding into the Dify Knowledge Base."""
        if not self.api_key or not self.dataset_id:
            print("Error: DIFY_API_KEY or DIFY_DATASET_ID not configured.")
            return
            
        print("📦 Indexing finding into the Brain...")
        url = f"{self.base_url}/datasets/{self.dataset_id}/document/create_by_text"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "name": metadata.get('title', 'Unnamed Finding'),
            "text": content,
            "indexing_technique": "high_quality",
            "process_rule": {"mode": "automatic"}
        }
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            print("✅ Finding indexed successfully.")
        except Exception as e:
            print(f"❌ Indexing Error: {e}")

if __name__ == "__main__":
    brain = DifyBrain()
    print(brain.query("What is the current state of the swarm?"))
