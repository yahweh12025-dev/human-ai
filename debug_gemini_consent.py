
#!/usr/bin/env python3
"""
Debug script to handle Google consent page and then proceed to Gemini.
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
        
        # Check if we are on a consent page
        if "consent.google.com" in agent.page.url:
            print("On consent page, attempting to accept...")
            # Look for the accept button - common selectors
            accept_selectors = [
                'button:has-text("I agree")',
                'button:has-text("Accept all")',
                'button:has-text("Accept")',
                '#introAgreeButton',  # common id
                'button[aria-label*="Accept"]',
            ]
            accepted = False
            for selector in accept_selectors:
                try:
                    await agent.page.wait_for_selector(selector, timeout=5000)
                    await agent.page.click(selector)
                    print(f"Clicked accept button with selector: {selector}")
                    accepted = True
                    break
                except:
                    continue
            
            if not accepted:
                # Try to find any button with text containing "agree" or "accept" using XPath
                try:
                    await agent.page.click('xpath=//button[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "agree") or contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "accept")]')
                    print("Clicked accept button via XPath")
                    accepted = True
                except:
                    pass
            
            if accepted:
                # Wait for navigation to Gemini
                await agent.page.wait_for_url("**/gemini.google.com/**", timeout=10000)
                print("Navigated to Gemini after consent")
            else:
                print("Could not find accept button on consent page")
        
        # Now we should be on Gemini
        await agent.page.wait_for_timeout(5000)
        content = await agent.page.content()
        with open("/home/ubuntu/human-ai/gemini_after_consent.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("Page content after consent saved to gemini_after_consent.html")
        url = agent.page.url
        print(f"Current URL: {url}")
        
        # Take a screenshot
        await agent.page.screenshot(path="/home/ubuntu/human-ai/gemini_after_consent.png")
        print("Screenshot saved to gemini_after_consent.png")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await agent.close()

asyncio.run(debug())
