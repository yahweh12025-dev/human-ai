
import asyncio
import sys
import os
sys.path.append('/home/ubuntu/human-ai/core/agents/researcher')

from deepseek_browser_agent import DeepSeekBrowserAgent

async def diagnostic():
    agent = DeepSeekBrowserAgent()
    try:
        print("🔧 Starting diagnostic...")
        await agent.start_browser()
        
        print("🔐 Checking login status...")
        login_success = await agent.login()
        print(f"Login result: {login_success}")
        
        print(f"📍 Current URL: {agent.page.url}")
        print(f"📄 Page title: {await agent.page.title()}")
        
        # Take a screenshot
        await agent.page.screenshot(path="/home/ubuntu/human-ai/scripts/diagnostic_after_login.png")
        print("📸 Screenshot saved to diagnostic_after_login.png")
        
        # Now try to find the input element with a longer timeout and also print what's on the page
        try:
            # Wait for up to 20 seconds for the input
            input_selector = 'textarea[placeholder*="Message"], textarea, [role="textbox"]'
            await agent.page.wait_for_selector(input_selector, timeout=20000)
            print("✅ Input element found!")
            
            # Try to get a sample of the page text to see if we are in the chat
            page_text = await agent.page.inner_text('body')
            if "Message" in page_text or "chat" in page_text.lower():
                print("📝 Page contains chat-related text")
            else:
                print("📝 Page text (first 500 chars):")
                print(page_text[:500])
        except Exception as e:
            print(f"❌ Failed to find input element: {e}")
            # Take another screenshot for debugging
            await agent.page.screenshot(path="/home/ubuntu/human-ai/scripts/diagnostic_no_input.png")
            print("📸 Screenshot saved to diagnostic_no_input.png")
            
    except Exception as e:
        print(f"❌ Diagnostic error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(diagnostic())
