import os
import re
from dotenv import load_dotenv
from skills.cloud_vault_skill import CloudVault

# Load local .env to read the secrets
load_dotenv()

# We need a MASTER KEY to encrypt the secrets. 
# In a real scenario, this would be provided via environment variable or prompt.
# For this migration, I will use a temporary master key.
MASTER_KEY = "temporary-migration-master-key-change-this-later"

def migrate():
    print("🚀 Starting Migration: .env -> Supabase Vault...")
    
    # 1. Initialize Vault
    vault = CloudVault(MASTER_KEY)
    
    # 2. Read the .env file manually to ensure we get everything
    env_path = "/home/ubuntu/human-ai/.env"
    if not os.path.exists(env_path):
        print(f"❌ Error: {env_path} not found.")
        return

    secrets_to_migrate = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                secrets_to_migrate[key.strip()] = value.strip().strip('"').strip("'")

    print(f"📦 Found {len(secrets_to_migrate)} secrets to migrate.")

    # 3. Upload to Supabase
    success_count = 0
    for key, value in secrets_to_migrate.items():
        try:
            print(f"🔐 Encrypting and uploading: {key}...")
            vault.set_secret(key, value)
            success_count += 1
        except Exception as e:
            print(f"⚠️ Failed to migrate {key}: {e}")

    print(f"\n✅ Migration Complete!")
    print(f"📊 Successfully migrated: {success_count}/{len(secrets_to_migrate)}")
    print(f"\n⚠️ IMPORTANT: Your secrets are now stored in Supabase.")
    print(f"⚠️ To retrieve them on a new machine, you MUST use the Master Key:")
    print(f"👉 MASTER_KEY: {MASTER_KEY}")
    print(f"\nNote: I have left your local .env file untouched as requested.")

if __name__ == "__main__":
    migrate()
