import os
import requests
from dotenv import load_dotenv
from supabase import create_client

def sync_infisical_universal():
    load_dotenv('/home/ubuntu/human-ai/.env')
    
    client_id = os.getenv("INFISICAL_CLIENT_ID")
    client_secret = os.getenv("INFISICAL_CLIENT_SECRET")
    project_slug = os.getenv("INFISICAL_PROJECT_SLUG")
    s_url = os.getenv("SUPABASE_URL")
    s_key = os.getenv("SUPABASE_KEY")
    
    if not all([client_id, client_secret, project_slug]):
        print("❌ Missing credentials in .env")
        return

    print(f"🔐 Attempting Universal Auth login...")
    
    auth_url = "https://app.infisical.com/api/v1/auth/universal-auth/login"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {
        'clientId': client_id,
        'clientSecret': client_secret
    }
    
    try:
        auth_resp = requests.post(auth_url, headers=headers, data=payload, timeout=15)
        if auth_resp.status_code != 200:
            print(f"❌ Auth failed: {auth_resp.status_code} - {auth_resp.text}")
            return
            
        token = auth_resp.json().get('token')
        print("✅ Universal Auth Successful! Token acquired.")
        
        # Fetch Secrets using the SLUG
        print(f"📦 Fetching secrets for project slug: {project_slug}...")
        secrets_url = f"https://app.infisical.com/api/v1/secrets/project/{project_slug}"
        headers = {"Authorization": f"Bearer {token}"}
        
        secrets_resp = requests.get(secrets_url, headers=headers, timeout=15)
        secrets_resp.raise_for_status()
        secrets = secrets_resp.json().get('secrets', [])
        print(f"Found {len(secrets)} secrets.")
        
        # Sync to Supabase
        if s_url and s_key:
            print("🔄 Syncing to Supabase swarm_secrets...")
            supabase = create_client(s_url, s_key)
            for s in secrets:
                name = s.get('secret_name')
                val = s.get('secret_value')
                if name and val:
                    try:
                        supabase.table('swarm_secrets').upsert({"name": name, "value": val}).execute()
                        print(f" - Synced {name}")
                    except Exception as e:
                        print(f" - Supabase error for {name}: {e}")
            print("🎉 Sync complete!")
        else:
            print("⚠️ Supabase config missing, skipping sync.")
            
    except Exception as e:
        print(f"❌ Error during Universal Auth flow: {e}")

if __name__ == "__main__":
    sync_infisical_universal()
