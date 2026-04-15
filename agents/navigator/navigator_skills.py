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

    async def extract_dynamic_table_data(self, table_selector: str, row_selector: str = 'tr', col_selector: str = 'td') -> List[List[str]]:
        """
        Waits for a table to load and extracts its data as a list of lists (rows x columns).
        """
        print(f"📊 Extracting data from dynamic table: {table_selector}")
        try:
            # Wait for the table to be present in the DOM
            await self.navigator.page.wait_for_selector(table_selector, state='attached', timeout=30000)
            
            # Optional: Wait a bit more for potential JS rendering
            await self.navigator.page.wait_for_timeout(2000)
            
            # Locate all rows within the table
            rows = await self.navigator.page.locator(f'{table_selector} {row_selector}').all()
            
            table_data = []
            for row_locator in rows:
                # Locate all cells within the current row
                cells = await row_locator.locator(col_selector).all()
                row_text = [await cell.inner_text() for cell in cells]
                table_data.append(row_text)
            
            return table_data
        except Exception as e:
            print(f"❌ Table extraction failed: {e}")
            return []
