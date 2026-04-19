
import asyncio
from playwright.async_api import async_playwright
import os

async def inspect_deepseek():
    pw = await async_playwright().start()
    # Using the session dir established in the agent
    session_dir = '/home/ubuntu/human-ai/session/browser_profile'
    context = await pw.chromium.launch_persistent_context(
        user_data_dir=session_dir,
        headless=False, # Headless=False to allow manual login if needed, but for test we assume logged in
        args=['--no-sandbox', '--disable-dev-shm-usage']
    )
    page = context.pages[0] if context.pages else await context.new_page()
    
    await page.goto("https://chat.deepseek.com")
    print("Waiting for page load...")
    await page.wait_for_timeout(5000)
    
    # Input prompt
    input_selector = 'textarea[placeholder*="Message"], textarea, [role="textbox"]'
    await page.fill(input_selector, "Generate a long list of 50 random facts about space.")
    await page.keyboard.press("Enter")
    print("Prompt sent. Monitoring DOM for generation markers...")
    
    # Monitor the DOM for 30 seconds
    for i in range(15):
        await asyncio.sleep(2)
        # Check for common 'stop' buttons or 'generating' indicators
        # We look for any button that might be a 'Stop generating' button
        buttons = await page.query_selector_all('button')
        stop_found = False
        for btn in buttons:
            text = await btn.inner_text()
            if "Stop" in text or "Stop generating" in text:
                stop_found = True
                break
        
        print(f"Tick {i}: Stop button found: {stop_found}")
        
    await context.close()
    await pw.stop()

if __name__ == '__main__':
    asyncio.run(inspect_deepseek())
