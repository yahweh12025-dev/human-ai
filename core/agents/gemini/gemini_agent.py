#!/usr/bin/env python3
"""
Gemini Browser Agent: Browser-based agent for interacting with Google Gemini via Playwright.
"""
import asyncio
import os
import time
from pathlib import Path
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

class GeminiBrowserAgent:
    """Browser-based agent for interacting with Google Gemini chat via Playwright."""

    def __init__(self, use_chrome_profile=True):
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        # Use the user's Chrome profile by default to maintain login state
        if use_chrome_profile:
            self.session_dir = os.path.expanduser('~/.config/google-chrome')
        else:
            self.session_dir = os.path.join(os.getenv('WORK_DIR', '/home/yahwehatwork/human-ai'), 'session', 'browser_profile_gemini')
        self.is_initialized = False

    async def start_browser(self):
        """Initialize Playwright browser with persistent context."""
        if self.is_initialized:
            return

        print("🌐 Initializing Gemini Browser Agent...")
        self.pw = await async_playwright().start()

        # Ensure session directory exists
        os.makedirs(self.session_dir, exist_ok=True)

        # Launch persistent context
        self.context = await self.pw.chromium.launch_persistent_context(
            user_data_dir=self.session_dir,
            headless=os.getenv("BROWSER_HEADLESS", "True").lower() == "true",
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-blink-features=AutomationControlled',
                '--window-size=1280,720',
                '--profile-directory=Default',
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
        print("✅ Gemini Browser Agent initialized")

    async def _handle_consent_page(self):
        """Handle Google consent page if present."""
        if "consent.google.com" in self.page.url:
            print("On consent page, attempting to accept...")
            accept_selectors = [
                'button:has-text("I agree")',
                'button:has-text("Accept all")',
                'button:has-text("Accept")',
                '#introAgreeButton',
                'button[aria-label*="Accept"]',
            ]
            accepted = False
            for selector in accept_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    await self.page.click(selector)
                    print(f"Clicked accept button with selector: {selector}")
                    accepted = True
                    break
                except:
                    continue
            
            if not accepted:
                try:
                    await self.page.click('xpath=//button[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "agree") or contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "accept")]')
                    print("Clicked accept button via XPath")
                    accepted = True
                except:
                    pass
            
            if accepted:
                try:
                    await self.page.wait_for_url("**/gemini.google.com/**", timeout=10000)
                    print("Navigated to Gemini after consent")
                except:
                    print("Timeout waiting for navigation to Gemini after consent")
            else:
                print("Could not find accept button on consent page")

    async def login(self):
        """Ensure we are logged into Google Gemini. Uses persistent session."""
        await self.start_browser()

        print("🔐 Checking Gemini login status...")
        # FIX: Changed wait_until="networkidle" to "domcontentloaded" to avoid timeout
        await self.page.goto("https://gemini.google.com", wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)

        await self._handle_consent_page()

        try:
            await self.page.wait_for_selector('textarea[placeholder*="Message"], textarea, [role="textbox"]', timeout=10000)
            print("✅ Already logged into Gemini (session restored)")
            return True
        except:
            print("⚠️ Not logged in after consent handling.")
            return False

    async def prompt(self, prompt_text: str) -> str:
        """Send a prompt to Gemini and return the response."""
        if not self.is_initialized:
            await self.start_browser()

        # FIX: Changed wait_until="networkidle" to "domcontentloaded" to avoid timeout
        await self.page.goto("https://gemini.google.com", wait_until="domcontentloaded")
        await self.page.wait_for_timeout(2000)

        await self._handle_consent_page()

        try:
            input_selector = 'textarea[placeholder*="Message"], textarea, [role="textbox"]'
            await self.page.wait_for_selector(input_selector, timeout=10000)

            await self.page.fill(input_selector, "")
            await self.page.fill(input_selector, prompt_text)
            await self.page.keyboard.press("Enter")

            await self.page.wait_for_timeout(3000)
            await self.page.wait_for_timeout(20000)

            message_selector = '.message, [data-message-role="assistant"], .chat-message, .assistant-message, .model-response'
            try:
                await self.page.wait_for_selector(message_selector, timeout=5000)
                messages = await self.page.locator(message_selector).all()
                if messages:
                    last_message = messages[-1]
                    text = await last_message.inner_text()
                    return text.strip()
            except:
                pass

            page_content = await self.page.evaluate("() => document.body.innerText")
            return page_content.strip()

        except Exception as e:
            print(f"❌ Error during Gemini prompt: {e}")
            raise e

    async def close(self):
        """Close browser resources."""
        if self.context:
            await self.context.close()
        if self.pw:
            await self.pw.stop()
        self.is_initialized = False
        print("🌐 Gemini Browser Agent closed")
