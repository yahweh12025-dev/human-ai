import os
import requests
from dotenv import load_dotenv
from supabase import create_client

def sync_infisical_machine_identity():
    load_dotenv('/home/ubuntu/human-ai/.env')
    
    # Credentials
    client_id = os.getenv("INFISICAL_CLIENT_ID")
    client_secret = os.getenv("INFISICAL_CLIENT_SECRET")
    project_id = os.getenv("INFISICAL_PROJECT_ID")
    s_url = os.getenv("SUPABASE_URL")
    s_key = os.getenv("SUPABASE_KEY")
    
    if not all([client_id, client_secret, project_id]):
        print("❌ Missing Infisical Machine Identity credentials in .env")
        return

    print(f"🔐 Authenticating with Infisical Machine Identity...")
    
    # 1. Authentication Handshake
    auth_url = "https://app.infisical.com/api/v1/auth/machine-identity/authenticate"
    auth_payload = {
        "clientId": client_id,
        "clientSecret": client_secret
    }
    
    try:
        auth_resp = requests.post(auth_url, json=auth_payload, timeout=15)
        auth_resp.raise_for_status()
        token = auth_resp.json().get('token')
        print("✅ Authenticated! Session token acquired.")
        
        # 2. Fetch Secrets
        print(f"📦 Fetching secrets for project {project_id}...")
        secrets_url = f"https://app.infisical.com/api/v1/secrets/project/{project_id}"
        headers = {"Authorization": f"Bearer {token}"}
        
        secrets_resp = requests.get(secrets_url, headers=headers, timeout=15)
        secrets_resp.raise_for_status()
        secrets = secrets_resp.json().get('secrets', [])
        print(f"Found {len(secrets)} secrets.")
        
        # 3. Sync to Supabase
        if s_url and s_key:
            print("🔄 Syncing to Supabase...")
            supabase = create_client(s_url, s_key)
            for s in secrets:
                name = s.get('secret_name')
                val = s.get('secret_value')
                if name and val:
                    try:
                        # Using a generic approach since vault_secrets schema was uncertain
                        # We'll attempt a simple insert into a dedicated 'swarm_secrets' table
                        supabase.table('swarm_secrets').upsert({"name": name, "value": val}).execute()
                        print(f" - Synced {name}")
                    except Exception as e:
                        print(f" - Supabase error for {name}: {e}")
            print("🎉 Sync complete!")
        else:
            print("⚠️ Supabase config missing, skipping sync.")
            
    except Exception as e:
        print(f"❌ Error during Infisical flow: {e}")

if __name__ == "__main__":
    sync_infisical_machine_identity()
