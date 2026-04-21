
import asyncio
import sys
import os
sys.path.append('/home/ubuntu/human-ai/core/agents/researcher')

from deepseek_browser_agent import DeepSeekBrowserAgent

async def debug_after_login():
    agent = DeepSeekBrowserAgent()
    try:
        print("🔧 Starting debug after login...")
        await agent.start_browser()
        
        print("🔐 Checking login status (this will use saved session)...")
        login_success = await agent.login()
        print(f"Login result: {login_success}")
        
        print(f"📍 Current URL: {agent.page.url}")
        print(f"📄 Page title: {await agent.page.title()}")
        
        # Get the full page content
        page_content = await agent.page.content()
        
        # Save it to a file for inspection
        with open('/home/ubuntu/human-ai/scripts/page_content_after_login.html', 'w') as f:
            f.write(page_content)
        print("💾 Full page content saved to page_content_after_login.html")
        
        # Also get the visible text
        visible_text = await agent.page.evaluate("() => document.body.innerText")
        with open('/home/ubuntu/human-ai/scripts/visible_text_after_login.txt', 'w') as f:
            f.write(visible_text)
        print("💾 Visible text saved to visible_text_after_login.txt")
        
        # Print first 1000 chars of visible text
        print("\n📝 First 1000 chars of visible text:")
        print(visible_text[:1000])
        
        # Let's also try to find ALL textarea elements and input elements
        textareas = await agent.page.query_selector_all('textarea')
        inputs = await agent.page.query_selector_all('input')
        print(f"\n🔍 Found {len(textareas)} textarea elements and {len(inputs)} input elements")
        
        for i, ta in enumerate(textareas[:5]):  # First 5 textareas
            placeholder = await ta.get_attribute('placeholder')
            role = await ta.get_attribute('role')
            print(f"  Textarea {i}: placeholder='{placeholder}', role='{role}'")
            
        for i, inp in enumerate(inputs[:5]):  # First 5 inputs
            placeholder = await inp.get_attribute('placeholder')
            type_attr = await inp.get_attribute('type')
            role = await inp.get_attribute('role')
            print(f"  Input {i}: placeholder='{placeholder}', type='{type_attr}', role='{role}'")
        
        # Try to find elements with specific text or attributes that might indicate chat
        chat_indicators = await agent.page.query_selector_all('*[class*="chat"], *[id*="chat"], *[class*="message"], *[id*="message"]')
        print(f"\n💬 Found {len(chat_indicators)} elements with chat/message in class/id")
        
    except Exception as e:
        print(f"❌ Debug error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(debug_after_login())
