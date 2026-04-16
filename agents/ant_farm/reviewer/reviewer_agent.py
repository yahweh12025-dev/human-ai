import asyncio
import json
import os
import re
from typing import Dict, Any
from dotenv import load_dotenv

# Import the shared browser agent
import sys
sys.path.append('/home/ubuntu/human-ai')
from agents.researcher.researcher_agent import DeepSeekBrowserAgent

load_dotenv('/home/ubuntu/human-ai/.env')

class ReviewerAgent:
    def __init__(self):
        # We no longer need the direct model/api_url
        self.browser_agent = None

    async def review(self, content: str) -> Dict[str, Any]:
        """
        Analyzes the provided content for technical accuracy, completeness, and style.
        Returns a JSON result: {"status": "pass"|"fail", "comments": "...", "suggestions": []}
        """
        print("🔍 Reviewer is analyzing the content...")
        
        prompt = (
            f"You are a Senior Technical Reviewer. Review the following technical content for accuracy, "
            f"clarity, and completeness. If it is high quality, return 'pass'. If it needs work, return 'fail'.\n\n"
            f"CONTENT:\n{content}\n\n"
            f"Respond ONLY in JSON format:\n"
            f"{{\n"
            f"  \"status\": \"pass\" | \"fail\",\n"
            f"  \"comments\": \"Your detailed feedback\",\n"
            f"  \"suggestions\": [\"suggestion 1\", \"suggestion 2\"]\n"
            f"}}"
        )

        try:
            self.browser_agent = DeepSeekBrowserAgent()
            await self.browser_agent.start_browser()
            
            # Ensure login (uses cookies if available)
            session_path = os.getenv("SESSION_PATH", "/home/ubuntu/human-ai/session/state.json")
            if not os.path.exists(session_path):
                await self.browser_agent.login()
            
            # Get the response from the LLM via the browser
            text = await self.browser_agent.prompt(prompt)
            
            # Extract JSON from response
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return {"status": "fail", "comments": "LLM failed to return valid JSON review."}
        except Exception as e:
            print(f"❌ Reviewer Error: {e}")
            return {"status": "fail", "comments": f"Internal error during review: {str(e)}"}
        finally:
            if self.browser_agent:
                await self.browser_agent.close()
