import os
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Config
INFISICAL_TOKEN = os.getenv("INFISICAL_SERVICE_TOKEN")
INFISICAL_PROJECT_ID = os.getenv("INFISICAL_PROJECT_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def fetch_infisical_secrets():
    print("🔑 Fetching secrets from Infisical...")
    url = f"https://app.infisical.com/api/v1/secrets/project/{INFISICAL_PROJECT_ID}"
    headers = {"X-Api-Key": INFISICAL_TOKEN}
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json().get('secrets', [])
    except Exception as e:
        print(f"❌ Infisical fetch error: {e}")
        return []

def sync_to_supabase(secrets):
    print(f"📦 Syncing {len(secrets)} secrets to Supabase Vault...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    for s in secrets:
        secret_name = s.get('secret_name')
        secret_value = s.get('secret_value')
        
        if not secret_name or not secret_value:
            continue
            
        try:
            # Upsert into vault_secrets
            # Note: Table schema assumed to have 'secret_name' and 'secret_value'
            supabase.table('vault_secrets').upsert({
                "secret_name": secret_name,
                "secret_value": secret_value
            }).execute()
            print(f"✅ Synced: {secret_name}")
        except Exception as e:
            print(f"❌ Supabase sync error for {secret_name}: {e}")

if __name__ == "__main__":
    secrets = fetch_infisical_secrets()
    if secrets:
        sync_to_supabase(secrets)
        print("🎉 Sync complete!")
    else:
        print("⚠️ No secrets found to sync.")
