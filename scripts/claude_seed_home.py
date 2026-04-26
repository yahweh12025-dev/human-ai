#!/usr/bin/env python3
"""
Claude.ai session seeder that goes to the home page and waits for manual login.
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
    Open Claude.ai home page for manual login and session seeding.
    """
    print("🌐 Opening Claude.ai home page...")
    driver.google_get("https://claude.ai", bypass_cloudflare=True)
    
    print("🔐 Please manually log into Claude.ai in the opened browser window.")
    print("   Click 'Sign in with Google' and complete the Google login.")
    print("   After logging in, you should see the Claude.ai chat interface.")
    print("   The script will wait for the chat input to appear.\n")
    
    # Wait for user to manually log in and navigate
    print("⏳ Waiting for you to log in and reach the chat interface...")
    print("   The script will check for the chat input every 2 seconds.")
    print("   You have 3 minutes to complete this process.\n")
    
    # Wait for chat input to appear (indicating successful login)
    start_time = time.time()
    timeout = 180  # 3 minutes
    
    # Selectors for chat input that indicate we are logged in
    selectors = [
        "textarea[placeholder*='Ask Claude']",
        "textarea[placeholder*='Message']", 
        "[data-testid='chat-input']",
        "[role='textbox']",
        "div[contenteditable='true']",
        ".chat-input",
        "#chat-input"
    ]
    
    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)
        remaining = timeout - elapsed
        
        # Try to find the chat input using get_element and catch exception
        try:
            found = False
            for selector in selectors:
                try:
                    element = driver.get_element(selector)
                    if element is not None:
                        print(f"✅ Chat interface detected with selector: '{selector}'")
                        found = True
                        break
                except Exception as e:
                    # Element not found, try next selector
                    continue
            
            if found:
                print("💾 Session cookies will be saved automatically by Botasaurus.")
                print("   You can now close the browser window.\n")
                
                # Wait a bit more to let user see success message
                time.sleep(2)
                return {"status": "success", "message": f"Session seeded successfully with selector: {selector}"}
                
        except Exception as e:
            # Ignore errors in checking elements
            pass
        
        # Status update every 10 seconds
        if elapsed % 10 == 0 and elapsed > 0:
            print(f"   Still waiting... {remaining} seconds remaining (elapsed: {elapsed}s)")
        
        time.sleep(2)
    
    print("⏰ Timeout reached. Please try again.")
    return {"status": "timeout", "message": "Seeding timed out after 3 minutes"}

if __name__ == "__main__":
    print("🌱 Claude.ai Session Seeding Tool (Home Page)")
    print("=" * 60)
    print(f"Using Chrome profile: {USER_DATA_DIR}\n")
    
    # Run the seeding function
    result = seed_claude_session({})
    
    print("\n" + "=" * 60)
    if result.get("status") == "success":
        print("🎉 Seeding completed successfully!")
        print("   You can now set BROWSER_HEADLESS=true and use Claude in automated scripts.")
    else:
        print("❌ Seeding failed or timed out.")
        print("   Please try again, ensuring you:")
        print("   1. Log into https://claude.ai via 'Sign in with Google'")
        print("   2. Complete the Google login process")
        print("   3. Wait for the chat input box to become visible")
        print("   4. Do not close the browser until the script indicates success")
    
    print("\n💡 Tip: Run this script periodically to refresh your session if it expires.")