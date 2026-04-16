import os
import requests
from dotenv import load_dotenv

def test_infisical_endpoints():
    load_dotenv('/home/ubuntu/human-ai/.env')
    client_id = os.getenv("INFISICAL_CLIENT_ID")
    client_secret = os.getenv("INFISICAL_CLIENT_SECRET")
    project_id = os.getenv("INFISICAL_PROJECT_ID")
    
    auth_url = "https://app.infisical.com/api/v1/auth/universal-auth/login"
    payload = {'clientId': client_id, 'clientSecret': client_secret}
    auth_resp = requests.post(auth_url, data=payload).json()
    token = auth_resp.get('token')
    
    endpoints = [
        "/api/v1/secrets",
        "/v1/secrets",
        "/api/v1/secrets/create",
        "/v1/secrets/create"
    ]
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    test_payload = {"secretName": "TEST_SECRET", "secretValue": "TEST_VALUE", "projectId": project_id, "environment": "dev"}
    
    for ep in endpoints:
        url = f"https://app.infisical.com{ep}"
        print(f"Testing {url}...", end=" ")
        resp = requests.post(url, headers=headers, json=test_payload)
        print(f"Result: {resp.status_code}")

if __name__ == "__main__":
    test_infisical_endpoints()
