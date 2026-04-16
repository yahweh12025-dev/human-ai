import json
import os
from datetime import datetime
from pathlib import Path

class SwarmMasterLog:
    def __init__(self, log_path="/home/ubuntu/human-ai/master_log.json"):
        self.log_path = Path(log_path)
        self.log_file = self.log_path

    def log_event(self, source: str, event_type: str, message: str, metadata: dict = None):
        """
        Adds a structured event to the master log.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "type": event_type,
            "message": message,
            "metadata": metadata or {}
        }
        
        # Load existing log
        logs = []
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(entry)
        
        # Save back to file
        with open(self.log_file, 'w') as f:
            json.dump(logs, f, indent=2)
        
        print(f"📝 MasterLog [{source}]: {message}")

if __name__ == "__main__":
    logger = SwarmMasterLog()
    logger.log_event("System", "INIT", "Master Log System initialized.")
