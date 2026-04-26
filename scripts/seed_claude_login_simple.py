#!/usr/bin/env python3
"""
Seeding script for Claude.ai login using Google account (Patchright version).
This script launches a visible browser with your Google profile.
After logging in, close the browser to save the session.
Note: Please close all Chrome instances before running this script to avoid conflicts.
"""

import asyncio
import os
import sys

async def main():
    # Path to your Google Chrome profile
    user_data_dir = os.path.join(os.getenv('HOME', '/home/yahwehatwork'), '.browser-profile', 'google')
    
    print("🌐 Starting Claude Browser Agent for manual seeding...")
    print("📝 Please log into Claude.ai using your Google account.")
    print("🛑 After successful login, CLOSE THE BROWSER WINDOW to finish.")
    print("")
    
    from patchright.async_api import async_playwright
    
    pw = await async_playwright().start()
    browser = None
    try:
        browser = await pw.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-blink-features=AutomationControlled',
            ],
        )
        print("✅ Browser started. Waiting for you to log in...")
        
        # Create a new page and navigate to Claude.ai login page
        page = await browser.new_page()
        await page.goto("https://claude.ai/login", wait_until="domcontentloaded")
        
        # Wait for the user to log in and then close the browser
        # We'll wait until the browser has no pages left (user closed all tabs/windows)
        while len(browser.pages) > 0:
            await asyncio.sleep(1)
        
        print("✅ Browser closed. Session saved in your Google profile.")
        print("🔐 You can now run the researcher agent in headless mode.")
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        if "Target page, context or browser has been closed" in str(e):
            print("💡 Hint: Please close all Chrome instances and try again.")
        import traceback
        traceback.print_exc()
    finally:
        if browser:
            await browser.close()
        await pw.stop()
        print("🌐 Browser agent cleaned up.")

if __name__ == "__main__":
    asyncio.run(main())