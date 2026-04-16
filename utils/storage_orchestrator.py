import os
import json
from typing import Any, Dict, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv('/home/ubuntu/human-ai/.env')

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
        success_supabase = False
        if self.supabase:
            try:
                self.supabase.table('research_findings').insert({'topic': topic, 'content': content, 'metadata': metadata}).execute()
                success_supabase = True
            except Exception as e:
                print(f"⚠️ Supabase Save Failed: {e}")

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

    def upload_large_file(self, file_path: str, destination_blob_name: str):
        """
        Saves large files exclusively to Firebase Storage to avoid Supabase bloat.
        """
        if not self.firebase_enabled:
            print("❌ Firebase not enabled. Cannot upload large file.")
            return None
            
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_filename(file_path)
            return blob.public_url
        except Exception as e:
            print(f"❌ Firebase Upload Failed: {e}")
            return None

if __name__ == "__main__":
    orch = StorageOrchestrator()
    print(f"Storage System Initialized. Firebase Enabled: {orch.firebase_enabled}")
