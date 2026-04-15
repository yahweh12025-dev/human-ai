#!/usr/bin/env python3
"""
Human AI: Researcher Agent (v3.0)
Integrated with DeepSeek Browser Agent, OpenClaw Gateway, and Supabase.
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
Path('/home/ubuntu/human-ai/session').mkdir(parents=True, exist_ok=True)

# Constants from .env
OPENCLAW_URL = os.getenv("OPENCLAW_URL", "http://localhost:18789")
OPENCLAW_TOKEN = os.getenv("OPENCLAW_TOKEN", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:14b")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
WORK_DIR = os.getenv("WORK_DIR", "/home/ubuntu/human-ai")
DEEPSEEK_EMAIL = os.getenv("DEEPSEEK_EMAIL", "")
DEEPSEEK_PASSWORD = os.getenv("DEEPSEEK_PASSWORD", "")
SESSION_PATH = os.path.join(WORK_DIR, "session", "state.json")

def log_error(agent_name, error_msg, context=''):
    errors_dir = Path('/home/ubuntu/human-ai/errors')
    errors_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    error_file = errors_dir / f'{agent_name}_{ts}.log'
    content = f'Agent: {agent_name}\nTime: {ts}\nError: {error_msg}\nContext: {context}\nTraceback:\n{traceback.format_exc()}'
    error_file.write_text(content)

class NetworkClient:
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5), retry=retry_if_exception_type(requests.RequestException))
    def post(self, url, payload, headers=None, timeout=120):
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()

class DeepSeekBrowserAgent:
    def __init__(self):
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.prompt_count = 0

    async def start_browser(self, login_mode=False):
        self.pw = await async_playwright().start()
        user_data_dir = Path('/home/ubuntu/human-ai/session/browser_profile')
        user_data_dir.mkdir(parents=True, exist_ok=True)
        self.context = await self.pw.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=os.getenv("BROWSER_HEADLESS", "True").lower() == "true",
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--disable-blink-features=AutomationControlled', '--window-size=1280,720'],
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 720},
            locale='en-US', timezone_id='America/New_York',
        )
        if not login_mode:
            await self.context.add_init_script('Object.defineProperty(navigator, "webdriver", {get: () => undefined});')
        self.page = await self.context.new_page()
        self.browser = self.context.browser

    async def _human_type(self, locator, text):
        await locator.click()
        for char in text:
            await locator.type(char, delay=random.randint(50, 150))

    async def login(self, interactive=False):
        await self.start_browser(login_mode=True)
        
        # Try loading cookies from file first
        import sys
        sys.path.append('/home/ubuntu/human-ai')
        from cookie_manager import load_cookies, save_cookies
        cookies = load_cookies()
        if cookies:
            await self.context.add_cookies(cookies)
            await self.page.goto('https://chat.deepseek.com')
            await self.page.wait_for_timeout(2000)
            if 'sign_in' not in self.page.url:
                print("✅ Session restored from cookies!")
                return True

        # Normal login flow...
        await self.page.goto('https://chat.deepseek.com/sign_in', wait_until='networkidle')
        if interactive:
            print("🌟 INTERACTIVE MODE: Please log in in browser...")
            try:
                await self.page.wait_for_url('https://chat.deepseek.com/**', timeout=300000)
                # Save cookies after successful login
                save_cookies(await self.context.cookies())
                return True
            except: return False
        else:
            try:
                email_input = self.page.locator('input.ds-input__input').nth(0)
                await self._human_type(email_input, os.getenv('DEEPSEEK_EMAIL', ''))
                pass_input = self.page.locator('input.ds-input__input').nth(1)
                await self._human_type(pass_input, os.getenv('DEEPSEEK_PASSWORD', ''))
                await pass_input.press('Enter')
                await self.page.wait_for_timeout(8000)
                if 'sign_in' not in self.page.url:
                    save_cookies(await self.context.cookies())
                    return True
                return False
            except: return False

    async def prompt(self, text):
        if not self.page: await self.start_browser()
        await self.page.goto("https://chat.deepseek.com")
        await self.page.wait_for_timeout(2000)
        textbox = self.page.locator('textarea, div[contenteditable=true]').last
        await self._human_type(textbox, text)
        await textbox.press("Enter")
        await self.page.wait_for_function('document.querySelector("textarea") && !document.querySelector("textarea").disabled', timeout=120000)
        await self.page.wait_for_timeout(2000)
        messages = await self.page.query_selector_all('[class*="markdown"]')
        return await messages[-1].inner_text() if messages else "No response"

    async def close(self):
        if self.browser: await self.browser.close()
        if self.pw: await self.pw.stop()

class WebScraper:
    async def scrape(self, url):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                content = await page.inner_text("body")
                return content[:15000]
            except: return "Scraping failed"
            finally: await browser.close()

class HumanAIResearcher:
    def __init__(self):
        self.net = NetworkClient()
        self.scraper = WebScraper()
        self.ds_agent = DeepSeekBrowserAgent()
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

    async def _run_ds_browser(self, prompt):
        if not self.ds_agent.page: await self.ds_agent.start_browser()
        if not os.path.exists(SESSION_PATH): await self.ds_agent.login()
        return await self.ds_agent.prompt(prompt)

    async def _call_llm(self, prompt):
        try:
            return await self._run_ds_browser(prompt)
        except Exception as e: return f"Error: {str(e)}"

    async def research(self, topic):
        print(f"\\n🔍 Deep Researching: {topic}")
        
        if self.supabase:
            try:
                print(f"🔍 Checking Supabase for existing research on '{topic}'...")
                res = self.supabase.table('research_findings')\
                    .select('*')\
                    .ilike('topic', f'%{topic}%')\
                    .order('created_at', desc=True)\
                    .limit(1).execute()
                
                if res.data:
                    print("✅ Found existing research in Supabase! Returning cached result.")
                    return res.data[0]['content']
            except Exception as e:
                print(f"⚠️ Supabase check failed: {e}")

        target_prompt = f"I need to research {topic}. Provide a list of 3-5 high-quality URLs. Return only URLs, one per line."
        targets_text = await self._call_llm(target_prompt)
        urls = re.findall(r'https?://[^\s<>"]+', targets_text)
        
        if not urls:
            print("❌ No target URLs found.")
            return "Could not find relevant sources for research."

        schema_prompt = f"What specific data points should be extracted from a webpage to research {topic}? Return a simple comma-separated list of fields."
        schema_desc = await self._call_llm(schema_prompt)
        print(f"📋 Extraction Schema: {schema_desc}")

        aggregated_data = ""
        parser_path = "/home/ubuntu/.openclaw/workspace/skills/advanced-scraper/scripts/structured_parser.py"
        for url in urls[:3]:
            print(f"🌐 Processing: {url}...")
            raw_html = await self.scraper.scrape(url)
            
            try:
                process = await asyncio.create_subprocess_exec(
                    'python3', parser_path, raw_html, schema_desc,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                parsed_json_str = stdout.decode().strip()
                aggregated_data += f"\\n--- Source: {url} ---\\n{parsed_json_str}\\n"
            except Exception as e:
                print(f"⚠️ Parsing failed for {url}: {e}")
                aggregated_data += f"\\n--- Source: {url} (Raw) ---\\n{raw_html[:2000]}\\n"

        synthesis_prompt = f"Create a detailed technical report on {topic} using the following structured data extracted from multiple sources:\\n{aggregated_data}"
        report = await self._call_llm(synthesis_prompt)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        topic_slug = re.sub(r'[^a-zA-Z0-9]', '_', topic).lower()
        out_dir = os.path.join(WORK_DIR, 'outputs', topic_slug)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f'{timestamp}.md'), 'w') as f: f.write(report)

        if self.supabase:
            try:
                self.supabase.table('research_findings').insert({'topic': topic, 'content': report}).execute()
            except Exception as e: print(f'Supabase error: {e}')

        return report

    async def get_research(self, topic):
        if not self.supabase:
            return "Supabase not configured."
        try:
            res = self.supabase.table('research_findings')\
                .select('*')\
                .ilike('topic', f'%{topic}%')\
                .order('created_at', desc=True)\
                .limit(1).execute()
            return res.data[0]['content'] if res.data else "No research found for this topic."
        except Exception as e:
            return f"Error retrieving research: {str(e)}"

    async def send_gateway_message(self, message: str, priority: str = "info"):
        """Send a message or request back to the OpenClaw Gateway."""
        try:
            payload = {
                "message": message,
                "priority": priority,
                "agent": "HumanAIResearcher",
                "timestamp": datetime.now().isoformat()
            }
            self.net.post(f"{OPENCLAW_URL}/message", payload)
            print(f"📡 Gateway Notification sent: {message}")
        except Exception as e:
            print(f"⚠️ Gateway communication failed: {e}")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()
    agent = HumanAIResearcher()
    if args.interactive:
        await agent.ds_agent.login(interactive=True)
    elif args.login:
        await agent.ds_agent.login(interactive=False)
    else:
        print(await agent._run_ds_browser("Hello world"))

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
