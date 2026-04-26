#!/usr/bin/env python3
"""
Claude.ai session seeder that waits for manual login by checking for known logged-in indicators.
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
    Waits for user to log in manually.
    """
    print("🌐 Opening Claude.ai...")
    driver.google_get("https://claude.ai/chats", bypass_cloudflare=True)
    
    print("🔐 Please manually log into Claude.ai in the opened browser window.")
    print("   If you see a Cloudflare challenge ('Just a moment...'), please solve it.")
    print("   After logging in, navigate to https://claude.ai/chats to see the chat interface.")
    
    # Wait for user to manually log in and navigate
    print("\n⏳ Waiting for you to log in and reach the chat interface...")
    print("   The script will check for logged-in indicators every 10 seconds.")
    print("   You have 5 minutes to complete this process.\n")
    
    # Wait for chat input to appear or other logged-in indicators (indicating successful login)
    start_time = time.time()
    timeout = 300  # 5 minutes
    
    # Indicators that we are logged in
    logged_in_indicators = [
        # Text that appears in the chat input placeholder
        ("xpath", "//textarea[contains(@placeholder, 'Ask Claude')]"),
        ("xpath", "//textarea[contains(@placeholder, 'Message')]"),
        # Data testid for chat input (if exists)
        ("css", "[data-testid='chat-input']"),
        # Role textbox
        ("css", "[role='textbox']"),
        # Contenteditable div (often used for chat input)
        ("css", "div[contenteditable='true']"),
        # Common class names for chat input
        ("css", ".chat-input"),
        ("css", "#chat-input"),
        # User avatar or menu (indicates logged in)
        ("css", "[data-testid='user-menu']"),
        ("css", ".user-avatar"),
        ("css", ".avatar"),
        ("css", "[aria-label*='Account']"),
        ("css", "[href*='/settings']"),
        ("css", ".sidebar"),
        ("css", "[data-testid='sidebar']"),
    ]
    
    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)
        remaining = timeout - elapsed
        
        # Get current URL and title for debugging
        try:
            current_url = driver.get_current_url() if hasattr(driver, 'get_current_url') else 'N/A'
        except:
            current_url = 'N/A'
        try:
            title = driver.title
        except:
            title = 'N/A'
        
        # Check each indicator
        logged_in = False
        found_indicator = None
        for by, selector in logged_in_indicators:
            try:
                if by == "xpath":
                    # Botasaurus might not have direct xpath support in is_element_visible? We'll try css conversion or use get_element and catch exception.
                    # For simplicity, we'll try to use get_element with xpath via driver.get_element? Not sure if supported.
                    # Let's skip xpath for now and rely on css.
                    continue
                else:  # css
                    if driver.is_element_visible(selector):
                        logged_in = True
                        found_indicator = selector
                        break
            except Exception as e:
                # Ignore errors on individual selectors
                pass
        
        if logged_in:
            print(f"✅ Logged-in indicator found: {found_indicator}")
            print("💾 Session cookies will be saved automatically by Botasaurus.")
            print("   You can now close the browser window.\n")
            
            # Wait a bit more to let user see success message
            time.sleep(2)
            return {"status": "success", "message": f"Session seeded successfully with indicator: {found_indicator}"}
        
        # Also check if we are on a login page (indicating not logged in yet)
        if "login" in current_url.lower():
            # Still on login page, keep waiting
            pass
        elif "claude.ai" in current_url and ("/chats" in current_url or "/chat" in current_url):
            # We are on the chats page, but maybe not logged in yet? 
            # If we are on chats page and not seeing chat input, maybe the session is expired or we need to login again.
            # We'll still wait for the chat input.
            pass
        
        # Status update every 10 seconds
        if elapsed % 10 == 0 and elapsed > 0:
            print(f"   Still waiting... {remaining} seconds remaining (elapsed: {elapsed}s)")
            print(f"      Title: {title}")
            print(f"      URL: {current_url[:80] if len(current_url) > 80 else current_url}")
        
        time.sleep(2)
    
    print("⏰ Timeout reached. Please try again.")
    return {"status": "timeout", "message": "Seeding timed out after 5 minutes"}

if __name__ == "__main__":
    print("🌱 Claude.ai Session Seeding Tool")
    print("=" * 50)
    print(f"Using Chrome profile: {USER_DATA_DIR}")
    print("This will open a browser for you to manually log into Claude.ai.\n")
    
    # Run the seeding function
    result = seed_claude_session({})
    
    print("\n" + "=" * 50)
    if result.get("status") == "success":
        print("🎉 Seeding completed successfully!")
        print("   You can now set BROWSER_HEADLESS=true and use Claude in automated scripts.")
    else:
        print("❌ Seeding failed or timed out.")
        print("   Please try again, ensuring you:")
        print("   1. Log into https://claude.ai/chats")
        print("   2. Solve any Cloudflare challenge that appears")
        print("   3. Wait for the chat input box or other logged-in indicator to become visible")
        print("   4. Do not close the browser until the script indicates success")
    
    print("\n💡 Tip: Run this script periodically to refresh your session if it expires.")