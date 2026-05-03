import os
import json
from typing import Any, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import firebase_admin
from firebase_admin import credentials, firestore, storage

# Load environment variables from .env file
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORK_DIR = os.getenv("WORK_DIR", str(PROJECT_ROOT))
load_dotenv(Path(WORK_DIR) / '.env')

class StorageOrchestrator:
    def __init__(self):
        # Supabase Setup
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase = create_client(self.supabase_url, self.supabase_key) if self.supabase_url else None
        
        # Firebase Setup
        self.firebase_key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        self.firebase_bucket = os.getenv("FIREBASE_STORAGE_BUCKET")
        self.firebase_enabled = False
        
        if self.firebase_key_path and os.path.exists(self.firebase_key_path):
            try:
                import firebase_admin
                from firebase_admin import credentials, firestore, storage
                if not firebase_admin._apps:
                    cred = credentials.Certificate(self.firebase_key_path)
                    firebase_admin.initialize_app(cred, {
                        'storageBucket': self.firebase_bucket
                    })
                self.db = firestore.client()
                self.bucket = storage.bucket()
                self.firebase_enabled = True
            except Exception as e:
                print(f"❌ Firebase Init Error: {e}")

    def save_finding(self, topic: str, content: str, metadata: Dict[str, Any] = None):
        """
        Save a research finding. 
        Primary: Supabase (Relational/RAG)
        Backup: Firebase Firestore (NoSQL/Recovery)
        """
        # 1. Save to Supabase (Matches schema: topic, content)
        success_supabase = False
        if self.supabase:
            try:
                self.supabase.table('research_findings').insert({
                    'topic': topic, 
                    'content': content
                }).execute()
                success_supabase = True
            except Exception as e:
                print(f"⚠️ Supabase Save Failed: {e}")

        # 2. Save to Firebase as Backup (Firestore allows flexible schema)
        if self.firebase_enabled:
            try:
                doc_ref = self.db.collection('research_findings').document(topic.replace(" ", "_"))
                doc_ref.set({
                    "content": content,
                    "metadata": metadata,
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "synced_to_supabase": success_supabase
                })
            except Exception as e:
                print(f"⚠️ Firebase Backup Failed: {e}")

        return success_supabase

    def retrieve_findings(self, topic: str, limit: int = 5) -> Optional[list]:
        """
        Retrieve previously saved research findings from Supabase.
        """
        if not self.supabase:
            print("❌ Supabase not enabled. Cannot retrieve findings.")
            return None
            
        try:
            # Query the research_findings table for entries matching the topic
            response = self.supabase.table('research_findings')\
                .select('*')\
                .ilike('topic', f'%{topic}%')\
                .limit(limit)\
                .execute()
            
            return response.data
        except Exception as e:
            print(f"⚠️ Supabase Retrieval Failed: {e}")
            return None

if __name__ == "__main__":
    orch = StorageOrchestrator()
    print(f"Storage System Initialized. Firebase Enabled: {orch.firebase_enabled}")
