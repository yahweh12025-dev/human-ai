#!/usr/bin/env python3
"""
Human AI: Researcher Agent (v3.2)
Integrated with DeepSeek Browser Agent, OpenClaw Gateway, Supabase, and Graphify.
"""

import asyncio
import os
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import async_playwright
from supabase import create_client, Client
import random
import traceback

# Load environment variables
load_dotenv()

# Ensure essential directories exist
Path('/home/ubuntu/human-ai/outputs').mkdir(parents=True, exist_ok=True)
Path('/home/ubuntu/human-ai/logs').mkdir(parents=True, exist_ok=True)

class HumanAIResearcher:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase = create_client(self.supabase_url, self.supabase_key) if self.supabase_url else None
        
        # Integration with Browser-First Routing (via DeepSeekBrowserAgent)
        # In a real scenario, this would be a separate class/module
        self.browser_agent = None # Initialized on demand

    async def start_browser(self):
        if not self.browser_agent:
            # Mock initialization for the sake of the example
            self.browser_agent = "DeepSeekBrowserAgent_Active"
            print("🌐 Browser Agent initialized.")

    async def call_llm_via_browser(self, prompt: str) -> str:
        # This simulates the browser routing we implemented earlier
        print(f"🌐 Routing prompt to DeepSeek Browser: {prompt[:50]}...")
        await asyncio.sleep(1)
        return f"Synthesized result for: {prompt[:30]}... [Browser-First Response]"

    async def research(self, topic: str, queries: List[str]) -> List[Dict[str, Any]]:
        findings = []
        await self.start_browser()
        for query in queries:
            print(f"🔍 Researching: {query}")
            result = await self.call_llm_via_browser(query)
            findings.append({'topic': query, 'content': result})
        return findings

    async def synthesize(self, topic: str, final_findings: List[Dict[str, Any]]) -> str:
        # 1. Textual Synthesis
        report = f"# Research Report: {topic}\\n\\n"
        for finding in final_findings:
            report += f"## {finding['topic']}\\n{finding['content']}\\n\\n"
        
        # 2. Visualization Phase (Graphify)
        try:
            from skills.graphify_skill import GraphifySkill
            graphify = GraphifySkill()
            nodes = [{'id': f['topic'], 'label': f['topic']} for f in final_findings]
            edges = []
            # Simple logic to connect all findings to the main topic
            for node in nodes:
                edges.append({'source': topic, 'target': node['id'], 'label': 'explains'})
            
            graph_data = graphify.generate_graph(nodes, edges)
            report += f"\\n\\n## Visual Relationship Graph\\n\\n{graph_data['content']}"
        except Exception as e:
            print(f"Graphify integration failed: {e}")
            
        return report

    async def run(self, topic: str):
        # Simple pipeline: Query -> Research -> Synthesize
        queries = [f"What are the latest trends in {topic}?", f"Key challenges in {topic}"]
        findings = await self.research(topic, queries)
        report = await self.synthesize(topic, findings)
        
        # Save to Supabase
        if self.supabase:
            self.supabase.table('research_findings').insert({'topic': topic, 'content': report}).execute()
            
        print(f"✅ Research complete for {topic}. Report generated.")
        return report

if __name__ == "__main__":
    import asyncio
    asyncio.run(HumanAIResearcher().run("Solid State Batteries"))
