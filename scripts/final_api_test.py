import os
import requests
from dotenv import load_dotenv

def final_check():
    load_dotenv('/home/ubuntu/human-ai/.env')
    client_id = os.getenv("INFISICAL_CLIENT_ID")
    client_secret = os.getenv("INFISICAL_CLIENT_SECRET")
    
    urls = [
        "https://api.infisical.com/api/v1/auth/machine-identity/authenticate",
        "https://api.infisical.com/api/v2/auth/machine-identity/authenticate",
        "https://app.infisical.com/api/v1/auth/machine-identity/authenticate",
        "https://app.infisical.com/api/v2/auth/machine-identity/authenticate"
    ]
    
    for url in urls:
        print(f"Testing {url}...")
        try:
            resp = requests.post(url, json={"clientId": client_id, "clientSecret": client_secret}, timeout=10)
            print(f"Result: {resp.status_code}")
            if resp.status_code == 200:
                print("✅ FOUND WORKING ENDPOINT!")
                return
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    final_check()
