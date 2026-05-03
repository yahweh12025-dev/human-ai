import os
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

# Setup logging to file for debugging
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORK_DIR = os.getenv("WORK_DIR", str(PROJECT_ROOT))
LOG_DIR = Path(WORK_DIR) / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "agent_responses.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_FILE)),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ResponseLogger:
    """
    Handles redundant storage of AI agent responses to Supabase and Firebase.
    Added local file logging for debugging.
    """
    def __init__(self):
        self.supabase_client = None
        self.firebase_client = None
        self._init_supabase()
        self._init_firebase()

    def _init_supabase(self):
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                import supabase
                self.supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("✅ Supabase logger initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Supabase: {e}")

    def _init_firebase(self):
        FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
        if FIREBASE_PROJECT_ID:
            try:
                import firebase_admin
                from firebase_admin import credentials, firestore
                if not firebase_admin._app:
                    cred = credentials.ApplicationDefault()
                    firebase_admin.initialize_app(cred)
                self.firebase_client = firestore.client()
                logger.info("✅ Firebase logger initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Firebase: {e}")

    async def log_response(self, agent_name: str, prompt: str, raw_response: str, cleaned_response: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Saves the interaction to both Supabase and Firebase, and also to a local log file.
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_name": agent_name,
            "prompt": prompt,
            "raw_response": raw_response,
            "cleaned_response": cleaned_response,
            "metadata": metadata or {}
        }

        # Local File Logging (Crucial for debugging)
        try:
            with open("/home/yahwehatwork/human-ai/logs/agent_responses.log", "a") as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"TIMESTAMP: {log_entry['timestamp']}\n")
                f.write(f"AGENT: {agent_name}\n")
                f.write(f"PROMPT: {prompt}\n")
                f.write(f"RAW: {raw_response}\n")
                f.write(f"CLEANED: {cleaned_response}\n")
                f.write(f"METADATA: {metadata}\n")
                f.write(f"{'='*50}\n")
        except Exception as e:
            logger.error(f"❌ Local file logging failed: {e}")

        # 1. Store in Supabase (SQL)
        if self.supabase_client:
            try:
                self.supabase_client.table("agent_logs").insert(log_entry).execute()
            except Exception as e:
                logger.error(f"❌ Supabase log failed: {e}")

        # 2. Store in Firebase (NoSQL)
        if self.firebase_client:
            try:
                self.firebase_client.collection("agent_logs").add(log_entry)
            except Exception as e:
                logger.error(f"❌ Firebase log failed: {e}")

# Singleton instance for easy import
response_logger = ResponseLogger()
