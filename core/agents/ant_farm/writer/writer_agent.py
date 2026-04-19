#!/usr/bin/env python3
"""
Human AI: Ant Farm - Writer Agent
The 'Creative Engine' of the Squad.
Generates high-fidelity initial drafts based on task descriptions.
"""

import asyncio
import logging
import os
import random
from typing import Dict, Any

# Import the OmniChannelRouter to ensure high-quality generation via multiple models
try:
    from omnichannel_router import OmniChannelRouter
except ImportError:
    print("⚠️ Warning: omnichannel_router.py not found. Falling back to local LLM logic.")
    class OmniChannelRouter:
        def __init__(self):
            self.MODEL_QUEUE = []
        async def call_llm(self, prompt: str):
            return f"Mock Draft based on: {prompt[:50]}..."
    router = OmniChannelRouter()
else:
    router = OmniChannelRouter()

class WriterAgent:
    def __init__(self):
        self.logger = logging.getLogger("AntFarm.Writer")
        logging.basicConfig(level=logging.INFO)
        print("✍️ Writer Agent Initialized.")

    async def draft(self, task: Dict[str, Any]) -> str:
        """
        Generates a high-fidelity draft for a given task.
        """
        description = task.get("description", "No task description provided.")
        print(f"✍️ Writing draft for: {description}")

        prompt = (
            f"You are the Writer Agent in an advanced AI Research Squad. "
            f"Your goal is to create a highly detailed, professional, and structured initial draft "
            f"based on the following task description.\n\n"
            f"TASK DESCRIPTION:\n{description}\n\n"
            f"Please provide a comprehensive Markdown document. Include sections like:\n"
            f"- Executive Summary\n"
            f"- Detailed Analysis/Implementation Details\n"
            f"- Technical Specifications\n"
            f"- Next Steps/Recommendations\n\n"
            f"Ensure the tone is professional and the content is actionable."
        )

        try:
            # Use the OmniChannelRouter to leverage the best available LLM
            draft = await router.call_llm(prompt)
            print("✅ Draft generated successfully.")
            return draft
        except Exception as e:
            print(f"❌ Failed to generate draft: {e}")
            return f"Error generating draft: {str(e)}"

async def main():
    agent = WriterAgent()
    test_task = {"description": "A technical report on the future of solid-state batteries in electric vehicles."}
    result = await agent.draft(test_task)
    print("\n--- GENERATED DRAFT ---\n")
    print(result)
    print("\n-----------------------\n")

if __name__ == "__main__":
    asyncio.run(main())
