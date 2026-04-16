import os
import traceback
from dotenv import load_dotenv
from infisical_client import InfisicalClient, ClientSettings

def verify_infisical_sdk():
    load_dotenv('/home/ubuntu/human-ai/.env')
    
    client_id = os.getenv("INFISICAL_PROJECT_ID")
    client_secret = os.getenv("INFISICAL_SERVICE_TOKEN")
    
    if not client_id or not client_secret:
        print("❌ Missing INFISICAL_PROJECT_ID or INFISICAL_SERVICE_TOKEN in .env")
        return

    print(f"Attempting to authenticate with Infisical SDK...")
    
    try:
        settings = ClientSettings(
            client_id=client_id,
            client_secret=client_secret
        )
        client = InfisicalClient(settings=settings)
        
        # Providing options as a dictionary as per common SDK patterns
        # Usually requires at least 'environment_slug'
        options = {"environment_slug": "dev"} 
        secrets = client.listSecrets(options=options)
        
        if secrets:
            print("✅ SUCCESS: Infisical API access verified via SDK!")
            print(f"Found {len(secrets)} secrets.")
            for s in secrets:
                name = s.get('secret_name') if isinstance(s, dict) else getattr(s, 'secret_name', 'Unknown')
                print(f" - {name}")
            return True
        else:
            print("⚠️ Connection successful, but no secrets found.")
            return True
            
    except Exception as e:
        print(f"❌ SDK Verification failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verify_infisical_sdk()
