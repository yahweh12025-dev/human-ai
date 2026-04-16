import os
import requests
from dotenv import load_dotenv

def verify_infisical_v2_slug():
    load_dotenv('/home/ubuntu/human-ai/.env')
    
    token = os.getenv("INFISICAL_SERVICE_TOKEN")
    slug = os.getenv("INFISICAL_PROJECT_SLUG")
    
    if not token or not slug:
        print("❌ Missing credentials")
        return

    print(f"Testing Infisical v2 with Slug: {slug}...")
    
    url = "https://app.infisical.com/api/v2/secrets/list"
    headers = {
        "X-Api-Key": token,
        "Content-Type": "application/json"
    }
    payload = {
        "workspaceId": slug, # Trying slug here
        "environment": "dev"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            print("✅ SUCCESS: Infisical v2 API access verified via SLUG!")
            return True
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")

    return False

if __name__ == "__main__":
    verify_infisical_v2_slug()
