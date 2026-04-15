import asyncio
import json
from typing import List, Dict, Any

class NavigatorSkills:
    """
    High-level skills for the Navigator Agent to perform complex web tasks.
    """
    def __init__(self, navigator):
        self.navigator = navigator

    async def perform_login(self, url: str, credentials: Dict[str, str]):
        """
        Attempts to log into a site using provided credentials.
        """
        print(f"🔐 Attempting login at {url}...")
        await self.navigator.navigate_to(url)
        
        try:
            # Use CSS selectors instead of locator objects
            email_selector = 'input[type="email"], input[name="email"], input[name="username"]'
            pass_selector = 'input[type="password"]'
            
            await self.navigator.fill(email_selector, credentials.get('email', ''))
            await self.navigator.fill(pass_selector, credentials.get('password', ''))
            await self.navigator.press_key(pass_selector, 'Enter')
            
            await self.navigator.page.wait_for_load_state("networkidle")
            return True
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False

    async def find_and_click_link(self, target_text: str):
        """
        Searches for a link containing specific text and clicks it.
        """
        print(f"🔗 Searching for link: {target_text}")
        try:
            link = self.navigator.page.get_by_role("link", name=target_text, exact=False).first
            await self.navigator.click(link)
            return True
        except Exception as e:
            print(f"❌ Link not found: {e}")
            return False

    async def extract_structured_page_data(self, selector: str):
        """
        Extracts data from a specific section of the page.
        """
        element = self.navigator.page.locator(selector)
        return await element.inner_text()
