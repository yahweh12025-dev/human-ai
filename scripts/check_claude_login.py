#!/usr/bin/env python3
"""
Test if the current profile is logged into Claude.ai.
"""

import os
import sys

# Add Botasaurus to path
sys.path.insert(0, '/home/yahwehatwork/human-ai/botasaurus')
sys.path.insert(0, '/home/yahwehatwork/.local/lib/python3.11/site-packages')

from botasaurus.browser import browser, Driver

USER_DATA_DIR = "/home/yahwehatwork/.browser-profile/google"

@browser(
    add_arguments=lambda _: [f"--user-data-dir={USER_DATA_DIR}"],
    headless=True,
)
def check_login_status(driver: Driver, data):
    """
    Check if we are already logged into Claude.ai.
    """
    print("🌐 Checking Claude.ai login status...")
    driver.google_get("https://claude.ai/chats", bypass_cloudflare=True)
    
    # Wait a bit for page to load
    import time
    time.sleep(3)
    
    print(f"Page title: {driver.title}")
    print(f"Current URL: {driver.get_current_url() if hasattr(driver, 'get_current_url') else 'URL method not available'}")
    
    # Check for login indicators
    logged_in = False
    # Selectors that indicate we are logged in
    logged_in_selectors = [
        "textarea[placeholder*='Ask Claude']",
        "textarea[placeholder*='Message']", 
        "[data-testid='chat-input']",
        "[role='textbox']",
        "div[contenteditable='true']",
        ".chat-input",
        "#chat-input",
        "[data-testid='user-menu']",
        ".user-avatar",
        ".avatar",
        "[aria-label*='Account']",
        "[href*='/settings']",
        ".sidebar",
        "[data-testid='sidebar']"
    ]
    
    for selector in logged_in_selectors:
        try:
            if driver.is_element_visible(selector):
                print(f"✅ Found logged-in indicator: {selector}")
                logged_in = True
                break
        except Exception as e:
            # Ignore errors
            pass
    
    # Also check if we are NOT on a login page
    if "login" in driver.get_current_url().lower():
        print("❌ Appears to be on login page")
        logged_in = False
    elif "claude.ai" in driver.get_current_url() and ("/chats" in driver.get_current_url() or "/chat" in driver.get_current_url()):
        print("✅ On chats page")
        logged_in = True  # Strengthen the indicator
    
    if logged_in:
        print("🎉 SUCCESS: Already logged into Claude.ai!")
        print("   The session is saved in your profile.")
    else:
        print("🔒 NOT logged in: Need to seed the session.")
        print("   Please run the seeding script with BROWSER_HEADLESS=false to log in manually.")
    
    return {"logged_in": logged_in}

if __name__ == "__main__":
    print("🔍 Claude.ai Login Status Checker")
    print("=" * 40)
    print(f"Using profile: {USER_DATA_DIR}\n")
    
    result = check_login_status({})
    print("\n" + "=" * 40)
    if result.get("logged_in"):
        print("✅ Your session is ready for automated use.")
    else:
        print("❌ You need to seed your session first.")
        print("   Run: BROWSER_HEADLESS=false python3 /path/to/seed_script.py")