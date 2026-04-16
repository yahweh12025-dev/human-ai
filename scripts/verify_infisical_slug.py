import os
import requests
from dotenv import load_dotenv

def verify_infisical_slug():
    load_dotenv('/home/ubuntu/human-ai/.env')
    
    token = os.getenv("INFISICAL_SERVICE_TOKEN")
    slug = os.getenv("INFISICAL_PROJECT_SLUG")
    
    if not token or not slug:
        print("❌ Missing credentials in .env")
        return

    print(f"Testing Infisical via Slug: {slug}...")
    
    # Trying a more generic secrets endpoint using the slug
    url = f"https://app.infisical.com/api/v1/secrets/project/{slug}"
    headers = {"X-Api-Key": token}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            print("✅ SUCCESS: Access verified via Project Slug!")
            return True
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")

    return False

if __name__ == "__main__":
    verify_infisical_slug()
