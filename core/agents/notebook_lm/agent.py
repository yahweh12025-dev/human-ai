
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json
import os

class NotebookLMAgent:
    def __init__(self, use_chrome_profile=True):
        """
        Initialize the NotebookLM agent.
        
        Args:
            use_chrome_profile (bool): If True, attempt to use the existing Chrome profile.
                                       If False or if Chrome profile fails, use a dedicated session.
        """
        self.use_chrome_profile = use_chrome_profile
        self.chrome_profile_path = Path.home() / '.config' / 'google-chrome' / 'Default'
        self.session_path = Path("/home/ubuntu/.hermes/browser_sessions/notebook_lm")
        self.session_path.mkdir(parents=True, exist_ok=True)
        # Selectors - these may need adjustment based on actual DOM
        self.selectors = {
            "main_container": "div[role='main']",
            "new_notebook_button": "button:has-text('New notebook')",
            "upload_button": "button:has-text('Upload')",
            "file_input": "input[type='file']",
            "chat_input": "textarea[placeholder*='Message']",
            "send_button": "button:has-text('Send')",
            "response_message": ".message:last-child, [data-message-role='assistant']:last-child"
        }

    async def launch_browser(self, playwright):
        """
        Launch browser context. Tries to use Chrome profile if enabled and available.
        Falls back to persistent session if Chrome profile fails.
        """
        # Try to use Chrome profile if requested
        if self.use_chrome_profile and self.chrome_profile_path.exists():
            try:
                print(f"Attempting to use Chrome profile: {self.chrome_profile_path}")
                context = await playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.chrome_profile_path),
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--window-size=1280,720",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-extensions-except=velmateajipfelahligkjlbhdpnlfdpngn",  # uBlock Origin example
                    ]
                )
                # Test if we can navigate to NotebookLM without being blocked by login
                test_page = await context.new_page()
                await test_page.goto("https://notebooklm.google.com/", wait_until="domcontentloaded")
                # Check if we see the app or the login page
                content = await test_page.content()
                if "Sign in" in content or "accounts.google.com" in test_page.url:
                    print("Chrome profile requires login. Falling back to dedicated session.")
                    await test_page.close()
                    await context.close()
                    # Fall through to use dedicated session
                else:
                    print("Successfully used Chrome profile (already logged in).")
                    await test_page.close()
                    return context
            except Exception as e:
                print(f"Failed to use Chrome profile: {e}")
                print("Falling back to dedicated session.")
        
        # Fallback: use dedicated session
        print(f"Using dedicated session at: {self.session_path}")
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.session_path),
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        return context

    async def ensure_logged_in(self, page):
        """Check if we are logged into NotebookLM, raise exception if not."""
        # Wait for main app to load
        try:
            await page.wait_for_selector(self.selectors["main_container"], timeout=10000)
        except:
            pass
        
        # Check if we are on the login page
        url = page.url
        content = await page.content()
        if "Sign in" in content or "accounts.google.com" in url:
            raise Exception("Not logged into NotebookLM. Please run the login helper to establish a session.")
        
        # Additional check: look for signs of the app
        try:
            await page.wait_for_selector(self.selectors["new_notebook_button"], timeout=5000)
        except:
            # Maybe we are on the homepage without a notebook yet
            pass
        
        return True

    async def upload_document(self, context, file_path):
        """
        Upload a document to NotebookLM.
        Assumes we are already logged in and on the NotebookLM homepage.
        """
        page = await context.new_page()
        try:
            await page.goto("https://notebooklm.google.com/", wait_until="domcontentloaded")
            await self.ensure_logged_in(page)
            
            # Click 'New notebook' to start fresh (or we could use an existing one)
            try:
                await page.wait_for_selector(self.selectors["new_notebook_button"], timeout=5000)
                await page.click(self.selectors["new_notebook_button"])
                # Wait for the notebook to load
                await page.wait_for_timeout(2000)
            except:
                # If new notebook button not found, maybe we are already in a notebook
                pass
            
            # Look for upload button
            try:
                await page.wait_for_selector(self.selectors["upload_button"], timeout=5000)
                await page.click(self.selectors["upload_button"])
            except:
                # Maybe the upload button is elsewhere, try to find by text
                upload_button = await page.query_selector("button:has-text('Upload'), button:has-text('Add source')")
                if upload_button:
                    await upload_button.click()
                else:
                    raise Exception("Could not find upload button")
            
            # Wait for file input to appear
            try:
                await page.wait_for_selector(self.selectors["file_input"], timeout=5000)
            except:
                # Sometimes the file input is already present but hidden
                pass
            
            # Set the file input
            # Note: the file_input selector might be the same as the upload button if it's an input[type=file] styled as button
            file_input = await page.query_selector(self.selectors["file_input"])
            if not file_input:
                # Try to find any file input
                file_input = await page.query_selector("input[type='file']")
            if not file_input:
                raise Exception("Could not find file input element")
            
            # Set the file path
            await file_input.set_input_files(str(file_path))
            print(f"Set file input to: {file_path}")
            
            # Wait for upload to complete - we can wait for a notification or for the file to appear in the sources list
            # We'll wait a bit and then check for the file name in the page
            await page.wait_for_timeout(3000)  # Initial wait
            
            # Check if the file name appears in the page (indicating upload started)
            file_name = Path(file_path).name
            try:
                await page.wait_for_function(f"document.body.innerText.includes('{file_name}')", timeout=10000)
                print(f"File {file_name} detected in page - upload likely in progress")
            except:
                print(f"Warning: Did not detect file name in page after upload, but continuing")
            
            # Wait a bit more for upload to finish
            await page.wait_for_timeout(5000)
            
        finally:
            await page.close()

    async def query_notebook(self, context, query):
        """
        Send a query to the NotebookLM chat and return the response.
        Assumes we are already logged in and have a notebook with sources.
        """
        page = await context.new_page()
        try:
            await page.goto("https://notebooklm.google.com/", wait_until="domcontentloaded")
            await self.ensure_logged_in(page)
            
            # Wait for chat input to be ready
            try:
                await page.wait_for_selector(self.selectors["chat_input"], timeout=10000)
            except:
                # Try to find any textarea or contenteditable
                chat_input = await page.query_selector("textarea, [contenteditable='true']")
                if not chat_input:
                    raise Exception("Could not find chat input")
            
            # Clear and fill the input
            await page.fill(self.selectors["chat_input"], "")
            await page.fill(self.selectors["chat_input"], query)
            
            # Submit by pressing Enter or clicking send button
            try:
                # Try to find send button
                send_button = await page.query_selector(self.selectors["send_button"])
                if send_button:
                    await send_button.click()
                else:
                    # Press Enter
                    await page.keyboard.press("Enter")
            except:
                await page.keyboard.press("Enter")
            
            # Wait for response to start
            await page.wait_for_timeout(2000)
            
            # Wait for response to complete - we'll wait for a new message to appear and stop changing
            # Simple approach: wait for a response element and then wait a bit more
            try:
                await page.wait_for_selector(self.selectors["response_message"], timeout=30000)
            except:
                # If we don't see a response, wait a bit and then try to get the page content
                await page.wait_for_timeout(10000)
            
            # Additional wait for response to finish streaming
            await page.wait_for_timeout(5000)
            
            # Extract the response - get the last message from the assistant
            response_elements = await page.query_selector_all(self.selectors["response_message"])
            if response_elements:
                last_response = response_elements[-1]
                response_text = await last_response.inner_text()
                return response_text.strip()
            else:
                # Fallback: get all messages and take the last one that looks like a response
                # Or get the entire page content and try to extract
                page_content = await page.content()
                # We'll return a placeholder for now
                return f"[Could not extract response from NotebookLM. Page length: {len(page_content)}]"
                
        finally:
            await page.close()

async def main():
    agent = NotebookLMAgent(use_chrome_profile=True)
    async with async_playwright() as p:
        context = await agent.launch_browser(p)
        print("Browser launched.")
        # Example usage would go here
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
