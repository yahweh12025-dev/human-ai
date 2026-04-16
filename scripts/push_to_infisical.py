import os
import requests
from dotenv import load_dotenv

def push_secrets_to_infisical():
    load_dotenv('/home/ubuntu/human-ai/.env')
    
    client_id = os.getenv("INFISICAL_CLIENT_ID")
    client_secret = os.getenv("INFISICAL_CLIENT_SECRET")
    project_id = os.getenv("INFISICAL_PROJECT_ID")
    
    if not all([client_id, client_secret, project_id]):
        print("❌ Missing Infisical credentials in .env")
        return

    print(f"🔐 Authenticating for upload...")
    auth_url = "https://app.infisical.com/api/v1/auth/universal-auth/login"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {'clientId': client_id, 'clientSecret': client_secret}
    
    try:
        auth_resp = requests.post(auth_url, headers=headers, data=payload, timeout=15)
        auth_resp.raise_for_status()
        token = auth_resp.json().get('token')
        print("✅ Authenticated.")
        
        # Read .env for secrets to push
        secrets_to_push = {}
        with open('/home/ubuntu/human-ai/.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    # Don't push the Infisical credentials themselves to Infisical to avoid recursion
                    if k not in ["INFISICAL_CLIENT_ID", "INFISICAL_CLIENT_SECRET", "INFISICAL_PROJECT_ID", "INFISICAL_PROJECT_SLUG"]:
                        secrets_to_push[k] = v

        print(f"📦 Found {len(secrets_to_push)} secrets in .env to push.")
        
        # Push each secret
        # endpoint: POST /api/v1/secrets
        secret_url = "https://app.infisical.com/api/v1/secrets"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        for key, value in secrets_to_push.items():
            payload = {
                "secretName": key,
                "secretValue": value,
                "projectId": project_id,
                "environment": "dev"
            }
            try:
                resp = requests.post(secret_url, headers=headers, json=payload, timeout=10)
                if resp.status_code in [200, 201]:
                    print(f"✅ Pushed: {key}")
                else:
                    print(f"⚠️ Failed to push {key}: {resp.status_code} - {resp.text}")
            except Exception as e:
                print(f"❌ Error pushing {key}: {e}")

        print("🎉 All possible secrets have been pushed to Infisical.")
            
    except Exception as e:
        print(f"❌ General Error: {e}")

if __name__ == "__main__":
    push_secrets_to_infisical()
