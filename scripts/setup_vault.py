import os
from dotenv import load_dotenv
from supabase import create_client

def setup_vault():
    load_dotenv('/home/ubuntu/human-ai/.env')
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    
    # We use a RPC or a dummy update to check for existence, 
    # but since I can't run raw SQL directly from the Python client's top level,
    # I'll try to just insert into a table and handle the error.
    
    key_val = os.getenv("OPENROUTER_API_KEY_BACKUP")
    try:
        supabase.table('secrets_vault').upsert({"key": "OPENROUTER_API_KEY_BACKUP", "value": key_val}).execute()
        print("✅ Backup key synced to secrets_vault.")
    except Exception as e:
        print(f"❌ Table may not exist: {e}")

if __name__ == "__main__":
    setup_vault()
