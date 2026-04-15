import asyncio
import json
import os
import re
from typing import Dict, Any
import requests
from dotenv import load_dotenv

load_dotenv()

class ReviewerAgent:
    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "deepseek-r1:14b")
        self.api_url = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/generate"

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
            # Using a thread for the synchronous request
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.post(
                self.api_url,
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=120
            ))
            
            res_data = response.json()
            text = res_data.get('response', '')
            
            # Extract JSON from response
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return {"status": "fail", "comments": "LLM failed to return valid JSON review."}
        except Exception as e:
            print(f"❌ Reviewer Error: {e}")
            return {"status": "fail", "comments": f"Internal error during review: {str(e)}"}
