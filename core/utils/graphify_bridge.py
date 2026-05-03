#!/usr/bin/env python3
"""
Human AI: Graphify Bridge - v1.0
Synchronizes distilled knowledge between Dify (RAG) and Graphify (Knowledge Graph).
Implements the 'Symmetry' pipeline to ensure relational intelligence is preserved.
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORK_DIR = os.getenv("WORK_DIR", str(PROJECT_ROOT))
load_dotenv(Path(WORK_DIR) / '.env')

class GraphifyBridge:
    def __init__(self):
        # Dify Configuration
        self.dify_api_key = os.getenv("DIFY_API_KEY")
        self.dify_base_url = os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1")
        
        # Graphify Configuration
        self.graphify_api_key = os.getenv("GRAPHIFY_API_KEY")
        self.graphify_url = os.getenv("GRAPHIFY_URL", "https://api.graphify.ai/v1")
        
        self.enabled = True if self.dify_api_key and self.graphify_api_key else False
        if not self.enabled:
            print("⚠️ Graphify Bridge partially disabled: Missing DIFY or GRAPHIFY API keys.")

    def query_graph(self, query: str) -> List[Dict[str, str]]:
        """
        Query the Graphify Knowledge Graph for triples matching the query.
        Returns a list of triples (subject, predicate, object).
        """
        if not self.graphify_api_key:
            return []
        
        try:
            headers = {"Authorization": f"Bearer {self.graphify_api_key}", "Content-Type": "application/json"}
            # Assuming Graphify has a query endpoint for triples
            params = {"query": query}
            resp = requests.get(f"{self.graphify_url}/triples", headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json().get("triples", [])
        except Exception as e:
            print(f"❌ Graphify Query Error: {e}")
            return []

    def distill_to_triples(self, text: str) -> List[Dict[str, str]]:
        """
        Transforms raw text into Knowledge Graph Triples (Subject -> Predicate -> Object).
        Uses the designated free-model routing to avoid direct costs.
        """
        # Logic: Prompt a free model to extract triples from the text
        # To avoid direct API calls here, we assume the Bridge is called by the 
        # Orchestrator which handles the model routing.
        # For internal logic, we'll return a structured request for the router.
        return {
            "action": "extract_triples",
            "content": text
        }

    def sync_to_graph(self, triples: List[Dict[str, str]]):
        """
        Pushes extracted triples into the Graphify Knowledge Graph.
        """
        if not self.graphify_api_key:
            return False

        try:
            headers = {"Authorization": f"Bearer {self.graphify_api_key}", "Content-Type": "application/json"}
            payload = {"triples": triples}
            resp = requests.post(f"{self.graphify_url}/nodes", headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"❌ Graphify Sync Error: {e}")
            return False

    def bridge_dify_to_graph(self, topic: str):
        """
        The Symmetry Pipeline: 
        1. Pulls high-density context from Dify.
        2. Distills it into a relational graph.
        3. Updates Graphify.
        """
        from core.utils.dify_brain import DifyBrain
        brain = DifyBrain()
        
        print(f"🔄 Bridging Dify $\rightarrow$ Graphify for topic: {topic}")
        context = brain.query(topic)
        
        if not context or "Error" in context:
            print("❌ Dify query failed. Bridge aborted.")
            return False
            
        # In a real flow, the Bridge asks the Omni-Router to convert 'context' to triples
        # For now, we implement the structured request
        triples_request = self.distill_to_triples(context)
        
        # Simulating the Graphify push
        # In production, this would be the result of the LLM's triple extraction
        mock_triples = [{"subject": topic, "predicate": "is_documented_in", "object": "DifyBrain"}]
        
        return self.sync_to_graph(mock_triples)

if __name__ == "__main__":
    bridge = GraphifyBridge()
    print(f"Graphify Bridge Initialized. Enabled: {bridge.enabled}")
