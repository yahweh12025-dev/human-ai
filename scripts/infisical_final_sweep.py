import os
import requests
from dotenv import load_dotenv
from supabase import create_client

def attempt_sync():
    load_dotenv('/home/ubuntu/human-ai/.env')
    
    client_id = os.getenv("INFISICAL_CLIENT_ID")
    client_secret = os.getenv("INFISICAL_CLIENT_SECRET")
    project_id = os.getenv("INFISICAL_PROJECT_ID")
    s_url = os.getenv("SUPABASE_URL")
    s_key = os.getenv("SUPABASE_KEY")
    
    # Test various endpoints to find the working one
    endpoints = [
        ("https://app.infisical.com/api/v1/auth/machine-identity/authenticate", "v1"),
        ("https://app.infisical.com/api/v2/auth/machine-identity/authenticate", "v2"),
        ("https://api.infisical.com/api/v1/auth/machine-identity/authenticate", "api-v1"),
        ("https://api.infisical.com/api/v2/auth/machine-identity/authenticate", "api-v2"),
    ]
    
    token = None
    version = None
    
    for url, ver in endpoints:
        print(f"Testing {ver} endpoint: {url}...")
        try:
            resp = requests.post(url, json={"clientId": client_id, "clientSecret": client_secret}, timeout=10)
            if resp.status_code == 200:
                token = resp.json().get('token')
                version = ver
                print(f"✅ Authenticated via {ver}!")
                break
            else:
                print(f"❌ {resp.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")

    if not token:
        print("🚨 All authentication endpoints failed. Please check the API access in Infisical settings.")
        return

    # Fetch secrets using the working token
    print(f"📦 Fetching secrets for project {project_id}...")
    # Attempt both v1 and v2 listing paths
    secrets_endpoints = [
        f"https://app.infisical.com/api/v1/secrets/project/{project_id}",
        f"https://app.infisical.com/api/v2/secrets/list" # v2 requires POST
    ]
    
    secrets = []
    for url in secrets_endpoints:
        try:
            if "v2" in url:
                resp = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, 
                                     json={"workspaceId": project_id, "environment": "dev"}, timeout=10)
            else:
                resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
                
            if resp.status_code == 200:
                secrets = resp.json().get('secrets', [])
                print(f"✅ Successfully retrieved {len(secrets)} secrets.")
                break
        except Exception as e:
            print(f"⚠️ Failed to fetch via {url}: {e}")

    if not secrets:
        print("⚠️ No secrets found or failed to retrieve secrets.")
        return

    # Sync to Supabase
    if s_url and s_key:
        print("🔄 Syncing to Supabase swarm_secrets...")
        supabase = create_client(s_url, s_key)
        for s in secrets:
            name = s.get('secret_name') if isinstance(s, dict) else getattr(s, 'secret_name', 'Unknown')
            val = s.get('secret_value') if isinstance(s, dict) else getattr(s, 'secret_value', 'Unknown')
            if name and val:
                try:
                    supabase.table('swarm_secrets').upsert({"name": name, "value": val}).execute()
                    print(f" - Synced {name}")
                except Exception as e:
                    print(f" - Supabase error for {name}: {e}")
        print("🎉 Sync complete!")

if __name__ == "__main__":
    attempt_sync()
