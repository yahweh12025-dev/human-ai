#!/usr/bin/env python3
"""
Env-Request Manager Skill
Controlled process for agents to request and receive new .env keys via a secure request log.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class EnvRequestManager:
    def __init__(self, log_file: str = "/home/ubuntu/human-ai/logs/env_request_log.md"):
        """
        Initialize the Env-Request Manager.
        
        Args:
            log_file: Path to the request log file. Defaults to /home/ubuntu/human-ai/logs/env_request_log.md
        """
        self.log_file = Path(log_file)
        # Ensure the log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize the log file with a header if it doesn't exist
        if not self.log_file.exists():
            self._initialize_log_file()

    def _initialize_log_file(self):
        """Create the log file with a header if it doesn't exist."""
        header = """# Environment Variable Request Log

This log records requests for new environment variables (e.g., API keys) made by agents.
Requests are reviewed and approved by a human or trusted agent.

## Format
Each request is logged as:
- **Timestamp**: ISO 8601 format
- **Agent ID**: The ID of the agent making the request
- **Variable Name**: The name of the environment variable being requested (e.g., OPENAI_API_KEY)
- **Justification**: Reason why the variable is needed

---

"""
        self.log_file.write_text(header, encoding='utf-8')
        print(f"📝 Initialized request log: {self.log_file}")

    def log_request(self, variable_name: str, justification: str, agent_id: str = "unknown") -> bool:
        """
        Log a request for a new environment variable.
        
        Args:
            variable_name: The name of the environment variable being requested (e.g., OPENAI_API_KEY)
            justification: Reason why the variable is needed
            agent_id: The ID of the agent making the request (defaults to "unknown")
            
        Returns:
            True if the request was logged successfully, False otherwise
        """
        try:
            # Validate inputs
            if not variable_name or not variable_name.strip():
                print("❌ Error: Variable name cannot be empty")
                return False
                
            if not justification or not justification.strip():
                print("❌ Error: Justification cannot be empty")
                return False
            
            # Create the log entry
            timestamp = datetime.utcnow().isoformat() + "Z"  # UTC time
            entry = f"- **Timestamp**: {timestamp}\n"
            entry += f"  - **Agent ID**: {agent_id}\n"
            entry += f"  - **Variable Name**: {variable_name.strip()}\n"
            entry += f"  - **Justification**: {justification.strip()}\n"
            entry += "\n---\n\n"
            
            # Append to the log file (append-only for security)
            with self.log_file.open('a', encoding='utf-8') as f:
                f.write(entry)
            
            print(f"📝 Logged request for {variable_name} by agent {agent_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error logging env request: {e}")
            return False

    def get_recent_requests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve recent requests from the log (for review purposes).
        NOTE: This method is intended for human/trusted agent review only.
        Regular agents should NOT use this to check if their request was fulfilled.
        
        Args:
            limit: Maximum number of recent requests to return
            
        Returns:
            List of request dictionaries (most recent first)
        """
        try:
            if not self.log_file.exists():
                return []
                
            content = self.log_file.read_text(encoding='utf-8')
            # Simple parsing - in a production system, this would be more robust
            # For now, we'll return a placeholder indicating the log exists
            return [{"note": "Log exists and contains requests. Manual review recommended."}]
        except Exception as e:
            print(f"❌ Error reading request log: {e}")
            return []

# Example usage for testing
if __name__ == "__main__":
    import asyncio
    
    async def test():
        manager = EnvRequestManager()
        
        # Log a test request
        success = manager.log_request(
            "OPENAI_API_KEY", 
            "Need GPT-4o access to improve paper summarization and reasoning capabilities for the swarm.",
            "test-agent-001"
        )
        
        if success:
            print("✅ Test request logged successfully")
        else:
            print("❌ Failed to log test request")
    
    asyncio.run(test())