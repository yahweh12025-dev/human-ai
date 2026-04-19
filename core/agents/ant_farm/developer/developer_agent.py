import asyncio
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Import the shared browser agent
import sys
sys.path.append('/home/ubuntu/human-ai')
from agents.researcher.researcher_agent import DeepSeekBrowserAgent

load_dotenv('/home/ubuntu/human-ai/.env')

class DeveloperAgent:
    def __init__(self):
        self.browser_agent = None

    async def implement(self, draft: str) -> str:
        """
        Takes an approved draft and transforms it into a final, polished implementation.
        """
        print("💻 Developer is polishing the final deliverable...")
        
        prompt = (
            f"You are a Lead Software Engineer. Take the following approved technical draft "
            f"and turn it into a professional, production-ready document/implementation. "
            f"Ensure perfect formatting, clear headings, and technical precision.\n\n"
            f"DRAFT:\n{draft}"
        )

        try:
            self.browser_agent = DeepSeekBrowserAgent()
            await self.browser_agent.start_browser()
            
            # Ensure login (uses cookies if available)
            session_path = os.getenv("SESSION_PATH", "/home/ubuntu/human-ai/session/state.json")
            if not os.path.exists(session_path):
                await self.browser_agent.login()
            
            # Get the response from the LLM via the browser
            result = await self.browser_agent.prompt(prompt)
            return result
        except Exception as e:
            print(f"❌ Developer Error: {e}")
            return f"Error during implementation: {str(e)}"
        finally:
            if self.browser_agent:
                await self.browser_agent.close()
