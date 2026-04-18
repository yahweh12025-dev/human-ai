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

# Load environment variables
load_dotenv()

# Ensure essential directories exist
Path('/home/ubuntu/human-ai/outputs').mkdir(parents=True, exist_ok=True)
Path('/home/ubuntu/human-ai/logs').mkdir(parents=True, exist_ok=True)

class DeepSeekBrowserAgent:
    """Browser-based agent for interacting with DeepSeek chat via Playwright."""
    
    def __init__(self):
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        self.session_dir = os.path.join(os.getenv('WORK_DIR', '/home/ubuntu/human-ai'), 'session', 'browser_profile')
        self.is_initialized = False
        
    async def start_browser(self):
        """Initialize Playwright browser with persistent context."""
        if self.is_initialized:
            return
            
        print("🌐 Initializing DeepSeek Browser Agent...")
        self.pw = await async_playwright().start()
        
        # Ensure session directory exists
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Launch persistent context
        self.context = await self.pw.chromium.launch_persistent_context(
            user_data_dir=self.session_dir,
            headless=os.getenv("BROWSER_HEADLESS", "True").lower() == "true",
            args=[
                '--no-sandbox', 
                '--disable-dev-shm-usage', 
                '--disable-gpu', 
                '--disable-blink-features=AutomationControlled',
                '--window-size=1280,720'
            ],
            user_agent=self.user_agent,
            viewport={'width': 1280, 'height': 720},
            locale='en-US',
            timezone_id='America/New_York',
        )
        
        # Get the first page (or create new)
        pages = self.context.pages
        if pages:
            self.page = pages[0]
        else:
            self.page = await self.context.new_page()
            
        self.is_initialized = True
        print("✅ DeepSeek Browser Agent initialized")
        
    async def login(self):
        """Ensure we are logged into DeepSeek. Uses persistent session."""
        await self.start_browser()
        
        print("🔐 Checking DeepSeek login status...")
        await self.page.goto("https://chat.deepseek.com", wait_until="networkidle")
        await self.page.wait_for_timeout(3000)
        
        # Check if we're already logged in by looking for chat input
        try:
            # Wait for the chat input textarea to appear (indicates logged in)
            await self.page.wait_for_selector('textarea[placeholder*="Message"], textarea, [role="textbox"]', timeout=10000)
            print("✅ Already logged into DeepSeek (session restored)")
            return True
        except:
            print("⚠️ Not logged in, attempting login...")
            # If we need to implement actual login logic, we would do it here.
            # For now, rely on saved session in user_data_dir.
            # If login fails, we'll throw an error on prompt.
            return False
            
    async def prompt(self, prompt_text: str) -> str:
        """Send a prompt to DeepSeek and return the response."""
        if not self.is_initialized:
            await self.start_browser()
            
        # Ensure we're on the chat page
        await self.page.goto("https://chat.deepseek.com", wait_until="networkidle")
        await self.page.wait_for_timeout(2000)
        
        # Find the input textarea
        try:
            input_selector = 'textarea[placeholder*="Message"], textarea, [role="textbox"]'
            await self.page.wait_for_selector(input_selector, timeout=10000)
            
            # Clear and fill the input
            await self.page.fill(input_selector, "")
            await self.page.fill(input_selector, prompt_text)
            
            # Submit by pressing Enter
            await self.page.keyboard.press("Enter")
            
            # Wait for response to start generating
            await self.page.wait_for_timeout(3000)
            
            # Wait for the response to complete (we'll wait for a new message to appear and stop changing)
            # Simple approach: wait a fixed time then get last message
            await self.page.wait_for_timeout(15000)  # Wait for response generation
            
            # Get all message elements and take the last one
            # Adjust selector based on DeepSeek's actual DOM
            message_selector = '.message, [data-message-role="assistant"], .chat-message, .assistant-message'
            try:
                await self.page.wait_for_selector(message_selector, timeout=5000)
                messages = await self.page.locator(message_selector).all()
                if messages:
                    last_message = messages[-1]
                    text = await last_message.inner_text()
                    # Clean up potential extra whitespace
                    return text.strip()
            except:
                pass
                
            # Fallback: get all page text and try to extract
            page_content = await self.page.evaluate("() => document.body.innerText")
            # Simple extraction: look for lines after our prompt (not robust)
            return page_content.strip()
            
        except Exception as e:
            print(f"❌ Error during DeepSeek prompt: {e}")
            raise e
            
    async def close(self):
        """Close browser resources."""
        if self.context:
            await self.context.close()
        if self.pw:
            await self.pw.stop()
        self.is_initialized = False
        print("🌐 DeepSeek Browser Agent closed")

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
            # Initialize the real DeepSeekBrowserAgent
            self.browser_agent = DeepSeekBrowserAgent()
            await self.browser_agent.start_browser()
            print("🌐 Browser Agent initialized.")

    async def call_llm_via_browser(self, prompt: str) -> str:
        # Route prompt to DeepSeek Browser Agent
        print(f"🌐 Routing prompt to DeepSeek Browser: {prompt[:50]}...")
        await self.start_browser()
        # Ensure login (uses cookies if available)
        session_path = os.path.join(os.getenv('WORK_DIR', '/home/ubuntu/human-ai'), 'session', 'browser_profile')
        # We'll rely on the agent's login method which checks session
        await self.browser_agent.login()
        
        # Get the response from the LLM via the browser
        response = await self.browser_agent.prompt(prompt)
        return response

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
