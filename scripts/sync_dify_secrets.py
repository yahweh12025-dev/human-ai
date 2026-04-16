import os
from dotenv import load_dotenv
from supabase import create_client

def sync_dify_secrets():
    load_dotenv('/home/ubuntu/human-ai/.env')
    
    dify_url = os.getenv("DIFY_BASE_URL")
    dify_key = os.getenv("DIFY_API_KEY")
    s_url = os.getenv("SUPABASE_URL")
    s_key = os.getenv("SUPABASE_KEY")
    
    if not all([dify_url, dify_key, s_url, s_key]):
        print("❌ Missing credentials in .env")
        return

    try:
        supabase = create_client(s_url, s_key)
        secrets = {
            "DIFY_BASE_URL": dify_url,
            "DIFY_API_KEY": dify_key
        }
        
        for name, value in secrets.items():
            # Using vault_secrets with assumed columns secret_name and secret_value
            supabase.table('vault_secrets').upsert({"secret_name": name, "secret_value": value}).execute()
            print(f"✅ Synced {name} to vault_secrets.")
            
    except Exception as e:
        print(f"❌ Sync error: {e}")

if __name__ == "__main__":
    sync_dify_secrets()
