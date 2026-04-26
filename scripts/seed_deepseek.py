#!/usr/bin/env python3
"""
Manual seeding script for DeepSeek session.
Run with: BROWSER_HEADLESS=false xvfb-run -a python3 seed_deepseek.py
"""
import asyncio
import os
from core.agents.researcher.deepseek_browser_agent import DeepSeekBrowserAgent

async def main():
    agent = DeepSeekBrowserAgent()
    try:
        await agent.start_browser()
        print("🌐 DeepSeek browser opened in headed mode (via XVFB).")
        print("🔐 Please manually log into https://chat.deepseek.com")
        print("   Solve any CAPTCHA if presented.")
        print("   After logging in, the script will detect success and close.")
        print("   If you need to abort, press Ctrl+C.")
        
        # Wait for login by periodically checking session
        while True:
            await asyncio.sleep(5)
            if await agent.check_session():
                print("✅ DeepSeek session seeded successfully!")
                break
            else:
                print("⏳ Waiting for login... (checking again in 5 seconds)")
    except KeyboardInterrupt:
        print("\n🛑 Seeding aborted by user.")
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
