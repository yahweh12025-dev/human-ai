#!/usr/bin/env python3
"""
Script to run the nodriver DeepSeek agent login for manual seeding.
This will start a visible browser so you can manually log into DeepSeek.
"""

import asyncio
import sys
import os

# Add the human-ai directory to the path
sys.path.insert(0, '/home/yahwehatwork/human-ai')

async def main():
    print("🚀 Starting Nodriver DeepSeek Agent for Manual Login")
    print("=" * 60)
    
    # Import the agent
    from core.agents.researcher.nodriver_deepseek_browser_agent import NodriverDeepSeekAgent
    
    # Create agent instance
    agent = NodriverDeepSeekAgent()
    print("✅ Agent created successfully")
    
    try:
        print("\n🔐 Starting browser for manual login...")
        print("📋 Please follow these steps:")
        print("   1. A browser window will open")
        print("   2. Go to https://chat.deepseek.com")
        print("   3. Manually log into your DeepSeek account")
        print("   4. Solve any CAPTCHA if presented")
        print("   5. Once logged in, DO NOT close the browser yet")
        print("   6. Return to this terminal and press ENTER to continue")
        print("   7. The agent will then test if the session is saved")
        print("   8. Close the browser when prompted")
        print("")
        print("💡 Tip: Make sure you're actually logged in (see your chat history)")
        print("")
        
        # Start browser in visible mode for manual login
        await agent.start_browser(headless=False)
        print("✅ Browser started in visible mode")
        
        # Navigate to DeepSeek chat
        print("\n🌐 Navigating to DeepSeek chat...")
        await agent.driver.get("https://chat.deepseek.com")
        print("✅ Navigated to https://chat.deepseek.com")
        
        print("\n⏳ Please complete your login in the browser window...")
        input("   Press ENTER once you've successfully logged into DeepSeek: ")
        
        # Check if session is valid
        print("\n🔍 Checking if session is valid...")
        is_valid = await agent.check_session()
        if is_valid:
            print("✅ SUCCESS: Session is valid and saved!")
            print("💾 Your login session has been saved to:")
            print(f"   {agent.session_dir}")
            print("")
            print("🚀 You can now use the agent in headless mode for automation")
        else:
            print("❌ Session check failed")
            print("💡 Please make sure you're actually logged into https://chat.deepseek.com")
            print("   and try again")
        
        print("\n📝 Next steps:")
        print("   1. Close this browser window when ready")
        print("   2. To use the agent for automation, run:")
        print("      python3 -c \"import asyncio; from core.agents.researcher.nodriver_deepseek_browser_agent import NodriverDeepSeekAgent; agent = NodriverDeepSeekAgent(); asyncio.run(agent.login(headless=True)); print('Session valid:', await agent.check_session())\"")
        print("")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🛑 Closing browser...")
        try:
            await agent.close()
        except:
            pass
        print("✅ Done!")

if __name__ == "__main__":
    asyncio.run(main())
