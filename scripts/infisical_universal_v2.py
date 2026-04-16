import os
import requests
from dotenv import load_dotenv
from supabase import create_client

def sync_infisical_universal_v2():
    load_dotenv('/home/ubuntu/human-ai/.env')
    
    client_id = os.getenv("INFISICAL_CLIENT_ID")
    client_secret = os.getenv("INFISICAL_CLIENT_SECRET")
    project_id = os.getenv("INFISICAL_PROJECT_ID")
    s_url = os.getenv("SUPABASE_URL")
    s_key = os.getenv("SUPABASE_KEY")
    
    print(f"🔐 Attempting Universal Auth login...")
    auth_url = "https://app.infisical.com/api/v1/auth/universal-auth/login"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {'clientId': client_id, 'clientSecret': client_secret}
    
    try:
        auth_resp = requests.post(auth_url, headers=headers, data=payload, timeout=15)
        auth_resp.raise_for_status()
        token = auth_resp.json().get('token')
        print("✅ Token acquired.")
        
        # Use v2 List Secrets endpoint
        print(f"📦 Fetching secrets via v2 list endpoint...")
        secrets_url = "https://app.infisical.com/api/v2/secrets/list"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"workspaceId": project_id, "environment": "dev"}
        
        secrets_resp = requests.post(secrets_url, headers=headers, json=payload, timeout=15)
        secrets_resp.raise_for_status()
        secrets = secrets_resp.json().get('secrets', [])
        print(f"Found {len(secrets)} secrets.")
        
        if s_url and s_key:
            supabase = create_client(s_url, s_key)
            for s in secrets:
                name = s.get('secret_name')
                val = s.get('secret_value')
                if name and val:
                    supabase.table('swarm_secrets').upsert({"name": name, "value": val}).execute()
            print("🎉 Sync complete!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    sync_infisical_universal_v2()
