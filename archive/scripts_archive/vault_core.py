import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# SHARED CONSTANTS
VAULT_SALT = b'human_ai_fixed_salt_2026'
S_ITERATIONS = 100000

def derive_fernet(password: str) -> Fernet:
    """Derives a Fernet key from a password using a fixed salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=VAULT_SALT,
        iterations=S_ITERATIONS,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return Fernet(key)

def encrypt_value(password: str, value: str) -> str:
    fernet = derive_fernet(password)
    return fernet.encrypt(value.encode()).decode()

def decrypt_value(password: str, encrypted_value: str) -> str:
    fernet = derive_fernet(password)
    return fernet.decrypt(encrypted_value.encode()).decode()
