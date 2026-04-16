import os
import requests
from dotenv import load_dotenv

def verify_infisical():
    load_dotenv('/home/ubuntu/human-ai/.env')
    
    token = os.getenv("INFISICAL_SERVICE_TOKEN")
    project_id = os.getenv("INFISICAL_PROJECT_ID")
    
    if not token or not project_id:
        print("❌ Missing INFISICAL_SERVICE_TOKEN or INFISICAL_PROJECT_ID in .env")
        return

    print(f"Testing connection to Infisical...")
    print(f"Project ID: {project_id}")
    
    # Try 1: List secrets for the project (Standard endpoint)
    url = f"https://app.infisical.com/api/v1/secrets/project/{project_id}"
    headers = {"X-Api-Key": token}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            print("✅ SUCCESS: Connection established and secrets retrieved!")
            print(f"Found {len(response.json().get('secrets', []))} secrets.")
            return True
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    # Try 2: Test a different common endpoint (e.g., project details) to see if the token is valid at all
    print("\nAttempting to verify token validity via project info endpoint...")
    try:
        info_url = f"https://app.infisical.com/api/v1/projects/{project_id}"
        info_resp = requests.get(info_url, headers=headers, timeout=15)
        if info_resp.status_code == 200:
            print("✅ Token is VALID, but secrets endpoint returned 404. This suggests a permission issue or a different API version.")
            return True
        else:
            print(f"❌ Token verification failed: {info_resp.status_code}")
    except Exception as e:
        print(f"❌ info request failed: {e}")

    return False

if __name__ == "__main__":
    verify_infisical()
