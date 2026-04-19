import json
from pathlib import Path

COOKIE_FILE = Path('/home/ubuntu/human-ai/session/cookies.json')

def save_cookies(cookies):
    COOKIE_FILE.write_text(json.dumps(cookies))

def load_cookies():
    if COOKIE_FILE.exists():
        return json.loads(COOKIE_FILE.read_text())
    return []
