import os
from dotenv import load_dotenv
import requests
from supabase import create_client

def run_sync():
    load_dotenv('/home/ubuntu/human-ai/.env')
    
    # Get config
    token = os.getenv("INFISICAL_SERVICE_TOKEN")
    project_id = os.getenv("INFISICAL_PROJECT_ID")
    s_url = os.getenv("SUPABASE_URL")
    s_key = os.getenv("SUPABASE_KEY")
    
    print(f"Config: ProjectID={project_id[:5]}... Token={token[:5]}...")
    
    if not all([token, project_id, s_url, s_key]):
        print("❌ Missing environment variables")
        return

    # Fetch from Infisical
    url = f"https://app.infisical.com/api/v1/secrets/project/{project_id}"
    headers = {"X-Api-Key": token}
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        secrets = resp.json().get('secrets', [])
        print(f"Fetched {len(secrets)} secrets.")
        
        # Sync to Supabase
        supabase = create_client(s_url, s_key)
        for s in secrets:
            name = s.get('secret_name')
            val = s.get('secret_value')
            if name and val:
                supabase.table('vault_secrets').upsert({"secret_name": name, "secret_value": val}).execute()
                print(f"✅ Synced {name}")
        print("🎉 Sync complete!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_sync()
