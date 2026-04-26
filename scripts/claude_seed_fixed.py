#!/usr/bin/env python3
"""
Fixed Claude.ai session seeder with better element detection.
"""

import os
import sys
import time

# Add Botasaurus to path
sys.path.insert(0, '/home/yahwehatwork/human-ai/botasaurus')
sys.path.insert(0, '/home/yahwehatwork/.local/lib/python3.11/site-packages')

from botasaurus.browser import browser, Driver

@browser
def seed_claude_session_fixed(driver: Driver, data):
    """
    Open Claude.ai for manual login and session seeding with improved detection.
    """
    print("🌐 Opening Claude.ai...")
    driver.google_get("https://claude.ai/chats", bypass_cloudflare=True)
    
    print("🔐 Please manually log into Claude.ai in the opened browser window.")
    print("   If you see a Cloudflare challenge ('Just a moment...'), please solve it.")
    print("   After logging in, navigate to https://claude.ai/chats to see the chat interface.")
    
    # Wait for user to manually log in and navigate
    print("\n⏳ Waiting for you to log in and reach the chat interface...")
    print("   The script will detect when you're ready (when chat input is visible).")
    print("   You have 3 minutes to complete this process.\n")
    
    # Wait for chat input to appear (indicating successful login)
    start_time = time.time()
    timeout = 180  # 3 minutes
    
    # Multiple possible selectors for Claude.ai chat input
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
        
        # Check each selector
        for selector in selectors:
            try:
                if driver.is_element_visible(selector):
                    print(f"✅ Chat interface detected with selector: '{selector}'")
                    print("💾 Session cookies will be saved automatically by Botasaurus.")
                    print("   You can now close the browser window.\n")
                    
                    # Wait a bit more to let user see success message
                    time.sleep(2)
                    return {"status": "success", "message": f"Session seeded successfully with selector: {selector}"}
            except:
                continue  # Selector not found or error, try next
        
        # Status update every 15 seconds
        if elapsed % 15 == 0 and elapsed > 0:
            print(f"   Still waiting... {remaining} seconds remaining (elapsed: {elapsed}s)")
            # Debug: print what elements we CAN find
            try:
                # Try to find any textarea or input
                textareas = driver.get_elements("textarea")
                inputs = driver.get_elements("input")
                content_editables = driver.get_elements("[contenteditable='true']")
                print(f"   Debug: Found {len(textareas)} textarea, {len(inputs)} input, {len(content_editables)} contenteditable elements")
                if textareas:
                    for i, ta in enumerate(textareas[:3]):  # Show first 3
                        placeholder = driver.get_attribute(f"textarea:nth-child({i+1})", "placeholder") or "no-placeholder"
                        print(f"     Textarea {i+1} placeholder: '{placeholder}'")
            except:
                pass  # Ignore debug errors
        
        time.sleep(2)
    
    print("⏰ Timeout reached. Please try again.")
    return {"status": "timeout", "message": "Seeding timed out after 3 minutes"}

if __name__ == "__main__":
    print("🌱 Claude.ai Session Seeding Tool (FIXED)")
    print("=" * 50)
    print("This will open a browser for you to manually log into Claude.ai.")
    print("After logging in, the session will be saved for automated use.\n")
    
    # Run the seeding function
    result = seed_claude_session_fixed({})
    
    print("\n" + "=" * 50)
    if result.get("status") == "success":
        print("🎉 Seeding completed successfully!")
        print("   You can now set BROWSER_HEADLESS=true and use Claude in automated scripts.")
    else:
        print("❌ Seeding failed or timed out.")
        print("   Please try again, ensuring you:")
        print("   1. Log into https://claude.ai/chats")
        print("   2. Solve any Cloudflare challenge that appears")
        print("   3. Wait for the chat input box to become visible")
        print("   4. Do not close the browser until the script indicates success")
    
    print("\n💡 Tip: Run this script periodically to refresh your session if it expires.")
