import asyncio
from playwright.async_api import async_playwright

async def main():
    print("Starting Playwright test...")
    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.launch(headless=True)
        print("Browser launched!")
        page = await browser.new_page()
        print("Page created!")
        await page.goto("https://www.google.com")
        print("Navigated to Google!")
        await browser.close()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
