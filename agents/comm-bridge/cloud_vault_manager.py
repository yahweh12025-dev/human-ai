#!/usr/bin/env python3
"""
Cloud Vault Manager
Handles secure synchronization of .env, .openclaw_history, and .infrastructure_vault 
to Supabase storage/database to eliminate local dependency.
"""
import os
import json
import base64
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class CloudVaultManager:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        if not self.url or not self.key:
            raise Exception("Supabase credentials missing from .env")
        self.supabase: Client = create_client(self.url, self.key)

    def _encrypt_data(self, data: str) -> str:
        # Placeholder for actual encryption. In a production swarm, 
        # we would use a master key from the user.
        return base64.b64encode(data.encode()).decode()

    def _decrypt_data(self, encrypted_data: str) -> str:
        return base64.b64decode(encrypted_data).decode()

    async def backup_to_cloud(self, file_path: str, vault_key: str):
        """Uploads a local sensitive file to Supabase as an encrypted blob."""
        path = Path(file_path)
        if not path.exists():
            print(f"File {file_path} not found. Skipping.")
            return
        
        content = path.read_text()
        encrypted = self._encrypt_data(content)
        
        data = {
            "vault_key": vault_key,
            "content": encrypted,
            "updated_at": "now()"
        }
        # Upsert into a 'cloud_vault' table
        self.supabase.table("cloud_vault").upsert(data).execute()
        print(f"✅ {vault_key} backed up to cloud vault.")

    async def restore_from_cloud(self, vault_key: str, destination_path: str):
        """Downloads and decrypts a file from Supabase to the local instance."""
        res = self.supabase.table("cloud_vault").select("content").eq("vault_key", vault_key).single().execute()
        if res.data:
            encrypted_content = res.data['content']
            decrypted = self._decrypt_data(encrypted_content)
            Path(destination_path).write_text(decrypted)
            print(f"✅ {vault_key} restored to {destination_path}.")
        else:
            print(f"❌ No cloud backup found for {vault_key}.")

async def main():
    vault = CloudVaultManager()
    # Map of local sensitive files to cloud keys
    files_to_sync = {
        "/home/ubuntu/.env": "system_env",
        "/home/ubuntu/human-ai/.openclaw_history/README.md": "history_readme",
        "/home/ubuntu/human-ai/.infrastructure_vault/manifest.json": "infra_manifest"
    }
    
    for path, key in files_to_sync.items():
        await vault.backup_to_cloud(path, key)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
