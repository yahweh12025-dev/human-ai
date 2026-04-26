#!/usr/bin/env python3
"""
Claude.ai session seeder with improved detection and explicit user data dir.
"""

import os
import sys
import time

# Add Botasaurus to path
sys.path.insert(0, '/home/yahwehatwork/human-ai/botasaurus')
sys.path.insert(0, '/home/yahwehatwork/.local/lib/python3.11/site-packages')

from botasaurus.browser import browser, Driver

# Configuration
USER_DATA_DIR = "/home/yahwehatwork/.browser-profile/google"

@browser(
    add_arguments=lambda _: [f"--user-data-dir={USER_DATA_DIR}"],
    headless=False,  # Will be overridden by BROWSER_HEADLESS env var if needed
    # We'll control headless via environment variable in the function if needed, but decorator is set at definition time.
    # Instead, we'll read the environment inside the function and adjust behavior? Actually, headless is set at decoration time.
    # So we'll make two versions or read from env and recreate the decorator? Too complex.
    # Let's just set headless=False and rely on the user to set BROWSER_HEADLESS=false in the env when running.
    # Actually, the browser decorator reads the headless argument at decoration time, not at call time.
    # So we need to set it based on environment. We'll do a trick: define the function inside a conditional? 
    # Instead, let's just not set headless in the decorator and rely on the botasaurus default (which is False) and let the user control it via BROWSER_HEADLESS environment variable?
    # Looking at the botasaurus source, the headless parameter in the decorator defaults to False, but it seems like it might also read from environment? Not sure.
    # Let's just set headless=False and if the user wants headless, they can set BROWSER_HEADLESS=true and hope the decorator picks it up? 
    # Actually, the browser decorator does not read environment variables for headless. It uses the value passed to the decorator.
    # So we need to pass headless as a variable. We'll create the decorator dynamically? 
    # For simplicity, let's assume the user will run with BROWSER_HEADLESS=false for seeding and true for automated use, and we'll have two scripts or two runs.
    # We'll document that.
    # For now, we'll set headless=False and instruct the user to set BROWSER_HEADLESS=false in the environment when running.
    # Actually, the user already tried that and it didn't work because of the module issue.
    # We'll ignore the headless parameter in the decorator and set it via add_arguments? Let's see if we can add --headless or not.
    # We can add "--headless" to the add_arguments if we want headless, but we want to control it via environment.
    # Let's not overcomplicate: we'll have the user set the headless mode by editing the script or via an environment variable that we read and then conditionally add the argument.
    # We'll read BROWSER_HEADLESS environment variable and if it's "true", we add "--headless" to the arguments.
)

def make_browser_decorator():
    headless_env = os.environ.get('BROWSER_HEADLESS', 'false').lower()
    headless_arg = [] if headless_env != 'true' else ["--headless"]
    return browser(
        add_arguments=lambda _: [f"--user-data-dir={USER_DATA_DIR}"] + headless_arg,
    )

# Actually, let's just hardcode for now and tell the user to adjust the script for headless vs headed.
# We'll make two separate scripts or tell them to change the headless parameter in the decorator.
# For seeding, we want headed (visible browser), so we'll set headless=False.
# For automated use, they can set headless=True in the decorator or use a different script.
# We'll create a script that is for seeding (headed) and another for automated (headless) if needed.

# Let's create the decorator for headed mode (seeding)
@browser(
    add_arguments=lambda _: [f"--user-data-dir={USER_DATA_DIR}"],
    headless=False,
)
def seed_claude_session(driver: Driver, data):
    """
    Open Claude.ai for manual login and session seeding.
    """
    print("🌐 Opening Claude.ai...")
    driver.google_get("https://claude.ai/chats", bypass_cloudflare=True)
    
    print("🔐 Please manually log into Claude.ai in the opened browser window.")
    print("   If you see a Cloudflare challenge ('Just a moment...'), please solve it.")
    print("   After logging in, navigate to https://claude.ai/chats to see the chat interface.")
    
    # Wait for user to manually log in and navigate
    print("\n⏳ Waiting for you to log in and reach the chat interface...")
    print("   The script will detect when you're ready (when chat input is visible or URL is chats page).")
    print("   You have 3 minutes to complete this process.\n")
    
    # Wait for chat input to appear or URL to be chats page (indicating successful login)
    start_time = time.time()
    timeout = 180  # 3 minutes
    
    # Selectors for chat input
    input_selectors = [
        "textarea[placeholder*='Ask Claude']",
        "textarea[placeholder*='Message']", 
        "[data-testid='chat-input']",
        "[role='textbox']",
        "div[contenteditable='true']",
        ".chat-input",
        "#chat-input"
    ]
    
    # Selectors for logged-in indicators (other than chat input)
    logged_in_indicators = [
        "[data-testid='user-menu']",
        ".user-avatar",
        ".avatar",
        "[aria-label*='Account']",
        "[href*='/settings']",
        ".sidebar",
        "[data-testid='sidebar']"
    ]
    
    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)
        remaining = timeout - elapsed
        
        # Check if we are on the chats page (URL contains /chats or /chat)
        current_url = getattr(driver, 'current_url', '')
        if not current_url:
            # Try to get URL via JavaScript
            try:
                current_url = driver.get_current_url() if hasattr(driver, 'get_current_url') else driver.execute_script("return window.location.href;")
            except:
                current_url = ''
        
        is_on_chats_page = ('claude.ai' in current_url and ('/chats' in current_url or '/chat' in current_url))
        
        # Check for chat input
        chat_input_found = False
        for selector in input_selectors:
            try:
                if driver.is_element_visible(selector):
                    chat_input_found = True
                    print(f"✅ Chat input detected with selector: '{selector}'")
                    break
            except:
                continue
        
        # Check for other logged-in indicators
        logged_in_found = False
        for selector in logged_in_indicators:
            try:
                if driver.is_element_visible(selector):
                    logged_in_found = True
                    print(f"✅ Logged-in indicator detected with selector: '{selector}'")
                    break
            except:
                continue
        
        # If we are on the chats page AND we have either chat input or another logged-in indicator, consider it success
        if is_on_chats_page and (chat_input_found or logged_in_found):
            print("💾 Session cookies will be saved automatically by Botasaurus.")
            print("   You can now close the browser window.\n")
            
            # Wait a bit more to let user see success message
            time.sleep(2)
            return {"status": "success", "message": f"Session seeded successfully (URL: {current_url})"}
        
        # Status update every 10 seconds
        if elapsed % 10 == 0 and elapsed > 0:
            print(f"   Still waiting... {remaining} seconds remaining (elapsed: {elapsed}s)")
            print(f"      Current URL: {current_url[:80] if current_url else 'N/A'}")
            # Debug: count of elements found for a few selectors
            try:
                textareas = driver.get_elements('textarea')
                print(f"      Found {len(textareas)} textarea elements on page")
            except:
                pass
        
        time.sleep(2)
    
    print("⏰ Timeout reached. Please try again.")
    return {"status": "timeout", "message": "Seeding timed out after 3 minutes"}

if __name__ == "__main__":
    print("🌱 Claude.ai Session Seeding Tool (Headed Mode for Seeding)")
    print("=" * 60)
    print("This will open a VISIBLE browser for you to manually log into Claude.ai.")
    print("After logging in, the session will be saved to your persistent profile.")
    print("Profile directory:", USER_DATA_DIR)
    print("Make sure BROWSER_HEADLESS=false is set in your environment (it is by default if not set).\n")
    
    # Run the seeding function
    result = seed_claude_session({})
    
    print("\n" + "=" * 60)
    if result.get("status") == "success":
        print("🎉 Seeding completed successfully!")
        print("   You can now run automated scripts with BROWSER_HEADLESS=true using the same profile.")
    else:
        print("❌ Seeding failed or timed out.")
        print("   Please try again, ensuring you:")
        print("   1. Log into https://claude.ai/chats")
        print("   2. Solve any Cloudflare challenge that appears")
        print("   3. Wait for the chat input box or other logged-in indicator to become visible")
        print("   4. Do not close the browser until the script indicates success")
    
    print("\n💡 Tip: Run this script periodically to refresh your session if it expires.")