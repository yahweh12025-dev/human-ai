import os
import requests
from dotenv import load_dotenv
from supabase import create_client

def sync_infisical_v2():
    load_dotenv('/home/ubuntu/human-ai/.env')
    
    client_id = os.getenv("INFISICAL_CLIENT_ID")
    client_secret = os.getenv("INFISICAL_CLIENT_SECRET")
    project_id = os.getenv("INFISICAL_PROJECT_ID")
    s_url = os.getenv("SUPABASE_URL")
    s_key = os.getenv("SUPABASE_KEY")
    
    print(f"🔐 Attempting Infisical v2 Machine Auth...")
    
    # v2 Machine Identity Auth Endpoint
    auth_url = "https://app.infisical.com/api/v2/auth/machine-identity/authenticate"
    auth_payload = {
        "clientId": client_id,
        "clientSecret": client_secret
    }
    
    try:
        auth_resp = requests.post(auth_url, json=auth_payload, timeout=15)
        if auth_resp.status_code == 404:
            print("❌ v2 endpoint also 404. The API structure has changed.")
            return
        auth_resp.raise_for_status()
        token = auth_resp.json().get('token')
        
        # Fetch Secrets via v2
        secrets_url = f"https://app.infisical.com/api/v2/secrets/list"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"workspaceId": project_id, "environment": "dev"}
        
        secrets_resp = requests.post(secrets_url, headers=headers, json=payload, timeout=15)
        secrets_resp.raise_for_status()
        secrets = secrets_resp.json().get('secrets', [])
        
        # Sync to Supabase
        if s_url and s_key:
            supabase = create_client(s_url, s_key)
            for s in secrets:
                name = s.get('secret_name')
                val = s.get('secret_value')
                if name and val:
                    supabase.table('swarm_secrets').upsert({"name": name, "value": val}).execute()
            print(f"🎉 Successfully synced {len(secrets)} secrets to Supabase!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    sync_infisical_v2()
