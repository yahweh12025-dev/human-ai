
#!/usr/bin/env python3
"""
Manual login helper for NotebookLM agent.
Run this once to log in via Google. The session will be saved to the 
persistent browser profile used by the agent.
Note: If you want to use your existing Chrome profile, just ensure you are logged in
and the agent will use it by default.
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

SESSION_PATH = Path("/home/ubuntu/.hermes/browser_sessions/notebook_lm")

async def main():
    SESSION_PATH.mkdir(parents=True, exist_ok=True)
    print(f"Launching browser for manual login. User data will be saved to: {SESSION_PATH}")
    print("This is useful if you want to create a dedicated session for the agent.")
    print("If you prefer to use your existing Chrome profile, just log in to NotebookLM via Chrome")
    print("and the agent will use it automatically (set use_chrome_profile=True in the agent).")
    print("")
    print("Please log in to Google and then to NotebookLM.")
    print("After you see your Notebooks list (or can create a new notebook),")
    print("you can close this browser window to end the session.")
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_PATH),
            headless=False,  # Visible browser for manual login
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = await context.new_page()
        await page.goto("https://notebooklm.google.com/")
        
        # Wait for the user to navigate and log in. We'll wait until we see an element
        # that indicates we are in the app (e.g., the sidebar or the new notebook button)
        try:
            # Wait for the main app container to appear (selector may change)
            await page.wait_for_selector("div[role='main']", timeout=300000)  # 5 minutes
            print("Successfully detected NotebookLM app. You can now close the browser.")
        except Exception as e:
            print(f"Timeout or error waiting for app: {e}")
            print("Please make sure you are logged in and on the NotebookLM homepage.")
        
        # Keep the browser open until the user closes it
        await context.wait_for_event("close")
        print("Browser session closed. Saved cookies and local storage for future use.")

if __name__ == "__main__":
    asyncio.run(main())
