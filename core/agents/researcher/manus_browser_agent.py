#!/usr/bin/env python3
"""
Manus AI Browser Agent - Core Implementation
Integrates high-reasoning browser agent with credit-limit awareness.
"""

import asyncio
import os
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

class ManusBrowserAgent:
    """
    Browser-based agent for interacting with Manus AI.
    Includes Google SSO persistence and daily credit limit tracking.
    """

    def __init__(self):
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        work_dir = os.getenv('WORK_DIR', '/home/ubuntu/human-ai')
        self.session_dir = os.path.join(work_dir, 'session', 'manus_profile')
        self.credit_log_path = os.path.join(work_dir, 'infrastructure/configs/manus_credits.json')
        self.is_initialized = False

    async def start_browser(self):
        """Initialize Playwright with a persistent context for Google SSO."""
        if self.is_initialized:
            return

        print("🌐 Initializing Manus Browser Agent...")
        self.pw = await async_playwright().start()
        os.makedirs(self.session_dir, exist_ok=True)
        
        headless_mode = os.getenv("BROWSER_HEADLESS", "True").lower() == "true"
        
        self.context = await self.pw.chromium.launch_persistent_context(
            user_data_dir=self.session_dir,
            headless=headless_mode,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled'],
            user_agent=self.user_agent,
            viewport={'width': 1280, 'height': 720},
        )
        
        pages = self.context.pages
        self.page = pages[0] if pages else await self.context.new_page()
        self.is_initialized = True
        print("✅ Manus Browser Agent initialized")

    def _check_credits(self) -> bool:
        """
        Track daily credit usage. 
        Returns True if credits are available, False otherwise.
        """
        try:
            if not os.path.exists(self.credit_log_path):
                with open(self.credit_log_path, 'w') as f:
                    json.dump({"last_reset": "", "used_today": 0}, f)

            with open(self.credit_log_path, 'r') as f:
                data = json.load(f)

            today = datetime.now().strftime('%Y-%m-%d')
            if data.get("last_reset") != today:
                data["last_reset"] = today
                data["used_today"] = 0
                with open(self.credit_log_path, 'w') as f:
                    json.dump(data, f)

            # Assuming a soft limit for 'complex' tasks per day
            # This can be adjusted based on actual account tier
            DAILY_LIMIT = 10 
            return data["used_today"] < DAILY_LIMIT
        except Exception as e:
            print(f"⚠️ Credit check error: {e}. Defaulting to ALLOW.")
            return True

    def _consume_credit(self):
        """Increment daily usage counter."""
        try:
            with open(self.credit_log_path, 'r') as f:
                data = json.load(f)
            data["used_today"] += 1
            with open(self.credit_log_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"⚠️ Credit logging error: {e}")

    async def prompt(self, prompt_text: str, force_complex=False) -> str:
        """
        Send a prompt to Manus AI. 
        Only proceeds if credits are available or force_complex is True.
        """
        if not self._check_credits() and not force_complex:
            return "Error: Manus AI daily credit limit reached. Use DeepSeek for this task."

        if not self.is_initialized:
            await self.start_browser()

        print("🚀 Routing complex task to Manus AI...")
        await self.page.goto("https://manus.ai", wait_until="domcontentloaded")
        
        try:
            # Selector logic tailored for Manus (to be refined during first live run)
            input_selector = 'textarea, [role="textbox"], .chat-input'
            await self.page.wait_for_selector(input_selector, timeout=15000)
            await self.page.fill(input_selector, prompt_text)
            await self.page.keyboard.press("Enter")
            
            # Wait for the "Agent is thinking/working" state to resolve
            # Manus often performs multi-step browser actions
            max_wait = 300 # Manus takes longer as it is an autonomous agent
            elapsed = 0
            last_content = ""
            
            while elapsed < max_wait:
                await asyncio.sleep(5)
                elapsed += 5
                
                # Look for the final response indicator (Stop button gone or 'Finished' state)
                # This is a placeholder for the actual Manus 'Task Complete' selector
                current_content = await self.page.locator('.message-content').last.inner_text()
                if current_content == last_content and len(current_content) > 50:
                    self._consume_credit()
                    return current_content.strip()
                last_content = current_content

            return last_content.strip() if last_content else "Error: Manus AI timed out."
            
        except Exception as e:
            print(f"❌ Manus prompt error: {e}")
            raise e

    async def close(self):
        if self.context: await self.context.close()
        if self.pw: await self.pw.stop()
        self.is_initialized = False

if __name__ == "__main__":
    async def main():
        agent = ManusBrowserAgent()
        try:
            # Test logic
            print("Manus Agent ready for SSO login.")
        finally:
            await agent.close()
    asyncio.run(main())
