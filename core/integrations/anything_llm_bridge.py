import os
import requests
from typing import Optional, Dict, Any, List
import logging
from dotenv import load_dotenv
from .base_bridge import BridgeInterface

# Load environment variables from .env files
load_dotenv()

logger = logging.getLogger(__name__)

class AnythingLLMBridge(BridgeInterface):
    """Bridge to connect OpenClaw to a local AnythingLLM instance."""
    
    def __init__(self, api_key: Optional[str] = None, endpoint: str = "http://localhost:3001/api/v1"):
        self.endpoint = endpoint
        self.api_key = api_key or os.getenv('ANYTHINGLLM_API_KEY')
        
        if not self.api_key:
            raise ValueError("ANYTHINGLLM_API_KEY not found in environment variables.")

    def initialize(self, query_params: Dict[str, Any]):
        """Initialize bridge with query parameters"""
        self.api_key = query_params.get('api_key', self.api_key)
        self.endpoint = query_params.get('endpoint', self.endpoint)

    def get_workspaces(self) -> List[Dict[str, Any]]:
        """Fetch all available workspaces."""
        url = f"{self.endpoint}/workspaces"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.handle_error(e)
            return []

    def query(self, data_source: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute query against data source (AnythingLLM workspace)"""
        # Mapping original 'prompt' to 'query' for interface compliance
        # Note: query in interface expects params, here we use workspace_slug from params
        prompt_text = params.get('prompt_text')
        workspace_slug = params.get('workspace_slug')
        
        if not prompt_text:
            raise ValueError("prompt_text is required for AnythingLLM query")

        return self.retrieve_data({"prompt_text": prompt_text, "workspace_slug": workspace_slug})

    def retrieve_data(self, results: Dict[str, Any]) -> str:
        """Process and return retrieved data (the chat response)"""
        prompt_text = results.get("prompt_text")
        workspace_slug = results.get("workspace_slug")

        if not workspace_slug:
            workspaces = self.get_workspaces()
            if workspaces and len(workspaces) > 0:
                workspace_slug = workspaces[0].get('slug', 'my-workspace')
            else:
                workspace_slug = 'my-workspace'
        
        url = f"{self.endpoint}/workspace/{workspace_slug}/chat"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "message": prompt_text,
            "mode": "chat"
        }
        
        try:
            with requests.Session() as session:
                response = session.post(url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                data = response.json()
                return data.get('textResponse', "Error: No text response received from AnythingLLM.")
        except Exception as e:
            return self.handle_error(e)

    def handle_error(self, error: Exception) -> str:
        """Standardized error handling"""
        msg = f"AnythingLLM API Error: {error}"
        logger.error(msg)
        return msg

    def close(self):
        """Close any connections"""
        pass
