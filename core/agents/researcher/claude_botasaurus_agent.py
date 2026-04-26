#!/usr/bin/env python3
"""
Claude Browser Agent using Botasaurus for Cloudflare bypass.
Uses persistent Google Chrome profile for login state.
"""

import asyncio
import os
from typing import Optional
from botasaurus.browser import browser, Driver

class ClaudeBotasaurusAgent:
    """
    Browser-based agent for interacting with Claude.ai using Botasaurus.
    Uses persistent Google Chrome profile for maintaining login state.
    """

    def __init__(self, profile_path: str = None):
        """
        Initialize the agent.
        
        Args:
            profile_path: Path to the Chrome profile. If None, uses default.
        """
        if profile_path is None:
            # Default to the Google profile in the human-ai directory
            self.profile_path = os.path.join(
                os.getenv('WORK_DIR', '/home/yahwehatwork/human-ai'),
                '.browser-profile',
                'google'
            )
        else:
            self.profile_path = profile_path
        
        self.driver = None
        self.is_initialized = False

    def _start_browser(self):
        """Start the Botasaurus browser with the Google profile."""
        if self.is_initialized:
            return
        
        print(f"🌐 Initializing Claude Botasaurus Agent with profile: {self.profile_path}")
        
        # We'll use the browser decorator in a helper function
        # Since Botasaurus is designed to be used with decorators, we create a helper
        self._run_browser_task()
        self.is_initialized = True

    def _run_browser_task(self):
        """Define and run the browser task."""
        # This is a bit tricky because Botasaurus uses decorators.
        # We'll create a helper function that we can call.
        
        @browser(
            user_data_dir=self.profile_path,
            headless=True,  # We can make this configurable
            close_on_crash=True,
            wait_for_complete_page_load=True,
            # Optional: add arguments to make it more stealthy
            # chrome_args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        def claude_task(driver: Driver, data):
            # Navigate to Claude.ai with Cloudflare bypass
            driver.google_get("https://claude.ai/chat", bypass_cloudflare=True)
            # Wait for the chat interface to load
            try:
                driver.wait_for_element("textarea[placeholder='Ask Claude anything']", timeout=15)
                # If we get here, we are logged in and past Cloudflare
                self.chat_input_selector = "textarea[placeholder='Ask Claude anything']"
                self.submit_button_selector = "button:has-text('Send')"
                return True
            except Exception as e:
                print(f"⚠️  Could not find chat input: {e}")
                # Maybe we are not logged in? Let's check for login button
                try:
                    # Check if we see the Google login button
                        driver.wait_for_element("text=Continue with Google", timeout=5)
                        self.needs_login = True
                except:
                    self.needs_login = False
                return False

        # We need to run the task and capture the result.
        # However, the browser decorator runs the function and returns the result.
        # We'll store the driver and state in the instance.
        # This is a simplified approach; for production, we might want to manage the driver more carefully.
        
        # Instead, let's use a different approach: we'll create a driver instance manually.
        # But Botasaurus doesn't expose a simple way to create a driver without the decorator.
        # Given the constraints, we'll use the decorator and store the result in a closure.
        
        # We'll use a mutable container to store the result
        result = {'success': False, 'needs_login': False, 'driver': None}
        
        @browser(
            user_data_dir=self.profile_path,
            headless=True,
            close_on_crash=True,
            wait_for_complete_page_load=True
        )
        def init_task(driver: Driver, data):
            # Store the driver so we can reuse it
            result['driver'] = driver
            # Navigate to Claude.ai with Cloudflare bypass
            driver.google_get("https://claude.ai/chat", bypass_cloudflare=True)
            # Wait for the chat interface to load
            try:
                driver.wait_for_element("textarea[placeholder='Ask Claude anything']", timeout=15)
                result['success'] = True
                result['chat_input_selector'] = "textarea[placeholder='Ask Claude anything']"
                result['submit_button_selector'] = "button:has-text('Send')"
            except Exception as e:
                print(f"⚠️  Could not find chat input: {e}")
                # Check if we need to log in
                try:
                    driver.wait_for_element("text=Continue with Google", timeout=5)
                    result['needs_login'] = True
                except:
                    result['needs_login'] = False
        
        # Run the task
        init_task({}, {})
        
        # Store the state
        self.driver = result['driver']
        self.success = result.get('success', False)
        self.needs_login = result.get('needs_login', False)
        self.chat_input_selector = result.get('chat_input_selector')
        self.submit_button_selector = result.get('submit_button_selector')
        
        if self.success:
            print("✅ Claude Botasaurus Agent initialized and logged in.")
        elif self.needs_login:
            print("⚠️  Claude Botasaurus Agent initialized but login required.")
        else:
            print("❌ Claude Botasaurus Agent initialized but unknown state.")

    async def start_browser(self):
        """Start the browser (async wrapper for the synchronous start)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._start_browser)

    def login(self):
        """
        Check if we are logged in. If not, we cannot automate login - requires manual seeding.
        Returns True if logged in, False otherwise.
        """
        if not self.is_initialized:
            # This should not happen if we call start_browser first, but just in case
            self._start_browser()
        
        if self.success:
            return True
        elif self.needs_login:
            print("🔐 Not logged into Claude.ai.")
            print("📝 MANUAL SEEDING REQUIRED:")
            print("   1. Set headless=False in the agent configuration (or use the seeding script)")
            print("   2. Run this agent once to open the browser")
            print("   3. Manually log into https://claude.ai via Google account")
            print("   4. Solve any CAPTCHA if presented")
            print("   5. Close the browser - session will be saved in Google profile")
            print("   6. Set headless=True and resume automation")
            return False
        else:
            print("❌ Unknown login state. Please check the browser manually.")
            return False

    def prompt(self, prompt_text: str) -> str:
        """
        Send a prompt to Claude.ai and return the response text.
        """
        if not self.is_initialized:
            # This is a synchronous method, but we'll run the browser start in a thread if needed
            # For simplicity, we assume start_browser has been called.
            # In a real async environment, we would make this async.
            # Since the researcher agent calls this from an async context, we'll make it async.
            # But for now, let's keep it synchronous and note that the researcher agent must call start_browser first.
            pass
        
        if not self.success:
            if self.needs_login:
                raise Exception("Claude session invalid. Please manually re-seed the session.")
            else:
                raise Exception("Claude agent not initialized properly.")
        
        # Use the stored driver to interact with the page
        driver = self.driver
        
        # Ensure we are on the correct page
        driver.google_get("https://claude.ai/chat", bypass_cloudflare=True)
        
        # Wait for the chat input (should be fast if we are already there)
        try:
            driver.wait_for_element(self.chat_input_selector, timeout=5)
        except:
            # If we get timed out, try to recover by waiting a bit longer
            driver.wait_for_element(self.chat_input_selector, timeout=15)
        
        # Clear any existing text and enter prompt
        driver.input(self.chat_input_selector, prompt_text)
        
        # Click the send button
        driver.click(self.submit_button_selector)
        
        # Wait for the response to generate
        # We'll wait for the stop button to disappear and then for the response to stabilize
        max_wait = 60  # seconds
        elapsed = 0
        last_response = ""
        stable_count = 0
        
        while elapsed < max_wait:
            # Check if the stop button is still visible (indicating generation)
            try:
                stop_button_visible = driver.is_element_visible("button:has-text('Stop')", timeout=1)
            except:
                stop_button_visible = False
            
            if stop_button_visible:
                # Still generating, wait a bit more
                asyncio.sleep(2)
                elapsed += 2
                continue
            
            # Stop button is not visible, try to get the last response
            try:
                # Get the last message from the assistant
                # We'll use a selector for the last message in the chat
                # This selector might need adjustment based on Claude's DOM
                last_message = driver.get_text(".message:last-child", timeout=2)
                if last_message and last_message != last_response:
                    # Response is still changing
                    last_response = last_message
                    stable_count = 0
                elif last_message and last_message == last_response:
                    # Response is stable
                    stable_count += 1
                    if stable_count >= 2:  # Require 2 consecutive stable readings
                        return last_response.strip()
                # If we get no message, we might be waiting for the first response
                # We'll treat empty as not changing
            except:
                # If we can't get the message, we'll wait a bit
                pass
            
            # Wait before checking again
            asyncio.sleep(2)
            elapsed += 2
        
        # If we timed out, return the last response we got
        if last_response:
            return last_response.strip()
        else:
            return "Error: Response timeout after waiting."

    def close(self):
        """Clean up browser resources."""
        if self.driver:
            try:
                self.driver.close()
            except Exception as e:
                print(f"Error closing driver: {e}")
            finally:
                self.driver = None
                self.is_initialized = False
                print("🌐 Claude Botasaurus Agent closed")

# For testing and manual seeding, we can add a headed mode method
def seed_login():
    """
    Manual seeding function to log into Claude.ai using Botasaurus in headed mode.
    """
    print("🌐 Starting Claude Botasaurus Agent for manual seeding (headed mode)...")
    print("📝 Please log into Claude.ai using your Google account.")
    print("🛑 After successful login, CLOSE THE BROWSER WINDOW to finish.")
    print("")
    
    agent = ClaudeBotasaurusAgent()
    try:
        # Override to use headed mode for seeding
        # We'll create a new agent with headless=False
        @browser(
            user_data_dir=agent.profile_path,
            headless=False,  # Headed mode for manual interaction
            close_on_crash=True,
            wait_for_complete_page_load=True
        )
        def seeding_task(driver: Driver, data):
            # Navigate to Claude.ai with Cloudflare bypass
            driver.google_get("https://claude.ai/chat", bypass_cloudflare=True)
            # Wait for the chat input to see if we are logged in
            try:
                driver.wait_for_element("textarea[placeholder='Ask Claude anything']", timeout=30)
                print("✅ Successfully logged into Claude.ai!")
                # Keep the browser open until the user closes it
                print("💡 You can now close the browser to save the session.")
                # Wait for the user to close the browser
                while True:
                    # Check if the browser is still open
                    if not driver:
                        break
                    # Sleep to avoid busy waiting
                    import time
                    time.sleep(1)
            except Exception as e:
                print(f"⚠️  Could not find chat input after waiting: {e}")
                print("💡 Please log in manually and then close the browser.")
                # Still wait for the user to close the browser
                while True:
                    if not driver:
                        break
                    import time
                    time.sleep(1)
        
        # Run the seeding task
        seeding_task({}, {})
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
    finally:
        # The driver should be closed by the user closing the window, but we try to clean up
        if agent.driver:
            try:
                agent.driver.close()
            except:
                pass

if __name__ == "__main__":
    # If run directly, we can test the agent
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        seed_login()
    else:
        # Simple test
        agent = ClaudeBotasaurusAgent()
        try:
            agent.start_browser()
            if agent.login():
                resp = agent.prompt("Hello! Who are you?")
                print(f"Response: {resp[:200]}")
            else:
                print("Please run with 'seed' argument to perform manual seeding.")
                print("Example: python3 claude_botasaurus_agent.py seed")
        finally:
            agent.close()