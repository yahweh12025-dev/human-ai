#!/usr/bin/env python3
"""
DeepSeek Browser Agent - Core Implementation
Restores the browser-first execution layer for the Human-AI Agent Swarm.
"""

import asyncio
import os
import json
from pathlib import Path
from playwright.async_api import async_playwright

class DeepSeekBrowserAgent:
    """
    Browser-based agent for interacting with DeepSeek chat via Playwright.
    Designed to route LLM requests through the browser to avoid direct API dependencies
    and adhere to the 'Browser-First' mandate.
    """

    def __init__(self):
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # Use WORK_DIR if provided, else default to project root
        work_dir = os.getenv('WORK_DIR', '/home/ubuntu/human-ai')
        self.session_dir = os.path.join(work_dir, 'session', 'browser_profile')
        self.is_initialized = False

    async def start_browser(self):
        """Initialize Playwright browser with a persistent context to maintain sessions."""
        if self.is_initialized:
            return

        print("🌐 Initializing DeepSeek Browser Agent...")
        self.pw = await async_playwright().start()
        
        # Ensure session directory exists for persistent cookies/storage
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Launch persistent context
        # Headless is usually True in production, but can be False for debugging
        headless_mode = os.getenv("BROWSER_HEADLESS", "True").lower() == "true"
        
        self.context = await self.pw.chromium.launch_persistent_context(
            user_data_dir=self.session_dir,
            headless=headless_mode,
            args=[
                '--no-sandbox', 
                '--disable-dev-shm-usage', 
                '--disable-gpu', 
                '--disable-blink-features=AutomationControlled',
                '--window-size=1280,720'
            ],
            user_agent=self.user_agent,
            viewport={'width': 1280, 'height': 720},
            locale='en-US',
            timezone_id='America/New_York',
        )
        
        # Get the first page (or create new)
        pages = self.context.pages
        if pages:
            self.page = pages[0]
        else:
            self.page = await self.context.new_page()
            
        self.is_initialized = True
        print("✅ DeepSeek Browser Agent initialized")

    async def login(self):
        """
        Ensure we are logged into DeepSeek. 
        Relies on persistent session (cookies) in user_data_dir.
        """
        await self.start_browser()
        
        print("🔐 Checking DeepSeek login status...")
        try:
            # Navigate to DeepSeek chat
            await self.page.goto("https://chat.deepseek.com", wait_until="domcontentloaded")
            await self.page.wait_for_timeout(3000)
            
            # Check if we're already logged in by looking for the chat input area
            # DeepSeek's selector may vary; we use a broad list of possible selectors
            input_selector = 'textarea[placeholder*="Message"], textarea, [role="textbox"]'
            try:
                await self.page.wait_for_selector(input_selector, timeout=10000)
                print("✅ Already logged into DeepSeek (session restored)")
                return True
            except:
                print("⚠️ Not logged in. Manual login or cookie import required in session_dir.")
                # In a fully autonomous setup, we would implement a cookie-injection 
                # or a managed login flow here.
                return False
        except Exception as e:
            print(f"❌ Login check failed: {e}")
            return False

    async def prompt(self, prompt_text: str) -> str:
        """
        Send a prompt to DeepSeek and return the response text.
        """
        if not self.is_initialized:
            await self.start_browser()
            
        # Ensure we are on the correct page
        await self.page.goto("https://chat.deepseek.com", wait_until="domcontentloaded")
        await self.page.wait_for_timeout(2000)
        
        try:
            # 1. Locate and fill the input area
            input_selector = 'textarea[placeholder*="Message"], textarea, [role="textbox"]'
            await self.page.wait_for_selector(input_selector, timeout=10000)
            
            # Clear any existing text and enter prompt
            await self.page.fill(input_selector, "")
            await self.page.fill(input_selector, prompt_text)
            
            # 2. Submit the prompt
            await self.page.keyboard.press("Enter")
            print("📤 Prompt submitted to DeepSeek...")
            
            # 3. Wait for the response to generate with improved detection
            # Wait for initial response to start appearing
            await self.page.wait_for_timeout(3000)
            
            # Polling loop to detect when generation is finished
            # We'll monitor the last assistant message for content stability
            max_wait = 90  # Increased timeout for complex responses
            elapsed = 0
            last_content = ""
            stable_count = 0  # Need multiple stable readings
            
            # Try multiple selectors that might work for DeepSeek
            message_selectors = [
                '.message:last-child',
                '[data-message-role="assistant"]:last-child',
                '.chat-message:last-child',
                '.assistant-message:last-child',
                '.text-message:last-child',
                'div[data-testid^="conversation-turn"]:last-child'
            ]
            
            while elapsed < max_wait:
                await asyncio.sleep(2)
                elapsed += 2
                
                try:
                    # Try each selector until we find one that works
                    current_content = ""
                    for selector in message_selectors:
                        try:
                            elements = await self.page.locator(selector).all()
                            if elements:
                                # Get the last element (most recent message)
                                last_element = elements[-1]
                                current_content = await last_element.inner_text()
                                if current_content.strip():  # Non-empty content
                                    break
                        except:
                            continue
                    
                    if current_content and current_content == last_content and len(current_content.strip()) > 10:
                        # Content has stabilized and is substantial
                        stable_count += 1
                        if stable_count >= 3:  # Require 3 consecutive stable readings
                            print("✅ Response generation complete (stable content detected).")
                            return current_content.strip()
                    elif current_content and current_content != last_content:
                        # Content is still changing
                        stable_count = 0  # Reset counter
                        last_content = current_content
                        print(f"🔄 Response still generating... ({len(current_content)} chars)")
                    elif not current_content and elapsed > 10:
                        # No content yet after reasonable wait
                        print("⚠️ No response content detected yet...")
                        
                except Exception as e:
                    # Continue polling even if individual checks fail
                    pass

            print(f"⚠️ Response generation timed out after {max_wait}s. Returning best available result.")
            return last_content.strip() if last_content.strip() else "Error: Response timeout after waiting."
            
        except Exception as e:
            print(f"❌ Error during DeepSeek prompt: {e}")
            raise e

    async def close(self):
        """Clean up browser resources."""
        try:
            if self.context:
                await self.context.close()
        except Exception as e:
            print(f"Error closing context: {e}")
            
        try:
            if self.pw:
                await self.pw.stop()
        except Exception as e:
            print(f"Error stopping playwright: {e}")
            
        self.is_initialized = False
        self.pw = None
        self.context = None
        self.page = None
        print("🌐 DeepSeek Browser Agent closed")

if __name__ == "__main__":
    # Basic test loop
    async def main():
        agent = DeepSeekBrowserAgent()
        try:
            if await agent.login():
                res = await agent.prompt("Hello! Who are you?")
                print(f"Response: {res}")
        finally:
            await agent.close()
    
    asyncio.run(main())
