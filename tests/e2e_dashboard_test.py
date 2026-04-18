import asyncio
from playwright.async_api import async_playwright
import json
import time
import os

async def run_e2e_test():
    async with async_playwright() as p:
        print("🛠️ Launching Browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        url = "https://human-ai.bpushpahava.africa"
        try:
            print(f"🚀 Visiting {url}...")
            await page.goto(url, timeout=30000)
            print("✅ Page loaded.")
            
            print("🔍 Searching for input field...")
            input_selector = 'input[placeholder*="Enter research goal"]'
            await page.wait_for_selector(input_selector, timeout=15000)
            print("✅ Input field found.")
            
            test_task = f"E2E Test {int(time.time())}: Verify Pipeline"
            print(f"📝 Entering task: {test_task}")
            await page.fill(input_selector, test_task)
            
            print("🔍 Searching for launch button...")
            button_selector = 'button:has-text("Launch")'
            await page.wait_for_selector(button_selector, timeout=15000)
            await page.click(button_selector)
            print("✅ Launch button clicked.")
            
            print("⏳ Waiting for pipeline to trigger (10s)...")
            await asyncio.sleep(10)
            
            # Check MasterLog on the local server
            print("📂 Checking MasterLog.json...")
            with open('/home/ubuntu/human-ai/master_log.json', 'r') as f:
                logs = json.load(f)
                # Find the most recent log entry containing our test task
                found = any(test_task in str(log) for log in logs)
                if found:
                    print("🎉 SUCCESS: Task reached the Swarm!")
                else:
                    print("❌ FAILURE: Task not found in MasterLog.")
                    print(f"Last log entry: {logs[-1] if logs else 'Empty'}")
                    
        except Exception as e:
            print(f"❌ Test Error: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
