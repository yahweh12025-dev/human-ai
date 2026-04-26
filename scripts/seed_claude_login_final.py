#!/usr/bin/env python3
"""
Seed a Claude.ai session for use with Botasaurus.
This script opens a browser for manual login and session saving.
Run this once with your Google profile, then set headless=true for automated use.
"""

import os
import sys
import time

# Add Botasaurus to path
sys.path.insert(0, '/home/yahwehatwork/.local/lib/python3.11/site-packages')
sys.path.insert(0, '/home/yahwehatwork/human-ai/botasaurus')

from botasaurus.browser import browser, Driver

# Path to your Google Chrome profile
GOOGLE_PROFILE_PATH = os.path.join(os.getenv('HOME', '/home/yahwehatwork'), '.browser-profile', 'google')

@browser(
    profile=GOOGLE_PROFILE_PATH,
    headless=False,
    close_on_crash=True,
    wait_for_complete_page_load=True,
)
def seed_claude_session(driver: Driver, data):
    """
    Open Claude.ai for manual login and session seeding.
    """
    print("🌐 Opening Claude.ai...")
    driver.google_get("https://claude.ai/chat", bypass_cloudflare=True)
    
    print("🔐 Please manually log into Claude.ai in the opened browser window.")
    print("   If you see a Cloudflare challenge ('Just a moment...'), please solve it.")
    print("   After logging in, navigate to https://claude.ai/chats to see the chat interface.")
    print("")
    
    # Wait for user to manually log in and navigate
    print("⏳ Waiting for you to log in and reach the chat interface...")
    print("   The script will detect when you're ready (when chat input is visible).")
    print("   You have 5 minutes to complete this process.\n")
    
    start_time = time.time()
    timeout = 300  # 5 minutes
    
    while time.time() - start_time < timeout:
        try:
            # Check if chat input is available
            if driver.is_element_visible('[data-testid="chat-input"], [role="textbox"], textarea[placeholder*="Message"]'):
                print("✅ Chat interface detected! Session is ready.")
                print("💾 Session cookies will be saved automatically by Botasaurus.")
                print("   You can now close the browser window.")
                
                # Wait a bit more to let user see success message
                time.sleep(3)
                return {"status": "success", "message": "Session seeded successfully"}
        except:
            pass  # Element not found yet, continue waiting
        
        time.sleep(2)
        elapsed = int(time.time() - start_time)
        remaining = timeout - elapsed
        if remaining % 30 == 0 and remaining > 0:  # Update every 30 seconds
            print(f"   Still waiting... {remaining} seconds remaining")
    
    print("⏰ Timeout reached. Please try again.")
    return {"status": "timeout", "message": "Seeding timed out after 5 minutes"}

if __name__ == "__main__":
    print("🌱 Claude.ai Session Seeding Tool")
    print("=" * 50)
    print("This will open a browser for you to manually log into Claude.ai.")
    print("After logging in, the session will be saved for automated use.\n")
    
    # Run the seeding function
    result = seed_claude_session({})
    
    print("\n" + "=" * 50)
    if result.get("status") == "success":
        print("🎉 Seeding completed successfully!")
        print("   You can now set headless=true and use Claude in automated scripts.")
    else:
        print("❌ Seeding failed or timed out.")
        print("   Please try again, ensuring you:")
        print("   1. Log into https://claude.ai/chats")
        print("   2. Solve any Cloudflare challenge that appears")
        print("   3. Wait for the chat input box to become visible")
        print("   4. Do not close the browser until the script indicates success")
    
    print("\n💡 Tip: Run this script periodically to refresh your session if it expires.")