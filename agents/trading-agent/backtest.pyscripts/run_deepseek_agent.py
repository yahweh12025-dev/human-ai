#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.expanduser("~/human-ai"))
from core.agents.researcher.deepseek_browser_agent import DeepSeekBrowserAgent

PROMPT = """Analyze the current market conditions for BTC/USDT and provide:
1. Key support and resistance levels
2. Current trend direction
3. Volume analysis
4. Recommended trading strategy
5. Risk management suggestions"""

async def main():
    agent = DeepSeekBrowserAgent()
    try:
        await agent.start_browser()
        logged_in = await agent.login()
        if not logged_in:
            print("Need to seed DeepSeek session first - opening browser for manual login...")
            print("Please log in to DeepSeek in the browser window, then press Enter here.")
            input()
            logged_in = await agent.check_session()
            if not logged_in:
                print("Session still invalid. Aborting.")
                return
        print("Sending prompt to DeepSeek...")
        response = await agent.prompt(PROMPT)
        print("\n" + "="*60)
        print("DEEPSEEK RESPONSE:")
        print("="*60)
        print(response)
        print("="*60)
        timestamp = __import__('time').strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.expanduser("~/human-ai/research")
        os.makedirs(output_dir, exist_ok=True)
        output_file = f"{output_dir}/deepseek_market_analysis_{timestamp}.txt"
        with open(output_file, "w") as f:
            f.write("DeepSeek Market Analysis - BTC/USDT\n")
            f.write("="*40 + "\n\n")
            f.write(f"Prompt:\n{PROMPT}\n\n")
            f.write(f"Response:\n{response}\n")
        print(f"\nSaved to: {output_file}")
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
