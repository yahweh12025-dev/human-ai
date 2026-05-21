#!/usr/bin/env python3
"""
One-time DeepSeek session seeder.
Runs Camoufox in headed mode so you can log in manually.
After logging in, the session is saved to ~/agent_profile/ and all
future headless runs will use it automatically.

Run once:
  DISPLAY=:11 python3 scripts/utility/seed_deepseek_session.py
  # Then log in manually in the browser window that opens
  # Press Enter here when done to save the session
"""
import os, sys, time
from pathlib import Path

os.environ.setdefault("DISPLAY", ":11")

try:
    from camoufox import Camoufox
except ImportError:
    print("ERROR: pip install camoufox")
    sys.exit(1)

PROFILE_DIR = Path.home() / "agent_profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

print(f"Opening DeepSeek in headed mode (profile: {PROFILE_DIR})")
print("1. Log in to DeepSeek in the browser window")
print("2. Once logged in and on the chat page, press Enter here")

with Camoufox(headless=False, persistent_context=True, user_data_dir=str(PROFILE_DIR)) as browser:
    page = browser.new_page()
    page.goto("https://chat.deepseek.com")
    print("\nBrowser opened. Log in, then press Enter in this terminal...")
    input()
    print(f"Session saved to: {PROFILE_DIR}")
    print("Future headless runs will use this session automatically.")
