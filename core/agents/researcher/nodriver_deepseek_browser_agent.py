#!/usr/bin/env python3
"""
Nodriver-based DeepSeek Browser Agent
Uses nodriver (undetected-chromedriver) for stealth automation.
"""

import asyncio
import os
import json
import random
import time
from pathlib import Path
from typing import Optional
import nodriver as nd
from nodriver import cdp


class NodriverDeepSeekAgent:
    """
    Browser-based agent for interacting with DeepSeek chat via nodriver.
    Uses stealth settings and human-like behavior to avoid detection.
    """

    def __init__(self, session_dir: Optional[str] = None):
        self.driver: Optional[nd.Browser] = None
        self.tab: Optional[nd.Tab] = None
        
        # Use WORK_DIR if provided, else default to project root
        work_dir = os.getenv('WORK_DIR', '/home/yahwehatwork/human-ai')
        if session_dir is None:
            self.session_dir = os.path.join(work_dir, 'browser_profiles', 'deepseek_nodriver')
        else:
            self.session_dir = session_dir
            
        # Create session directory
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Realistic user agent (rotating)
        self.user_agent = self._get_realistic_user_agent()
        
        # Human-like behavior settings
        self.min_delay = 0.15  # seconds (150 ms)
        self.max_delay = 0.4   # seconds (400 ms)
        self.last_action_time = 0
        
        # Session watchdog settings
        self.session_check_interval = 300  # 5 minutes
        self.last_session_check = 0
        
        # Anti-detection arguments for nodriver
        self.stealth_args = [
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
            f'--user-data-dir={self.session_dir}',
            f'--user-agent={self.user_agent}',
        ]

    def _get_realistic_user_agent(self) -> str:
        """Generate a realistic user agent string"""
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

    async def _human_delay(self, min_sec: Optional[float] = None, max_sec: Optional[float] = None):
        """Add a small random delay to mimic human behavior"""
        min_sec = min_sec or self.min_delay
        max_sec = max_sec or self.max_delay
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)
        self.last_action_time = time.time()

    async def _human_type(self, element: nd.Element, text: str):
        """Type text with human-like delays between characters"""
        await element.clear()
        await self._human_delay(0.1, 0.3)
        
        # Type with variable speed like a human
        for i, char in enumerate(text):
            await element.send_keys(char)
            # Variable delay: faster for common words, slower for punctuation/caps
            if char.isalpha() and i > 0 and text[i-1].isalpha():
                delay_range = (0.05, 0.15)  # Fast for letters in words
            else:
                delay_range = (0.1, 0.3)    # Slow for punctuation, caps, start
            await self._human_delay(*delay_range)

    async def _human_click(self, element: nd.Element):
        """Click with human-like movement and delay"""
        # Get element bounding box for realistic click position
        box = await element.get_bounding_box()
        if box:
            x = box['left'] + box['width'] / 2 + random.uniform(-3, 3)
            y = box['top'] + box['height'] / 2 + random.uniform(-3, 3)
            await self.driver.mouse.move(x, y, steps=random.randint(5, 15))
            await self._human_delay(0.1, 0.3)
            await self.driver.mouse.click(x, y)
        else:
            await element.click()
        await self._human_delay()

    async def start_browser(self, headless: bool = True):
        """Initialize nodriver browser with stealth settings"""
        if self.driver is not None:
            return

        print("🌐 Initializing Nodriver DeepSeek Agent...")
        
        # Prepare launch arguments
        args = self.stealth_args.copy()
        if headless:
            args.append('--headless=new')  # Use new headless mode if available
        
        # Start browser
        self.driver = await nd.start(
            browser_args=args,
            headless=headless,
            # Note: nodriver handles user-agent and user-data-dir via args above
        )
        
        # Get the main tab
        self.tab = self.driver.main_tab
        await self.tab.wait_for_ready()
        
        """Initialize nodriver browser with stealth settings"""
        if self.driver is not None:
            return

        print("🌐 Initializing Nodriver DeepSeek Agent...")

        # Prepare launch arguments
        args = self.stealth_args.copy()
        if headless:
            args.append('--headless=new')  # Use new headless mode if available

        # Start browser
        self.driver = await nd.start(
            browser_args=args,
            headless=headless,
            sandbox=False,  # Required when running as root
            # Note: nodriver handles user-agent and user-data-dir via args above
        )

        # Get the main tab
        self.tab = self.driver.main_tab
        await self.tab.wait_for_ready()

        self.is_initialized = True
        print("✅ Nodriver DeepSeek Agent initialized")
    async def check_session(self) -> bool:
        """
        Session watchdog: Check if we're still authenticated.
        Returns True if session is valid, False if re-authentication needed.
        """
        try:
            # Update last check time
            self.last_session_check = time.time()
            
            # Navigate to DeepSeek chat
            await self.driver.get("https://chat.deepseek.com")
            await self._human_delay(2, 4)  # Human-like pause after navigation
            
            # Check if we're already logged in by looking for the chat input area
            input_selectors = [
                'textarea[placeholder*="Message"]',
                '[role="textbox"][aria-label*="Message"]',
                '[data-testid="chat-input"]',
                'textarea'
            ]
            
            for selector in input_selectors:
                try:
                    elements = await self.tab.select_all(selector, timeout=5)
                    if elements:
                        element = elements[0]
                        if await element.is_displayed() and await element.is_enabled():
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

    async def login(self, headless: bool = False) -> bool:
        """
        Ensure we are logged into DeepSeek.
        Relies on persistent session (cookies) in user_data_dir.
        Does NOT automate login - requires manual seeding as recommended.
        """
        await self.start_browser(headless=headless)
        
        print("🔐 Checking DeepSeek login status...")
        
        # Check if we already have a valid session
        if await self.check_session():
            return True
        
        print("⚠️ Not logged into DeepSeek.")
        print("📝 MANUAL SEEDING REQUIRED:")
        print("   1. Set headless=False in login() or use start_browser(headless=False)")
        print("   2. Run this agent once to open the browser")
        print("   3. Manually log into https://chat.deepseek.com")
        print("   4. Solve any CAPTCHA if presented")
        print("   5. Close the browser - session will be saved in user data dir")
        print("   6. Set headless=True and resume automation")
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
        if self.driver is None:
            await self.start_browser(headless=True)
        
        # Ensure session is valid before proceeding
        if not await self.ensure_session():
            raise Exception("DeepSeek session invalid. Please manually re-seed the session.")
        
        # Ensure we are on the correct page
        await self.driver.get("https://chat.deepseek.com")
        await self._human_delay(2, 4)
        
        try:
            # 1. Locate and fill the input area with human-like typing
            # Using resilient selectors (aria-label, role, placeholder)
            input_selectors = [
                'textarea[placeholder*="Message"]',
                '[role="textbox"][aria-label*="Message"]',
                '[data-testid="chat-input"]',
                'textarea'
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    elements = await self.tab.select_all(selector, timeout=10)
                    if elements:
                        input_element = elements[0]
                        break
                except:
                    continue
            
            if input_element is None:
                raise Exception("Could not find chat input element")
            
            # Clear any existing text and enter prompt with human-like typing
            await self._human_type(input_element, prompt_text)
            
            # 2. Submit the prompt (try multiple methods)
            submit_selectors = [
                'button:has-text("Send")',
                '[aria-label="Send"]',
                'button[type="submit"]'
            ]
            
            submitted = False
            for selector in submit_selectors:
                try:
                    elements = await self.tab.select_all(selector, timeout=5)
                    if elements:
                        await self._human_click(elements[0])
                        submitted = True
                        break
                except:
                    continue
            
            # Fallback to Enter key if no button found
            if not submitted:
                await self.tab.send_keys("Enter")
            
            print("📤 Prompt submitted to DeepSeek...")
            
            # 3. Wait for the response to generate with improved detection
            await self._human_delay(2, 3)  # Initial wait for response to start
            
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
                await asyncio.sleep(2)
                elapsed += 2
                
                try:
                    # 1. Check for "Stop" button (Strong indicator of generation)
                    stop_button_elements = await self.tab.select_all('button:has-text("Stop")', timeout=1)
                    is_generating = len(stop_button_elements) > 0
                    
                    if is_generating:
                        # Still generating - reset stability counter
                        last_content = ""
                        stable_count = 0
                        continue
                    
                    # 2. Content Stability Check
                    current_content = ""
                    for selector in message_selectors:
                        try:
                            elements = await self.tab.select_all(selector, timeout=1)
                            if elements:
                                last_element = elements[-1]
                                current_content = await last_element.get_content()
                                if current_content.strip():
                                    break
                        except:
                            continue
                    
                    # SUCCESS CONDITION: Stop button gone AND content is stable
                    if not is_generating and current_content and current_content == last_content and len(current_content.strip()) > 10:
                        stable_count += 1
                        if stable_count >= 2:  # Require 2 consecutive stable readings
                            print("✅ Response generation complete (No stop button & stable content).")
                            return current_content.strip()
                    
                    # FALLBACK: If stop button is gone but stability is slow, return best available after 15s
                    elif not is_generating and elapsed > 15 and current_content:
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
            if self.driver:
                await self.driver.stop()
        except Exception as e:
            print(f"Error stopping driver: {e}")
        finally:
            self.driver = None
            self.tab = None
            self.is_initialized = False
            print("🌐 Nodriver DeepSeek Agent closed")


# Example usage and simple test
async def _example_usage():
    """Example of how to use the agent"""
    agent = NodriverDeepSeekAgent()
    try:
        # First, you need to manually seed the session (login once with headless=False)
        # Uncomment the following lines to do manual seeding:
        # logged_in = await agent.login(headless=False)
        # if not logged_in:
        #     print("Please complete manual login and restart.")
        #     return
        
        # For testing with an existing session (assuming you've seeded it):
        logged_in = await agent.login(headless=True)
        if logged_in:
            response = await agent.prompt("Hello! Who are you?")
            print(f"Response: {response}")
        else:
            print("Please manually seed the session as instructed above.")
    finally:
        await agent.close()


if __name__ == "__main__":
    # Run the example
    asyncio.run(_example_usage())
