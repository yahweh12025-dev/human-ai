#!/usr/bin/env python3
import os
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

class CloudVault:
    def __init__(self, master_key: str):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.supabase = create_client(self.url, self.key)
        self.fernet = self._derive_fernet(master_key)

    def _derive_fernet(self, password: str) -> Fernet:
        salt = b'human_ai_salt_fixed' # In production, this should be unique and stored in the vault itself
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)

    def set_secret(self, key: str, value: str):
        encrypted = self.fernet.encrypt(value.encode()).decode()
        data = {"key": key, "encrypted_value": encrypted}
        res = self.supabase.table("vault_secrets").upsert(data).execute()
        return res

    def get_secret(self, key: str):
        res = self.supabase.table("vault_secrets").select("encrypted_value").eq("key", key).execute()
        if not res.data:
            return None
        encrypted_val = res.data[0]["encrypted_value"]
        decrypted = self.fernet.decrypt(encrypted_val.encode()).decode()
        return decrypted

if __name__ == "__main__":
    # Test usage
    vault = CloudVault("my-super-secret-master-key")
    vault.set_secret("test_key", "hello_world")
    print(f"Retrieved: {vault.get_secret('test_key')}")
