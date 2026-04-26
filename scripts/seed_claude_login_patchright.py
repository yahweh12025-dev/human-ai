#!/usr/bin/env python3
"""
Seeding script for Claude.ai login using Google account (Patchright version).
This script launches a visible browser with your Google profile and
Cloudflare bypass, allowing you to manually log into Claude.ai.
After logging in, close the browser to save the session.
"""

import asyncio
import os
import sys

# Add the project root to the path so we can import the agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agents.researcher.claude_browser_agent import ClaudeBrowserAgent

async def main():
    print("🌐 Starting Claude Browser Agent for manual seeding (Patchright)...")
    print("📝 Please log into Claude.ai using your Google account.")
    print("🛑 After successful login, CLOSE THE BROWSER WINDOW to finish.")
    print("")
    
    agent = ClaudeBrowserAgent()
    try:
        # Start browser in headed mode for manual interaction
        os.environ["BROWSER_HEADLESS"] = "false"
        await agent.start_browser()
        
        print("✅ Browser started. Waiting for you to log in and close the window...")
        # Keep the script running while the browser is open
        # We'll check if the context still has pages
        while agent.context and len(agent.context.pages) > 0:
            await asyncio.sleep(1)
        
        print("✅ Browser closed. Session saved in your Google profile.")
        print("🔐 You can now run the researcher agent in headless mode.")
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await agent.close()
        print("🌐 Browser agent cleaned up.")

if __name__ == "__main__":
    asyncio.run(main())