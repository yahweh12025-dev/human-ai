#!/usr/bin/env python3
"""
Patchright Base Agent - Foundation for stealthy browser automation
Uses Patchright (drop-in Playwright replacement) with persistent profiles
and human-like behavior hardening to avoid detection.
"""

import asyncio
import os
import json
import random
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from patchright.async_api import async_playwright, Page, BrowserContext


class PatchrightBaseAgent:
    """
    Base agent for stealthy browser automation using Patchright.
    Designed to be extended for specific platforms (DeepSeek, Gemini, Claude.ai, etc.)
    """

    def __init__(
        self,
        identity: str,
        headless: bool = True,
        viewport: Dict[str, int] = {"width": 1366, "height": 768},
        user_agent: Optional[str] = None,
        locale: str = "en-US",
        timezone_id: str = "America/New_York",
    ):
        """
        Initialize the base agent.

        Args:
            identity: Unique identifier for this browser profile (e.g., 'google', 'deepseek')
            headless: Run browser in headless mode
            viewport: Browser viewport dimensions
            user_agent: Custom user agent string (if None, uses a realistic rotating UA)
            locale: Browser locale
            timezone_id: Browser timezone
        """
        self.identity = identity
        self.headless = headless
        self.viewport = viewport
        self.user_agent = user_agent
        self.locale = locale
        self.timezone_id = timezone_id

        # Playwright objects
        self.pw = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_initialized = False

        # Human-like behavior settings
        self.min_delay = 100  # ms
        self.max_delay = 300  # ms
        self.last_action_time = 0

        # Session watchdog settings
        self.session_check_interval = 300  # 5 minutes
        self.last_session_check = 0

        # Profile directory
        work_dir = os.getenv('WORK_DIR', '/home/ubuntu/human-ai')
        self.profile_dir = os.path.join(work_dir, 'browser_profiles', self.identity)
        os.makedirs(self.profile_dir, exist_ok=True)

        # Anti-detection arguments
        self.stealth_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
            '--disable-ipc-flooding-protection',
        ]

    async def _human_delay(self, min_ms: Optional[int] = None, max_ms: Optional[int] = None):
        """Add a small random delay to mimic human behavior"""
        min_ms = min_ms or self.min_delay
        max_ms = max_ms or self.max_delay
        delay = random.randint(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)
        self.last_action_time = time.time()

    async def _human_type(self, selector: str, text: str):
        """Type text with human-like delays between characters"""
        await self.page.wait_for_selector(selector)
        await self.page.click(selector)
        await self.page.fill(selector, "")  # Clear first

        for char in text:
            await self.page.type(selector, char)
            await self._human_delay(50, 150)  # Faster for typing

    async def _human_click(self, selector: str):
        """Click with human-like movement and delay"""
        await self.page.wait_for_selector(selector)
        # Add slight randomness to click position
        box = await self.page.locator(selector).bounding_box()
        if box:
            x = box['x'] + box['width'] / 2 + random.uniform(-2, 2)
            y = box['y'] + box['height'] / 2 + random.uniform(-2, 2)
            await self.page.mouse.move(x, y)
            await self._human_delay(100, 300)
            await self.page.mouse.click(x, y)
        else:
            await self.page.click(selector)
        await self._human_delay()

    async def start_browser(self):
        """Initialize Patchright browser with persistent context"""
        if self.is_initialized:
            return

        print(f"🌐 Initializing Patchright Base Agent for identity: {self.identity}")
        self.pw = await async_playwright().start()

        # Ensure profile directory exists
        os.makedirs(self.profile_dir, exist_ok=True)

        # Determine user agent (rotate if not provided)
        if not self.user_agent:
            self.user_agent = self._get_realistic_user_agent()

        # Launch persistent context
        self.context = await self.pw.chromium.launch_persistent_context(
            user_data_dir=self.profile_dir,
            headless=self.headless,
            args=self.stealth_args,
            user_agent=self.user_agent,
            viewport=self.viewport,
            locale=self.locale,
            timezone_id=self.timezone_id,
            ignore_https_errors=True,
            java_script_enabled=True,
        )

        # Get or create page
        pages = self.context.pages
        if pages:
            self.page = pages[0]
        else:
            self.page = await self.context.new_page()

        # Set up event listeners for stealth
        await self._setup_stealth_listeners()

        self.is_initialized = True
        print(f"✅ Patchright Base Agent initialized for {self.identity}")

    def _get_realistic_user_agent(self) -> str:
        """Generate a realistic user agent string"""
        # Common Chrome versions on Windows 10
        chrome_versions = [
            "120.0.0.0",
            "119.0.0.0",
            "118.0.0.0",
            "117.0.0.0",
            "116.0.0.0",
        ]
        chrome_ver = random.choice(chrome_versions)
        return (
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{chrome_ver} Safari/537.36"
        )

    async def _setup_stealth_listeners(self):
        """Set up page listeners to enhance stealth"""
        # Override navigator.webdriver
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Override plugins to look like a real browser
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Function"},
                        description: "Portable Document Function",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    },
                    {
                        0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Function"},
                        description: "Portable Document Function",
                        filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                        length: 1,
                        name: "Chrome PDF Viewer"
                    },
                    {
                        0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable"},
                        1: {type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable"},
                        description: "",
                        filename: "internal-nacl-plugin",
                        length: 2,
                        name: "Native Client"
                    }
                ]
            });
        """)

        # Override languages
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)

    async def check_session(self) -> bool:
        """
        Watchdog: Check if we're still authenticated/session is valid.
        Should be overridden by subclasses for platform-specific checks.
        Returns True if session is valid, False if re-authentication needed.
        """
        # Default implementation: check if we're on a login page
        # Subclasses should override with more specific logic
        try:
            await self.page.wait_for_timeout(1000)
            url = self.page.url
            # Generic check: if we see common login indicators
            content = await self.page.content()
            login_indicators = [
                "sign in",
                "log in",
                "login",
                "username",
                "password",
                "authenticate"
            ]
            if any(indicator in content.lower() for indicator in login_indicators):
                print(f"⚠️ Session check: Possible login page detected for {self.identity}")
                return False
            return True
        except Exception as e:
            print(f"❌ Session check error: {e}")
            return False

    async def ensure_session(self) -> bool:
        """
        Ensure session is valid, performing check if needed based on interval.
        Returns True if session is good, False if manual intervention needed.
        """
        now = time.time()
        if now - self.last_session_check > self.session_check_interval:
            self.last_session_check = now
            return await self.check_session()
        return True  # Assume still good if checked recently

    async def navigate_and_wait(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: int = 30000
    ):
        """Navigate to URL with human-like behavior"""
        await self.page.goto(url, wait_until=wait_until, timeout=timeout)
        await self._human_delay(1000, 3000)  # Human-like pause after navigation

    async def safe_fill(self, selector: str, text: str, clear_first: bool = True):
        """Safely fill an input field with human-like typing"""
        if not await self.ensure_session():
            raise Exception("Session invalid - re-authentication required")

        await self.page.wait_for_selector(selector, timeout=15000)
        if clear_first:
            await self.page.fill(selector, "")
        await self._human_type(selector, text)

    async def safe_click(self, selector: str):
        """Safely click an element with human-like behavior"""
        if not await self.ensure_session():
            raise Exception("Session invalid - re-authentication required")

        await self._human_click(selector)

    async def safe_get_by_role(
        self,
        role: str,
        name: Optional[str] = None,
        exact: bool = False
    ):
        """Get element by role (resilient selector) with session check"""
        if not await self.ensure_session():
            raise Exception("Session invalid - re-authentication required")

        if name:
            return self.page.get_by_role(role, name=name, exact=exact)
        else:
            return self.page.get_by_role(role)

    async def safe_get_by_label(self, label: str, exact: bool = False):
        """Get element by label (resilient selector) with session check"""
        if not await self.ensure_session():
            raise Exception("Session invalid - re-authentication required")

        return self.page.get_by_label(label, exact=exact)

    async def safe_get_by_placeholder(self, placeholder: str):
        """Get element by placeholder (resilient selector) with session check"""
        if not await self.ensure_session():
            raise Exception("Session invalid - re-authentication required")

        return self.page.get_by_placeholder(placeholder)

    async def close(self):
        """Clean up browser resources"""
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
        print(f"🌐 Patchright Base Agent closed for {self.identity}")


# Example usage class for DeepSeek (to be implemented in subclass)
class DeepSeekAgent(PatchrightBaseAgent):
    """Example subclass for DeepSeek chat"""
    
    def __init__(self, **kwargs):
        super().__init__(identity="deepseek", **kwargs)
        self.login_url = "https://chat.deepseek.com"

    async def check_session(self) -> bool:
        """DeepSeek-specific session check"""
        try:
            await self.page.goto(self.login_url, wait_until="domcontentloaded")
            await self._human_delay(2000)
            
            # Check if we're logged in by looking for the chat input
            input_selectors = [
                'textarea[placeholder*="Message"]',
                '[role="textbox"]',
                'textarea'
            ]
            
            for selector in input_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    print("✅ DeepSeek session valid")
                    return True
                except:
                    continue
            
            print("⚠️ DeepSeek session invalid - not logged in")
            return False
        except Exception as e:
            print(f"❌ DeepSeek session check failed: {e}")
            return False

    async def prompt(self, prompt_text: str) -> str:
        """Send a prompt to DeepSeek and return response"""
        if not await self.ensure_session():
            raise Exception("DeepSeek session invalid - manual re-seeding required")

        await self.page.goto(self.login_url, wait_until="domcontentloaded")
        await self._human_delay(2000)

        # Find and fill input
        input_selector = 'textarea[placeholder*="Message"], [role="textbox"], textarea'
        await self.safe_fill(input_selector, prompt_text)
        
        # Submit
        await self.safe_click('button:has-text("Send"), [aria-label="Send"]')
        # Or press Enter
        await self.page.keyboard.press("Enter")
        
        # Wait for response (simplified - implement proper detection)
        await self._human_delay(5000)
        
        # Get last response (simplified)
        response_selectors = [
            '.message:last-child',
            '[data-message-role="assistant"]:last-child',
            '.chat-message:last-child'
        ]
        
        for selector in response_selectors:
            try:
                element = await self.page.locator(selector).last()
                if element:
                    return await element.inner_text()
            except:
                continue
        
        return "Error: Could not extract response"


if __name__ == "__main__":
    # Example test
    async def test():
        agent = DeepSeekAgent(headless=False)  # Set to True for production
        try:
            await agent.start_browser()
            if await agent.check_session():
                response = await agent.prompt("Hello! Who are you?")
                print(f"Response: {response}")
            else:
                print("Please log in manually and restart")
        finally:
            await agent.close()
    
    asyncio.run(test())