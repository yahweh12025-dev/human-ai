import os
import requests
from dotenv import load_dotenv

def verify_infisical_rest():
    load_dotenv('/home/ubuntu/human-ai/.env')
    
    token = os.getenv("INFISICAL_SERVICE_TOKEN")
    project_id = os.getenv("INFISICAL_PROJECT_ID")
    
    if not token or not project_id:
        print("❌ Missing credentials in .env")
        return

    print(f"Testing Infisical v2 API...")
    
    # Correct v2 endpoint for listing secrets
    url = "https://app.infisical.com/api/v2/secrets/list"
    headers = {
        "X-Api-Key": token,
        "Content-Type": "application/json"
    }
    # v2 usually requires a body for filters/environment
    payload = {
        "workspaceId": project_id,
        "environment": "dev"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            print("✅ SUCCESS: Infisical v2 API access verified!")
            data = response.json()
            secrets = data.get('secrets', [])
            print(f"Found {len(secrets)} secrets.")
            return True
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")

    return False

if __name__ == "__main__":
    verify_infisical_rest()
