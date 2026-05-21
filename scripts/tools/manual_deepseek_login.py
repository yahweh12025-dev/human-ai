
import asyncio
import os
from playwright.async_api import async_playwright

# Use the same session directory as the agent
SESSION_DIR = "/home/yahwehatwork/human-ai/session/browser_profile_enhanced"

async def manual_login():
    print("🚀 Manual DeepSeek Login Helper Started.")
    print("--------------------------------------")
    print("👉 A browser window will open. Please log into DeepSeek manually.")
    print("👉 Once you are fully logged in and see the chat interface, come back here.")
    print("👉 I will wait for you to press ENTER in this terminal.\n")

    async with async_playwright() as p:
        # Launch with a visible browser for manual interaction
        context = await p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=False,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--start-maximized']
        )
        
        page = await context.new_page()
        await page.goto("https://chat.deepseek.com")
        
        print("⏳ Waiting for manual login... (Press Enter in this terminal when done)")
        
        # Wait for user input in terminal
        await asyncio.get_event_loop().run_in_executor(None, input, "Press Enter once you are logged in: ")

        print("✅ Login detected! Closing browser and saving session...")
        await context.close()
        print("🚀 Session saved. You can now run the agent tests!")

if __name__ == "__main__":
    try:
        asyncio.run(manual_login())
    except KeyboardInterrupt:
        print("\nStopped by user.")
