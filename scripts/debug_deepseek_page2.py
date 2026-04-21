import asyncio
from playwright.async_api import async_playwright
import os

async def debug_page():
    pw = await async_playwright().start()
    session_dir = '/home/ubuntu/human-ai/session/browser_profile_enhanced'
    os.makedirs(session_dir, exist_ok=True)
    
    # Launch browser so we can see what's happening
    context = await pw.chromium.launch_persistent_context(
        user_data_dir=session_dir,
        headless=False,  # So we can see the browser
        args=['--no-sandbox', '--disable-dev-shm-usage']
    )
    
    pages = context.pages
    if pages:
        page = pages[0]
    else:
        page = await context.new_page()
    
    await page.goto("https://chat.deepseek.com")
    await page.wait_for_timeout(5000)
    
    print("URL:", page.url)
    print("Title:", await page.title())
    
    # Get page content
    content = await page.content()
    # Save to file for inspection
    with open('/home/ubuntu/human-ai/scripts/debug_page_content.html', 'w') as f:
        f.write(content)
    print("Page content saved to debug_page_content.html")
    
    # Check for common CAPTCHA indicators
    if "Human Verification" in content:
        print("Found 'Human Verification' in page content")
    if "captcha" in content.lower():
        print("Found 'captcha' in page content (lowercase)")
    if "Please verify you are a human" in content:
        print("Found 'Please verify you are a human'")
    
    # Let's also look for input elements
    inputs = await page.query_selector_all('input')
    textareas = await page.query_selector_all('textarea')
    print(f"Found {len(inputs)} input elements")
    print(f"Found {len(textareas)} textarea elements")
    
    # Print a snippet of the page text
    page_text = await page.inner_text('body')
    print("First 2000 characters of page text:")
    print(page_text[:2000])
    
    # Keep browser open for a bit so we can see
    await page.wait_for_timeout(10000)
    
    await context.close()
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(debug_page())