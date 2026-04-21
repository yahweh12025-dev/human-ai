
import asyncio
from playwright.async_api import async_playwright
import os

async def debug_deepseek_page():
    pw = await async_playwright().start()
    session_dir = '/home/ubuntu/human-ai/session/browser_profile'
    
    # Launch with visible browser for debugging
    context = await pw.chromium.launch_persistent_context(
        user_data_dir=session_dir,
        headless=False,  # Visible so we can see what's happening
        args=['--no-sandbox', '--disable-dev-shm-usage']
    )
    
    # Get or create page
    pages = context.pages
    if pages:
        page = pages[0]
    else:
        page = await context.new_page()
    
    try:
        print("🌐 Navigating to DeepSeek...")
        await page.goto("https://chat.deepseek.com", wait_until="networkidle")
        await page.wait_for_timeout(5000)
        
        print(f"📄 Current URL: {page.url}")
        print(f"📄 Page title: {await page.title()}")
        
        # Check if we're logged in by looking for common indicators
        # Try to find the input area
        selectors_to_try = [
            'textarea[placeholder*="Message"]',
            'textarea',
            '[role="textbox"]',
            '.chat-input textarea',
            '#chat-input'
        ]
        
        for selector in selectors_to_try:
            try:
                element = await page.wait_for_selector(selector, timeout=3000)
                if element:
                    print(f"✅ Found input with selector: {selector}")
                    # Try to get placeholder or other attributes
                    placeholder = await element.get_attribute('placeholder')
                    print(f"   Placeholder: {placeholder}")
                    break
            except:
                print(f"❌ Selector not found: {selector}")
                continue
        
        # Take a screenshot for debugging
        await page.screenshot(path="/home/ubuntu/human-ai/scripts/debug_deepseek.png")
        print("📸 Screenshot saved to /home/ubuntu/human-ai/scripts/debug_deepseek.png")
        
        # Get page content to see what's actually there
        content = await page.content()
        with open('/home/ubuntu/human-ai/scripts/debug_deepseek.html', 'w') as f:
            f.write(content)
        print("💾 Page source saved to debug_deepseek.html")
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
    finally:
        print("⏳ Keeping browser open for 10 seconds for manual inspection...")
        await page.wait_for_timeout(10000)
        await context.close()
        await pw.stop()

if __name__ == "__main__":
    asyncio.run(debug_deepseek_page())
