import json
import os
import fcntl
from datetime import datetime
from pathlib import Path

class SwarmMasterLog:
    def __init__(self, log_path=None):
        if log_path is None:
            PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
            WORK_DIR = os.getenv("WORK_DIR", str(PROJECT_ROOT))
            log_path = Path(WORK_DIR) / "master_log.json"
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
         
        # Load existing log with file locking
        logs = []
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        logs = json.load(f)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except:
                logs = []
         
        logs.append(entry)
         
        # Save back to file with file locking
        with open(self.log_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(logs, f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
         
        print(f"📝 MasterLog [{source}]: {message}")

if __name__ == "__main__":
    logger = SwarmMasterLog()
    logger.log_event("System", "INIT", "Master Log System initialized.")
