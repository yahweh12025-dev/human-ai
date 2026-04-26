#!/usr/bin/env python3
"""
Claude.ai session seeder that waits for user to press Enter after manual login.
"""

import os
import sys
import time

# Add Botasaurus to path
sys.path.insert(0, '/home/yahwehatwork/human-ai/botasaurus')
sys.path.insert(0, '/home/yahwehatwork/.local/lib/python3.11/site-packages')

from botasaurus.browser import browser, Driver

# Set the user data dir to your Google Chrome profile
USER_DATA_DIR = os.path.expanduser("~/.browser-profile/google")

@browser(
    add_arguments=lambda _: [f"--user-data-dir={USER_DATA_DIR}"],
    headless=False,  # Set to True for headless mode after seeding
)
def seed_claude_session(driver: Driver, data):
    """
    Open Claude.ai for manual login and session seeding.
    Waits for user to press Enter after they have logged in.
    """
    print("🌐 Opening Claude.ai...")
    driver.google_get("https://claude.ai/chats", bypass_cloudflare=True)
    
    print("🔐 Please manually log into Claude.ai in the opened browser window.")
    print("   If you see a Cloudflare challenge ('Just a moment...'), please solve it.")
    print("   After logging in, you can test by sending a message to Claude.")
    print("   When you have successfully logged in and tested, press ENTER in this terminal to continue.\n")
    
    # Wait for user to press Enter
    input("Press ENTER after you have logged into Claude.ai and tested the chat... ")
    
    print("💾 Saving session...")
    # The session should be saved automatically when the browser closes or when the context is released.
    # We'll give it a moment.
    time.sleep(2)
    
    print("✅ Session should now be saved in your profile.")
    return {"status": "success", "message": "Session seeded via user confirmation"}

if __name__ == "__main__":
    print("🌱 Claude.ai Session Seeding Tool (User Confirmation)")
    print("=" * 60)
    print(f"Using Chrome profile: {USER_DATA_DIR}\n")
    
    # Run the seeding function
    result = seed_claude_session({})
    
    print("\n" + "=" * 60)
    if result.get("status") == "success":
        print("🎉 Seeding completed successfully!")
        print("   You can now set BROWSER_HEADLESS=true and use Claude in automated scripts.")
    else:
        print("❌ Seeding failed.")
    
    print("\n💡 Tip: Run this script periodically to refresh your session if it expires.")