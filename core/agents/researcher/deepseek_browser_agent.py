#!/usr/bin/env python3
"""
DeepSeek Browser Agent - Patchright Version
Updated to use Patchright for stealth automation with persistent profiles
and human-like behavior hardening as recommended.
"""

import asyncio
import os
import json
import random
import time
from pathlib import Path
from patchright.async_api import async_playwright


class DeepSeekBrowserAgent:
    """
    Browser-based agent for interacting with DeepSeek chat via Patchright.
    Uses persistent profiles, human-like behavior, and session watchdog
    to avoid detection as per recommendations.
    """

    def __init__(self):
        self.pw = None
        self.context = None
        self.page = None
        # Use a realistic, rotating user agent
        self.user_agent = self._get_realistic_user_agent()
        
        # Use WORK_DIR if provided, else default to project root
        work_dir = os.getenv('WORK_DIR', '/home/ubuntu/human-ai')
        # Separate profile for DeepSeek identity (as recommended)
        self.session_dir = os.path.join(work_dir, 'browser_profiles', 'deepseek')
        self.is_initialized = False
        
        # Human-like behavior settings (adjusted per recommendations)
        self.min_delay = 150  # ms - reduced from 100-300 to avoid being too robotic
        self.max_delay = 400  # ms
        self.last_action_time = 0
        
        # Session watchdog settings
        self.session_check_interval = 300  # 5 minutes
        self.last_session_check = 0
        
        # Anti-detection arguments (as recommended)
        self.stealth_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
            '--disable-ipc-flooding-protection',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--disable-client-side-phishing-detection',
            '--disable-sync',
            '--metrics-recording-only',
            '--no-first-run',
            '--no-default-browser-check',
            f'--window-size={random.randint(1200, 1400)},{random.randint(700, 900)}',  # Varied viewport
        ]

    def _get_realistic_user_agent(self) -> str:
        """Generate a realistic user agent string"""
        # Common Chrome versions on Windows 10 (more realistic distribution)
        chrome_versions = [
            "120.0.6099.130",
            "119.0.6045.199",
            "118.0.5993.90",
            "117.0.5938.132",
            "116.0.5845.188",
            "121.0.6167.86",
            "122.0.6261.69",
        ]
        chrome_ver = random.choice(chrome_versions)
        return (
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{chrome_ver} Safari/537.36"
        )

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

        # Type with variable speed like a human
        for i, char in enumerate(text):
            await self.page.type(selector, char)
            # Variable delay: faster for common words, slower for punctuation/caps
            if char.isalpha() and i > 0 and text[i-1].isalpha():
                delay_range = (50, 150)  # Fast for letters in words
            else:
                delay_range = (100, 300)  # Slow for punctuation, caps, start
            await self._human_delay(*delay_range)

    async def _human_click(self, selector: str):
        """Click with human-like movement and delay"""
        await self.page.wait_for_selector(selector)
        # Add slight randomness to click position
        box = await self.page.locator(selector).bounding_box()
        if box:
            x = box['x'] + box['width'] / 2 + random.uniform(-3, 3)
            y = box['y'] + box['height'] / 2 + random.uniform(-3, 3)
            await self.page.mouse.move(x, y, steps=random.randint(5, 15))
            await self._human_delay(100, 300)
            await self.page.mouse.click(x, y)
        else:
            await self.page.click(selector)
        await self._human_delay()

    async def start_browser(self):
        """Initialize Patchright browser with persistent context"""
        if self.is_initialized:
            return

        print("🌐 Initializing DeepSeek Browser Agent (Patchright)...")
        self.pw = await async_playwright().start()
        
        # Ensure session directory exists for persistent cookies/storage
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Launch persistent context with enhanced stealth settings
        headless_mode = os.getenv("BROWSER_HEADLESS", "True").lower() == "true"
        
        self.context = await self.pw.chromium.launch_persistent_context(
            user_data_dir=self.session_dir,
            headless=headless_mode,
            args=self.stealth_args,
            user_agent=self.user_agent,
            viewport={'width': 1280, 'height': 720},  # Will be overridden by stealth args
            locale='en-US',
            timezone_id='America/New_York',
            # Additional settings to help with persistence and stealth
            ignore_https_errors=True,
            java_script_enabled=True,
        )
        
        # Get the first page (or create new)
        pages = self.context.pages
        if pages:
            self.page = pages[0]
        else:
            self.page = await self.context.new_page()
        
        # Set up page event listeners for enhanced stealth
        await self._setup_stealth_listeners()
        
        self.is_initialized = True
        print("✅ DeepSeek Browser Agent initialized (Patchright)")

    async def _setup_stealth_listeners(self):
        """Set up page listeners to enhance stealth beyond basic args"""
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
        
        # Override permissions
        await self.page.add_init_script("""
            const originalQuery = window.navigator.permissions.query;
            return window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

    async def check_session(self) -> bool:
        """
        Session watchdog: Check if we're still authenticated.
        Returns True if session is valid, False if re-authentication needed.
        """
        try:
            # Update last check time
            self.last_session_check = time.time()
            
            # Navigate to DeepSeek chat
            await self.page.goto("https://chat.deepseek.com", wait_until="domcontentloaded")
            await self._human_delay(2000, 4000)  # Human-like pause after navigation
            
            # Check if we're already logged in by looking for the chat input area
            # Using multiple selectors as recommended (aria-label and role attributes)
            input_selectors = [
                'textarea[placeholder*="Message"]',
                '[role="textbox"][aria-label*="Message"]',
                '[data-testid="chat-input"]',
                'textarea'
            ]
            
            for selector in input_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=8000)
                    # Additional check: make sure it's enabled and visible
                    element = await self.page.locator(selector).first()
                    if await element.is_visible() and await element.is_enabled():
                        print("✅ DeepSeek session valid (persistent session restored)")
                        return True
                except:
                    continue
            
            print("⚠️ DeepSeek session invalid - not logged in or CAPTCHA detected")
            return False
            
        except Exception as e:
            print(f"❌ Session check failed: {e}")
            return False

    async def ensure_session(self) -> bool:
        """
        Ensure session is valid, performing check if needed based on interval.
        Returns True if session is good, False if manual intervention needed.
        """
        now = time.time()
        if now - self.last_session_check > self.session_check_interval:
            return await self.check_session()
        return True  # Assume still good if checked recently

    async def login(self):
        """
        Ensure we are logged into DeepSeek.
        Relies on persistent session (cookies) in user_data_dir.
        Does NOT automate login - requires manual seeding as recommended.
        """
        await self.start_browser()
        
        print("🔐 Checking DeepSeek login status...")
        
        # Check if we already have a valid session
        if await self.check_session():
            return True
        
        print("⚠️ Not logged into DeepSeek.")
        print("📝 MANUAL SEEDING REQUIRED:")
        print("   1. Set BROWSER_HEADLESS=false in your environment")
        print("   2. Run this agent once to open the browser")
        print("   3. Manually log into https://chat.deepseek.com")
        print("   4. Solve any CAPTCHA if presented")
        print("   5. Close the browser - session will be saved")
        print("   6. Set BROWSER_HEADLESS=true and resume automation")
        print("")
        print("💡 This one-time manual seeding prevents:")
        print("   - Repeated 2FA challenges from datacenter IPs")
        print("   - Account flags from automated login attempts")
        print("   - Session trust issues with Google/DeepSeek")
        return False

    async def prompt(self, prompt_text: str) -> str:
        """
        Send a prompt to DeepSeek and return the response text.
        Uses human-like behavior and robust response detection.
        """
        if not self.is_initialized:
            await self.start_browser()
        
        # Ensure session is valid before proceeding
        if not await self.ensure_session():
            raise Exception("DeepSeek session invalid. Please manually re-seed the session.")
        
        # Ensure we are on the correct page
        await self.page.goto("https://chat.deepseek.com", wait_until="domcontentloaded")
        await self._human_delay(2000, 4000)
        
        try:
            # 1. Locate and fill the input area with human-like typing
            # Using resilient selectors (aria-label, role, placeholder)
            input_selector = 'textarea[placeholder*="Message"], [role="textbox"][aria-label*="Message"], textarea'
            await self.page.wait_for_selector(input_selector, timeout=15000)
            
            # Clear any existing text and enter prompt with human-like typing
            await self.page.fill(input_selector, "")
            await self._human_type(input_selector, prompt_text)
            
            # 2. Submit the prompt (try multiple methods)
            submit_selectors = [
                'button:has-text("Send")',
                '[aria-label="Send"]',
                'button[type="submit"]'
            ]
            
            submitted = False
            for selector in submit_selectors:
                try:
                    await self.page.click(selector)
                    submitted = True
                    break
                except:
                    continue
            
            # Fallback to Enter key if no button found
            if not submitted:
                await self.page.keyboard.press("Enter")
            
            print("📤 Prompt submitted to DeepSeek...")
            
            # 3. Wait for the response to generate with improved detection
            await self.page.wait_for_timeout(3000)  # Initial wait for response to start
            
            # Polling loop to detect when generation is finished
            max_wait = 120  # Increased timeout for very long responses
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
                'div[data-testid^="conversation-turn"]:last-child',
                '.markdown-body:last-child',
                '.prose:last-child'
            ]
            
            while elapsed < max_wait:
                await asyncio.sleep(3)
                elapsed += 3
                
                try:
                    # 1. Check for "Stop" button (Strong indicator of generation)
                    stop_button = await self.page.get_by_role("button", name="Stop").is_visible()
                    
                    if stop_button:
                        # Still generating - reset stability counter
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
                    
                    # SUCCESS CONDITION: Stop button gone AND content is stable
                    if not stop_button and current_content and current_content == last_content and len(current_content.strip()) > 10:
                        stable_count += 1
                        if stable_count >= 2:  # Require 2 consecutive stable readings
                            print("✅ Response generation complete (No stop button & stable content).")
                            return current_content.strip()
                    
                    # FALLBACK: If stop button is gone but stability is slow, return best available after 15s
                    elif not stop_button and elapsed > 15 and current_content:
                        # If we've waited a while and the stop button is gone, it's likely done
                        return current_content.strip()
                    
                    elif current_content and current_content != last_content:
                        stable_count = 0
                        last_content = current_content
                        print(f"🔄 Response content changing... ({len(current_content)} chars)")
                    elif not current_content and elapsed > 10:
                        print("⚠️ No response content detected yet...")
                        
                except Exception as e:
                    # Continue waiting on transient errors
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
            else:
                print("Please manually seed the session as instructed above.")
        finally:
            await agent.close()
    
    asyncio.run(main())