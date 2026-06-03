import os
from dotenv import load_dotenv
from supabase import create_client

def sync_backup_key():
    load_dotenv('/home/ubuntu/human-ai/.env')
    
    key_val = os.getenv("OPENROUTER_API_KEY_BACKUP")
    s_url = os.getenv("SUPABASE_URL")
    s_key = os.getenv("SUPABASE_KEY")
    
    if not key_val:
        print("❌ Backup key not found in .env")
        return

    try:
        supabase = create_client(s_url, s_key)
        # Trying 'name' and 'value' as common alternatives
        supabase.table('vault_secrets').upsert({
            "name": "OPENROUTER_API_KEY_BACKUP",
            "value": key_val
        }).execute()
        print("✅ Backup key synced to Supabase Vault (using name/value).")
    except Exception as e:
        print(f"❌ Sync error: {e}")

if __name__ == "__main__":
    sync_backup_key()
