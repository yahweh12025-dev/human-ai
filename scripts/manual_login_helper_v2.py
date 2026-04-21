import asyncio
from playwright.async_api import async_playwright
import os
import json

async def manual_login_helper():
    """Helper function to manually log in to DeepSeek and save session"""
    pw = await async_playwright().start()
    session_dir = '/home/ubuntu/human-ai/session/browser_profile'
    
    print("🚀 Launching browser for manual login...")
    print("📝 Please:")
    print("   1. Solve the Human Verification challenge if it appears")
    print("   2. Log in to your DeepSeek account")
    print("   3. Navigate to https://chat.deepseek.com")
    print("   4. Verify you can see the chat interface (textarea for input)")
    print("   5. Then type 'done' in this terminal and press Enter")
    
    context = await pw.chromium.launch_persistent_context(
        user_data_dir=session_dir,
        headless=False,  # Visible for manual interaction
        args=['--no-sandbox', '--disable-dev-shm-usage']
    )
    
    pages = context.pages
    if pages:
        page = pages[0]
    else:
        page = await context.new_page()
    
    # Go to DeepSeek
    await page.goto("https://chat.deepseek.com")
    print("\\n🌐 Navigated to DeepSeek. Please complete login manually...")
    
    # Wait for user to signal completion
    try:
        while True:
            user_input = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, input), 
                timeout=1.0
            )
            if user_input.strip().lower() == 'done':
                print("✅ User signaled completion. Saving session...")
                break
    except asyncio.TimeoutError:
        # Keep waiting
        pass
    except EOFError:
        # Handle case where stdin is closed
        pass
    
    # Give a moment for final actions
    await page.wait_for_timeout(3000)
    
    # Verify we're logged in by checking for chat input
    try:
        await page.wait_for_selector('textarea[placeholder*="Message"], textarea, [role="textbox"]', timeout=5000)
        print("✅ Successfully detected chat input - login appears successful!")
    except:
        print("⚠️  Could not verify chat input, but session saved anyway.")
    
    await context.close()
    await pw.stop()
    print("💾 Session saved. You can now run automated tests.")

if __name__ == "__main__":
    asyncio.run(manual_login_helper())