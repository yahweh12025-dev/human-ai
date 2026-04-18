
#!/usr/bin/env python3
"""
Debug script to see what page we are on when navigating to gemini.google.com
"""
import asyncio
import os
import sys
sys.path.insert(0, '/home/ubuntu/human-ai')

from agents.gemini.gemini_agent import GeminiBrowserAgent

async def debug():
    agent = GeminiBrowserAgent(use_chrome_profile=False)
    try:
        await agent.start_browser()
        await agent.page.goto("https://gemini.google.com", wait_until="networkidle")
        await agent.page.wait_for_timeout(5000)
        # Get the page content and save to file
        content = await agent.page.content()
        with open("/home/ubuntu/human-ai/gemini_debug.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("Page content saved to gemini_debug.html")
        # Also get the URL
        url = agent.page.url
        print(f"Current URL: {url}")
        # Take a screenshot
        await agent.page.screenshot(path="/home/ubuntu/human-ai/gemini_debug.png")
        print("Screenshot saved to gemini_debug.png")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await agent.close()

asyncio.run(debug())
