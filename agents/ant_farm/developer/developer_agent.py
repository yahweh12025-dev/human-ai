import asyncio
import os
from typing import Dict, Any
import requests
from dotenv import load_dotenv

load_dotenv()

class DeveloperAgent:
    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "deepseek-r1:14b")
        self.api_url = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/generate"

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
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.post(
                self.api_url,
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=120
            ))
            return response.json().get('response', "Implementation failed.")
        except Exception as e:
            print(f"❌ Developer Error: {e}")
            return f"Error during implementation: {str(e)}"
