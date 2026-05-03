#!/usr/bin/env python3
import os
import json
from typing import Dict, Any
from playwright.async_api import async_playwright

class N8nAgent:
    def __init__(self):
        self.api_key = os.getenv("N8N_API_KEY")
        self.n8n_url = os.getenv("N8N_URL", "http://localhost:5678")
        self.n8n_username = os.getenv("N8N_USERNAME")
        self.n8n_password = os.getenv("N8N_PASSWORD")
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None

    async def start_browser(self):
        if self.pw is not None:
            return
        print("🌐 Initializing browser for n8n...")
        self.pw = await async_playwright().start()
        # Use a persistent context? We'll use a temporary one for now.
        user_data_dir = os.path.join(os.getenv("WORK_DIR", "/home/yahwehatwork/human-ai"), "session", "n8n_profile")
        os.makedirs(user_data_dir, exist_ok=True)
        headless = os.getenv("BROWSER_HEADLESS", "True").lower() == "true"
        self.context = await self.pw.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--disable-blink-features=AutomationControlled'],
        )
        self.page = await self.context.new_page()
        print("✅ Browser for n8n initialized")

    async def close(self):
        if self.context:
            await self.context.close()
        if self.pw:
            await self.pw.stop()
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        print("🌐 Browser for n8n closed")

    async def login_if_needed(self):
        # Check if we are already logged in by visiting the n8n URL and looking for a sign of being logged in
        await self.page.goto(self.n8n_url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(2000)
        # We'll check for an element that indicates we are logged in, e.g., the user avatar or a logout button
        # We'll use a common selector for n8n: the user menu in the top right
        try:
            await self.page.wait_for_selector("nav .user-menu", timeout=5000)
            print("🔐 Already logged into n8n")
            return
        except:
            print("🔐 Not logged into n8n, attempting to log in")

        # Go to the login page
        await self.page.goto(f"{self.n8n_url}/login", wait_until="domcontentloaded")
        await self.page.wait_for_timeout(2000)

        # Fill in the login form
        # We'll try common selectors for email/username and password
        await self.page.fill('input[name="email"], input[name="username"]', self.n8n_username)
        await self.page.fill('input[name="password"]', self.n8n_password)
        await self.page.click('button[type="submit"]')

        # Wait for login to complete
        await self.page.wait_for_timeout(5000)
        # Check if we are logged in by looking for the user menu again
        try:
            await self.page.wait_for_selector("nav .user-menu", timeout=10000)
            print("✅ Logged into n8n successfully")
        except:
            raise Exception("Failed to log into n8n")

    async def trigger_workflow(self, workflow_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Triggers a specific n8n workflow via the browser and returns the result.
        """
        print(f"🌐 Triggering n8n workflow via browser: {workflow_id}...")
        try:
            await self.start_browser()
            await self.login_if_needed()
            
            # Navigate to the workflow page
            workflow_url = f"{self.n8n_url}/workflow/{workflow_id}"
            await self.page.goto(workflow_url, wait_until="domcontentloaded")
            await self.page.wait_for_timeout(2000)
            
            # Click the execute workflow button
            # We'll use a button with the text "Execute Workflow"
            execute_button = self.page.get_by_role("button", name="Execute Workflow")
            await execute_button.click()
            
            # Wait for the execution to start (we'll wait for a confirmation toast or the execution list to update)
            await self.page.wait_for_timeout(5000)
            
            # For now, we'll return a success message
            # In a real implementation, we might want to capture the execution ID or status
            print(f"✅ Workflow {workflow_id} triggered successfully via browser")
            return {"status": "success", "workflow_id": workflow_id}
        except Exception as e:
            print(f"❌ n8n workflow error: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            # We'll keep the browser open for potential reuse
            # Uncomment the following line if you want to close after each trigger
            # await self.close()
            pass

async def main():
    agent = N8nAgent()
    print("✅ N8n Agent Initialized")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())