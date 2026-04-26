#!/usr/bin/env python3
"""
Human AI: Researcher Agent (v3.2)
Integrated with DeepSeek Browser Agent, OpenClaw Gateway, Supabase, and Graphify.
"""

import asyncio
import os
import re
import sys
import json
import time
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

# Local import for the browser agent
from .claude_browser_agent import ClaudeBrowserAgent

# Load environment variables
load_dotenv()

# Ensure essential directories exist
Path('/home/yahwehatwork/human-ai/outputs').mkdir(parents=True, exist_ok=True)
Path('/home/yahwehatwork/human-ai/logs').mkdir(parents=True, exist_ok=True)

class HumanAIResearcher:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase = create_client(self.supabase_url, self.supabase_key) if self.supabase_url else None
        
        # Integration with Browser-First Routing (via DeepSeekBrowserAgent)
        self.browser_agent = None # Initialized on demand

    async def start_browser(self):
        if not self.browser_agent:
            # Initialize the real DeepSeekBrowserAgent
            self.browser_agent = ClaudeBrowserAgent()
            await self.browser_agent.start_browser()
            print("🌐 Browser Agent initialized.")
            
    async def call_llm_via_browser(self, prompt: str) -> str:
        # Route prompt to Claude Browser Agent (Botasaurus)
        print(f"🌐 Routing prompt to Claude Browser: {prompt[:50]}...")
        await self.start_browser()
        # Ensure login (uses cookies if available)
        # Since the Botasaurus agent's login is synchronous, we run it in a thread
        loop = asyncio.get_event_loop()
        logged_in = await loop.run_in_executor(None, self.browser_agent.login)
        if not logged_in:
            raise Exception("Claude session invalid. Please manually re-seed the session.")
        # Get the response from the LLM via the browser
        response = await loop.run_in_executor(None, self.browser_agent.prompt, prompt)
        return response

    async def research_with_notebooklm(self, topic: str, documents: List[Path], queries: List[str]) -> List[Dict[str, Any]]:
        """
        Research using NotebookLM for document-grounded insights.
        """
        if not hasattr(self, 'notebook_lm_agent') or not self.notebook_lm_agent:
            print("NotebookLMAgent not available, falling back to regular research")
            return await self.research(topic, queries)
        
        findings = []
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                context = await self.notebook_lm_agent.launch_browser(p)
                
                # Upload all documents
                for doc_path in documents:
                    if doc_path.exists():
                        print(f"Uploading document: {doc_path.name}")
                        await self.notebook_lm_agent.upload_document(context, doc_path)
                    else:
                        print(f"Warning: Document not found: {doc_path}")
                
                # Wait a bit for documents to process
                await asyncio.sleep(5)
                
                # Ask each query
                for query in queries:
                    print(f"Asking NotebookLM: {query}")
                    try:
                        response = await self.notebook_lm_agent.query_notebook(context, query)
                        findings.append({'topic': query, 'content': response, 'source': 'NotebookLM'})
                    except Exception as e:
                        print(f"Error querying NotebookLM: {e}")
                        findings.append({'topic': query, 'content': f"Error: {str(e)}", 'source': 'NotebookLM'})
                
                await context.close()
        except Exception as e:
            print(f"Error in NotebookLM research: {e}")
            # Fallback to regular research
            findings = await self.research(topic, queries)
        
        return findings

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
        report = f"# Research Report: {topic}\n\n"
        for finding in final_findings:
            report += f"## {finding['topic']}\n{finding['content']}\n\n"
        
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
            report += f"\n\n## Visual Relationship Graph\n\n{graph_data['content']}"
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
