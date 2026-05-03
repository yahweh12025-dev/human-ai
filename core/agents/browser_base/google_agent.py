#!/usr/bin/env python3
"""
Google/Gemini Agent using Patchright base
Handles Google account login and Gemini AI interaction
"""

import asyncio
import os
from .patchright_base_agent import PatchrightBaseAgent


class GoogleAgent(PatchrightBaseAgent):
    """Agent for Google/Gemini authentication and interaction"""
    
    def __init__(self, **kwargs):
        super().__init__(identity="google", **kwargs)
        self.login_url = "https://myaccount.google.com/"
        self.gemini_url = "https://gemini.google.com/app"

    async def check_session(self) -> bool:
        """Check if Google session is valid"""
        try:
            # First check if we're already on a Google page
            await self.page.goto(self.login_url, wait_until="domcontentloaded")
            await self._human_delay(2000, 2000)
            
            # Look for signs we're logged in (profile icon, Gmail link, etc.)
            logged_in_indicators = [
                '[data-test-id="profile-badge"]',  # Google profile badge
                'a[aria-label*="Google apps"]',   # Google apps menu
                'text=Sign out',                  # Sign out button
                '[data-ved]#account-chooser-link' # Account chooser when signed in
            ]
            
            for indicator in logged_in_indicators:
                try:
                    await self.page.wait_for_selector(indicator, timeout=5000)
                    print("✅ Google session valid")
                    return True
                except:
                    continue
            
            # If not on accounts page, check Gemini directly
            await self.page.goto(self.gemini_url, wait_until="domcontentloaded")
            await self._human_delay(3000, 3000)
            
            # Check if Gemini chat input is available
            gemini_selectors = [
                '[placeholder*="Ask Gemini"]',
                '[aria-label*="Input"]',
                'textarea[aria-label*="chat"]'
            ]
            
            for selector in gemini_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    print("✅ Gemini session valid")
                    return True
                except:
                    continue
            
            print("⚠️ Google session invalid - not logged in")
            return False
            
        except Exception as e:
            print(f"❌ Google session check failed: {e}")
            return False

    async def prompt_gemini(self, prompt_text: str) -> str:
        """Send a prompt to Gemini and return response"""
        if not await self.ensure_session():
            raise Exception("Google/Gemini session invalid - manual re-seeding required")

        await self.page.goto(self.gemini_url, wait_until="domcontentloaded")
        await self._human_delay(3000, 3000)

        # Find Gemini input area
        input_selectors = [
            '[placeholder*="Ask Gemini"]',
            '[aria-label*="Input"]:not([aria-label*="Search"])',
            'textarea[aria-label*="chat"]'
        ]
        
        input_ready = False
        for selector in input_selectors:
            try:
                await self.page.wait_for_selector(selector, timeout=5000)
                await self.safe_fill(selector, prompt_text)
                input_ready = True
                break
            except:
                continue
        
        if not input_ready:
            raise Exception("Could not find Gemini input field")

        # Submit prompt (usually Enter or send button)
        await self.page.keyboard.press("Enter")
        await self._human_delay(3000, 3000)
        
        # Wait for response with stability detection
        return await self._wait_for_gemini_response()

    async def _wait_for_gemini_response(self) -> str:
        """Wait for Gemini response to complete"""
        max_wait = 120
        elapsed = 0
        last_content = ""
        stable_count = 0
        
        # Gemini response selectors
        response_selectors = [
            '[data-message-author-role="model"]:last-child',
            '.model-response:last-child',
            '[role="presentation"]:last-child .markdown'
        ]
        
        while elapsed < max_wait:
            await asyncio.sleep(3)
            elapsed += 3
            
            try:
                # Check if still generating (look for thinking indicator)
                thinking_indicators = [
                    '[aria-label*="Thinking"]',
                    '.thinking',
                    '[data-test-id="response-streaming"]'
                ]
                
                is_generating = False
                for indicator in thinking_indicators:
                    if await self.page.locator(indicator).count() > 0:
                        is_generating = True
                        break
                
                if is_generating:
                    last_content = ""
                    stable_count = 0
                    continue
                
                # Get current response content
                current_content = ""
                for selector in response_selectors:
                    try:
                        elements = await self.page.locator(selector).all()
                        if elements:
                            last_element = elements[-1]
                            current_content = await last_element.inner_text()
                            if current_content.strip():
                                break
                    except:
                        continue
                
                # Check for stability
                if current_content and current_content == last_content and len(current_content.strip()) > 10:
                    stable_count += 1
                    if stable_count >= 2:
                        return current_content.strip()
                elif current_content and current_content != last_content:
                    stable_count = 0
                    last_content = current_content
                    
            except Exception as e:
                pass  # Continue waiting
        
        return last_content.strip() if last_content.strip() else "Error: Gemini response timeout"


# Export for easy importing
__all__ = ['GoogleAgent']