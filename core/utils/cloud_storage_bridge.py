import os
import json
from typing import Any, Dict, Optional
from supabase import create_client, Client
import firebase_admin
from firebase_admin import credentials, db

class CloudStorageBridge:
    """
    Centralized bridge to mirror agent outputs to Supabase (per-agent tables) 
    and Firebase (global backup).
    """
    def __init__(self):
        # Load credentials from environment
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        
        # Initialize Supabase
        self.supabase: Optional[Client] = None
        if self.supabase_url and self.supabase_key:
            try:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
            except Exception as e:
                print(f"❌ Supabase Init Error: {e}")

        # Initialize Firebase
        try:
            if not firebase_admin._apps:
                if self.firebase_json and os.path.exists(self.firebase_json):
                    cred = credentials.Certificate(self.firebase_json)
                    firebase_admin.initialize_app(cred, {
                        'databaseURL': f'https://{os.getenv("FIREBASE_PROJECT_ID")}.firebaseio.com'
                    })
        except Exception as e:
            print(f"❌ Firebase Init Error: {e}")

    def push_output(self, agent_name: str, task_id: str, data: Any):
        """
        Mirrors output to Supabase (agent-specific table) and Firebase.
        """
        payload = {
            "task_id": task_id,
            "content": data,
            "timestamp": "now()" # handled by DB
        }

        # 1. Push to Supabase (Per-Agent Table)
        if self.supabase:
            try:
                table_name = f"agent_{agent_name.lower().replace(' ', '_')}_outputs"
                # Note: Supabase JS/Python clients don't support 'CREATE TABLE' directly via API
                # We assume tables are pre-created or use a generic 'swarm_outputs' table.
                # To strictly follow 'separate tables', we'll attempt the insert.
                self.supabase.table(table_name).insert(payload).execute()
            except Exception as e:
                print(f"❌ Supabase push failed for {agent_name}: {e}")

        # 2. Push to Firebase (Global Backup)
        try:
            ref = db.reference(f'swarm_backups/{agent_name}/{task_id}')
            ref.set(payload)
        except Exception as e:
            print(f"❌ Firebase backup failed for {agent_name}: {e}")

# Singleton instance
cloud_bridge = CloudStorageBridge()
