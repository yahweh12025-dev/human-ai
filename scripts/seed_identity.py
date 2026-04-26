#!/usr/bin/env python3
"""
Manual seeding script for a browser identity (e.g., google, deepseek).
Run with: BROWSER_HEADLESS=false xvfb-run -a python3 seed_identity.py <identity>
Example: BROWSER_HEADLESS=false xvfb-run -a python3 seed_identity.py deepseek
"""
import asyncio
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from core.agents.browser_base.patchright_base_agent import PatchrightBaseAgent

class IdentityAgent(PatchrightBaseAgent):
    def __init__(self, identity: str, **kwargs):
        super().__init__(identity=identity, **kwargs)
        # Set the login URL based on identity
        if identity == "google":
            self.login_url = "https://myaccount.google.com/"
        elif identity == "deepseek":
            self.login_url = "https://chat.deepseek.com"
        else:
            # Generic login URL - user must set in subclass or we try to detect
            self.login_url = os.getenv(f"{identity.upper()}_LOGIN_URL", "about:blank")

    async def check_session(self) -> bool:
        """Check if we are logged in for this identity."""
        try:
            await self.page.goto(self.login_url, wait_until="domcontentloaded")
            await self._human_delay(2000, 4000)
            
            # Try to find signs of being logged in - this is identity-specific
            # For now, we use a generic check: look for common logged-in indicators
            # Subclasses should override this for better accuracy.
            logged_in_indicators = [
                # Google
                '[data-test-id="profile-badge"]',
                'a[aria-label*="Google apps"]',
                'text=Sign out',
                # DeepSeek
                'textarea[placeholder*="Message"]',
                '[role="textbox"][aria-label*="Message"]',
                '[data-testid="chat-input"]',
                'textarea'
            ]
            
            for indicator in logged_in_indicators:
                try:
                    await self.page.wait_for_selector(indicator, timeout=5000)
                    # Additional check: make sure it's enabled and visible for input selectors
                    if 'textarea' in indicator or 'textbox' in indicator:
                        element = await self.page.locator(indicator).first()
                        if await element.is_visible() and await element.is_enabled():
                            print(f"✅ {self.identity} session valid (logged in)")
                            return True
                    else:
                        # For non-input indicators, just presence is enough
                        print(f"✅ {self.identity} session valid (logged in indicator found)")
                        return True
                except:
                    continue
            
            print(f"⚠️ {self.identity} session invalid - not logged in or CAPTCHA detected")
            return False
        except Exception as e:
            print(f"❌ Session check failed for {self.identity}: {e}")
            return False

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 seed_identity.py <identity> [headless]")
        print("Example: python3 seed_identity.py deepseek false")
        sys.exit(1)
    
    identity = sys.argv[1]
    headless = sys.argv[2].lower() if len(sys.argv) > 2 else "true"
    headless_bool = headless == "true"
    
    print(f"🌐 Seeding {identity} session (headless={headless_bool})")
    
    agent = IdentityAgent(identity=identity, headless=headless_bool)
    try:
        await agent.start_browser()
        if agent.headless:
            print("💡 Running in headless mode. If you need to interact manually, set headless=false.")
        else:
            print("💡 Running in headed mode. Please interact with the browser to log in.")
        
        print(f"🔐 Please manually log into {agent.login_url}")
        print("   Solve any CAPTCHA if presented.")
        print("   After logging in, the script will detect success and close.")
        print("   If you need to abort, press Ctrl+C.")
        
        # Wait for login by periodically checking session
        while True:
            await asyncio.sleep(5)
            if await agent.check_session():
                print(f"✅ {identity} session seeded successfully!")
                break
            else:
                print(f"⏳ Waiting for {identity} login... (checking again in 5 seconds)")
    except KeyboardInterrupt:
        print(f"\n🛑 Seeding aborted by user for {identity}.")
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
