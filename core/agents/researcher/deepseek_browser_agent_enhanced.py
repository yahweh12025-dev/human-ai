#!/usr/bin/env python3
"""
Enhanced DeepSeek Browser Agent - Improved Session Handling
Restores the browser-first execution layer with better session persistence
and CAPTCHA handling capabilities.
"""

import asyncio
import os
import json
from pathlib import Path
from playwright.async_api import async_playwright
import random
import time

class DeepSeekBrowserAgentEnhanced:
    """
    Enhanced browser-based agent for interacting with DeepSeek chat via Playwright.
    Features improved session persistence, human-like behavior, and CAPTCHA handling.
    """

    def __init__(self, keep_browser_open=False, alert_on_captcha=False):
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # Use WORK_DIR if provided, else default to project root
        work_dir = os.getenv('WORK_DIR', '/home/yahwehatwork/human-ai')
        self.session_dir = os.path.join(work_dir, 'session', 'browser_profile_enhanced')
        self.is_initialized = False
        self.keep_browser_open = keep_browser_open
        self.alert_on_captcha = alert_on_captcha
        
        # Human-like behavior settings
        self.min_delay = 100  # ms
        self.max_delay = 300  # ms
        
    async def _human_delay(self):
        """Add a small random delay to mimic human behavior"""
        delay = random.randint(self.min_delay, self.max_delay) / 1000.0
        await asyncio.sleep(delay)
        
    async def _human_type(self, selector, text):
        """Type text with human-like delays between characters"""
        await self.page.wait_for_selector(selector)
        await self.page.click(selector)
        await self.page.fill(selector, "")  # Clear first
        
        for char in text:
            await self.page.type(selector, char)
            await self._human_delay()

    async def start_browser(self):
        """Initialize Playwright browser with a persistent context to maintain sessions."""
        if self.is_initialized:
            return

        print("🌐 Initializing Enhanced DeepSeek Browser Agent...")
        self.pw = await async_playwright().start()
        
        # Ensure session directory exists for persistent cookies/storage
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Launch persistent context with enhanced settings
        headless_mode = os.getenv("BROWSER_HEADLESS", "True").lower() == "true"
        
        self.context = await self.pw.chromium.launch_persistent_context(
            user_data_dir=self.session_dir,
            headless=headless_mode,
            args=[
                '--no-sandbox', 
                '--disable-dev-shm-usage', 
                '--disable-gpu', 
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1280,720',
                '--start-maximized'
            ],
            user_agent=self.user_agent,
            viewport={'width': 1280, 'height': 720},
            locale='en-US',
            timezone_id='America/New_York',
            # Additional settings to help with persistence
            ignore_https_errors=True,
            java_script_enabled=True,
        )
        
        # Get the first page (or create new)
        pages = self.context.pages
        if pages:
            self.page = pages[0]
        else:
            self.page = await self.context.new_page()
            
        # Set up page event listeners for CAPTCHA detection
        if self.alert_on_captcha:
            self.page.on("dialog", lambda dialog: print(f"🚨 Dialog detected: {dialog.message}"))
            
        self.is_initialized = True
        print("✅ Enhanced DeepSeek Browser Agent initialized")

    async def login(self):
        """
        Ensure we are logged into DeepSeek with improved session handling.
        Returns True if login successful or already logged in.
        """
        await self.start_browser()
        
        print("🔐 Checking DeepSeek login status...")
        try:
            # Navigate to DeepSeek chat
            await self.page.goto("https://chat.deepseek.com", wait_until="domcontentloaded")
            await self._human_delay()
            
            # Check if we're already logged in by looking for the chat input area
            input_selector = 'textarea[placeholder*="Message"], textarea, [role="textbox"]'
            try:
                # Wait for the input selector to appear, with a timeout
                await self.page.wait_for_selector(input_selector, timeout=15000)
                print("✅ Already logged into DeepSeek (session restored)")
                return True
            except:
                print("⚠️ Not logged in or CAPTCHA detected.")
                
                # --- Google SSO Attempt ---
                print("🚀 Attempting Google SSO Login...")
                try:
                    # Look for "Continue with Google" button
                    google_btn_selector = 'button:has-text("Google"), a:has-text("Google"), [aria-label*="Google"]'
                    await self.page.wait_for_selector(google_btn_selector, timeout=10000)
                    await self.page.click(google_btn_selector)
                    print("🖱️ Clicked Google SSO button. Waiting for account selection...")
                    
                    # Wait for account picker or automatic login
                    # We check for the input selector again as the ultimate proof of login
                    await self.page.wait_for_selector(input_selector, timeout=30000)
                    print("✅ Login successful via Google SSO!")
                    return True
                except Exception as sso_e:
                    print(f"⚠️ Google SSO attempt failed or required interaction: {sso_e}")

                # Fallback to CAPTCHA check
                page_content = await self.page.content()
                if "Human Verification" in page_content or "captcha" in page_content.lower():
                    print("🚨 CAPTCHA/Human Verification detected!")
                    if self.alert_on_captcha:
                        # Take a screenshot for manual solving
                        screenshot_path = f"/home/yahwehatwork/human-ai/scripts/captcha_alert_{int(time.time())}.png"
                        await self.page.screenshot(path=screenshot_path, full_page=True)
                        print(f"📸 CAPTCHA screenshot saved: {screenshot_path}")
                        print("🔐 Please solve the CAPTCHA manually in the browser.")
                        if self.keep_browser_open:
                            print("💡 Keeping browser open. Solve the CAPTCHA and then continue.")
                            await asyncio.sleep(30)  # Wait 30 seconds for manual solving
                            try:
                                await self.page.wait_for_selector(input_selector, timeout=5000)
                                print("✅ CAPTCHA appears to be solved!")
                                return True
                            except:
                                print("⏳ Still on CAPTCHA page after waiting.")
                                return False
                        else:
                            return False
                    else:
                        return False
                else:
                    print("⚠️ Neither logged in nor obvious CAPTCHA. Unknown state.")
                    return False
        except Exception as e:
            print(f"❌ Login check failed: {e}")
            return False

    async def prompt(self, prompt_text: str) -> str:
        """
        Send a prompt to DeepSeek and return the response text.
        Uses enhanced detection for response completion.
        """
        if not self.is_initialized:
            await self.start_browser()
            
        # Ensure we are on the correct page
        await self.page.goto("https://chat.deepseek.com", wait_until="domcontentloaded")
        await self._human_delay()
        
        try:
            # 1. Locate and fill the input area
            input_selector = 'textarea[placeholder*="Message"], textarea, [role="textbox"]'
            await self.page.wait_for_selector(input_selector, timeout=10000)
            
            # Clear any existing text and enter prompt with human-like typing
            await self.page.fill(input_selector, "")
            await self._human_type(input_selector, prompt_text)
            
            # 2. Submit the prompt
            await self.page.keyboard.press("Enter")
            print("📤 Prompt submitted to DeepSeek...")
            
            # 3. Wait for the response to generate with improved detection
            await self.page.wait_for_timeout(3000)
            
            # Polling loop to detect when generation is finished
            max_wait = 120  # Increased timeout for very long responses
            elapsed = 0
            last_content = ""
            stable_count = 0
            
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
                await asyncio.sleep(3)
                elapsed += 3
                
                try:
                    # 1. Check for "Stop" button (Strong indicator of generation)
                    stop_button = await self.page.get_by_role("button", name="Stop").is_visible()
                    if stop_button:
                        print(f"🔄 Response still generating (Stop button visible)... ({elapsed}s)")
                        last_content = ""
                        stable_count = 0
                        continue
                        
                    # 2. Content Stability Check
                    current_content = ""
                    for selector in message_selectors:
                        try:
                            elements = await self.page.locator(selector).all()
                            if elements:
                                last_element = elements[-1]
                                current_content = await last_element.inner_text()
                                if current_content.strip():
                                    break
                        except:
                            continue
                    
                    if current_content and current_content == last_content and len(current_content.strip()) > 10:
                        stable_count += 1
                        if stable_count >= 3: 
                            print("✅ Response generation complete (No stop button & stable content).")
                            return current_content.strip()
                    elif current_content and current_content != last_content:
                        stable_count = 0
                        last_content = current_content
                        print(f"🔄 Response content changing... ({len(current_content)} chars)")
                    elif not current_content and elapsed > 10:
                        print("⚠️ No response content detected yet...")
                        
                except Exception as e:
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
        
        if not self.keep_browser_open:
            print("🌐 Enhanced DeepSeek Browser Agent closed")
        else:
            print("🌐 Enhanced DeepSeek Browser Agent context closed (browser kept open)")

# Keep the original class name for compatibility
DeepSeekBrowserAgent = DeepSeekBrowserAgentEnhanced