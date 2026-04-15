#!/usr/bin/env python3
"""
Human AI: Navigator Agent (v1.6)
Specialized in multi-step, goal-oriented web navigation using Playwright.
"""

import asyncio
import os
import sys
import random
import traceback
from .navigator_skills import NavigatorSkills
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

WORK_DIR = os.getenv("WORK_DIR", "/home/ubuntu/human-ai")
MODEL_OVERRIDE = "openrouter/auto"

# Import the new Freeride manager
try:
    from freeride_manager import manager
except ImportError:
    print("⚠️ Warning: freeride_manager.py not found. Falling back to standard logic.")
    class MockManager:
        MODEL_QUEUE = [MODEL_OVERRIDE]
        def get_current(self): return MODEL_OVERRIDE, os.getenv("OPENROUTER_API_KEY")
        def get_next_fallback(self): return MODEL_OVERRIDE, os.getenv("OPENROUTER_API_KEY")
    manager = MockManager()

class WebNavigator:
    def __init__(self):
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'

    async def start(self):
        self.pw = await async_playwright().start()
        user_data_dir = os.path.join(WORK_DIR, "session", "navigator_profile")
        os.makedirs(user_data_dir, exist_ok=True)
        
        self.context = await self.pw.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=os.getenv("BROWSER_HEADLESS", "True").lower() == "true",
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--disable-blink-features=AutomationControlled', '--window-size=1280,720'],
            user_agent=self.user_agent,
            viewport={'width': 1280, 'height': 720},
            locale='en-US', timezone_id='America/New_York',
        )
        self.page = await self.context.new_page()
        self.browser = self.context.browser
        print("✅ Navigator Browser Started.")

    async def navigate_to(self, url: str):
        print(f"🌐 Navigating to: {url}")
        await self.page.goto(url, wait_until="networkidle")
        await self.page.wait_for_timeout(2000)

    async def click(self, selector: str):
        print(f"🖱️ Clicking: {selector}")
        await self.page.click(selector)
        await self.page.wait_for_load_state("networkidle")

    async def fill(self, selector: str, text: str):
        print(f"⌨️ Filling: {selector} with '{text}'")
        await self.page.fill(selector, text)
        await self.page.wait_for_timeout(500)

    async def press_key(self, selector: str, key: str):
        print(f"⌨️ Pressing '{key}' on: {selector}")
        await self.page.focus(selector)
        await self.page.keyboard.press(key)
        await self.page.wait_for_load_state("networkidle")

    async def scroll_to(self, selector: str):
        print(f"📜 Scrolling to: {selector}")
        await self.page.locator(selector).scroll_into_view_if_needed()

    async def get_accessibility_tree(self) -> str:
        """Returns a simplified semantic representation of the page via JS injection."""
        print("🔍 Extracting Semantic Map...")
        js_script = """
        () => {
            const elements = document.querySelectorAll('button, a, input, select, textarea, [role="button"], [role="link"]');
            return Array.from(elements).map(el => {
                return {
                    tag: el.tagName,
                    text: el.innerText || el.placeholder || el.value || 'No text',
                    role: el.getAttribute('role') || 'none',
                    id: el.id,
                    className: el.className,
                    ariaLabel: el.getAttribute('aria-label') || ''
                };
            });
        }
        """
        try:
            tree = await self.page.evaluate(js_script)
            return json.dumps(tree, indent=2)
        except Exception as e:
            return f"Error extracting semantic map: {str(e)}"

    async def get_visible_text(self) -> str:
        return await self.page.evaluate("document.body.innerText")

    async def get_screenshot_base64(self) -> str:
        """Returns base64 encoded screenshot for vision-based reasoning."""
        return await self.page.screenshot(type="jpeg", quality=50, encoding="base64")

    async def navigate_to_openclaw(self):
        """Navigate to OpenClaw's documentation section using Playwright"""
        await self.browser.open("https://openclaw.ai/docs")
        await self.browser.fill("search-input", "Playwright integration")
        await self.browser.click("search-button")

    async def extract_navigator_skill_content(self):
        """Extract visible content using supernatural mode"""
        return await self.browser.get_visible_text()

    async def close(self):
        if self.context: await self.context.close()
        if self.pw: await self.pw.stop()


class NavigatorAgent:
    def __init__(self):
        self.navigator = WebNavigator()
        self.skills = NavigatorSkills(self.navigator)
        self.history = []

    async def run_goal_oriented_loop(self, goal: str, max_steps: int = 10):
        """
        An autonomous loop that uses reasoning to achieve a high-level goal.
        """
        print(f"\\n🎯 GOAL: {goal}")
        log_file = Path(WORK_DIR) / "logs" / "navigator_loop.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        await self.navigator.start()
        
        history = []
        
        try:
            for step in range(max_steps):
                log_entry = f"\\n--- Loop Iteration {step+1}/{max_steps} ---\\n"
                print(log_entry)
                with open(log_file, "a") as f: f.write(log_entry)
                
                # 1. OBSERVE
                tree = await self.navigator.get_accessibility_tree()
                content = await self.navigator.get_visible_text()
                
                # 2. THINK
                print("🤔 Thinking about next action...")
                # Add a random sleep to mitigate rate limits
                await asyncio.sleep(random.uniform(2, 5))
                
                action_decided = await self._get_llm_decision(goal, tree, content)
                
                if action_decided["type"] == "complete":
                    res = f"✅ Goal achieved: {action_decided['reason']}"
                    print(res)
                    with open(log_file, "a") as f: f.write(res + "\\n")
                    return {"status": "success", "reason": action_decided["reason"]}
                
                if action_decided["type"] == "error":
                    err = f"❌ Loop Error: {action_decided['reason']}"
                    print(err)
                    with open(log_file, "a") as f: f.write(err + "\\n")
                    raise Exception(action_decided["reason"])

                act_msg = f"🚀 Executing: {action_decided['action']} ({action_decided['details']})"
                print(act_msg)
                with open(log_file, "a") as f: f.write(act_msg + "\\n")
                await self._execute_action(action_decided)
                
                history.append({
                    "step": step,
                    "action": action_decided["action"],
                    "observation": content[:200]
                })

            return {"status": "timeout", "reason": "Max steps reached without achieving goal."}

        except Exception as e:
            print(f"❌ Loop Error: {str(e)}")
            return {"status": "error", "error": str(e)}
        finally:
            await self.navigator.close()

    async def _get_llm_decision(self, goal, tree, content):
        """Calls the LLM to decide the next interaction based on page state."""
        prompt = (
            f"GOAL: {goal}\n\n"
            f"CURRENT PAGE TEXT:\n{content[:2000]}\n\n"
            f"SEMANTIC MAP (Accessibility Tree):\n{tree}\n\n"
            f"Based on the above, what is the next single action to take to reach the goal?\n"
            f"You MUST respond ONLY with a raw JSON object. No conversational filler, no markdown blocks, no explanation outside the JSON.\n"
            f"JSON Format:\n"
            f"{{\n"
            f"  \"type\": \"navigate\" | \"click\" | \"fill\" | \"press\" | \"scroll\" | \"complete\" | \"error\",\n"
            f"  \"action\": \"the action name\",\n"
            f"  \"details\": \"the selector or URL\",\n"
            f"  \"value\": \"text to fill (if applicable)\",\n"
            f"  \"key\": \"key to press (if applicable)\",\n"
            f"  \"reason\": \"explanation of why this action was chosen\"\n"
            f"}}"
        )
        
        for attempt in range(len(manager.MODEL_QUEUE)):
            model, api_key = manager.get_current()
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}", 
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:18789",
                    "X-Title": "OpenClaw Navigator"
                }
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}]
                }
                
                # Using requests in a thread to avoid blocking the event loop
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, lambda: requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=60
                ))
                
                if response.status_code == 429:
                    print(f"⚠️ Rate limit hit on {model}. Rotating...")
                    manager.get_next_fallback()
                    continue
                
                response.raise_for_status()
                res_data = response.json()
                response_text = res_data['choices'][0]['message']['content']
                
                match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group())
                    except json.JSONDecodeError:
                        # Fallback: try cleaning common LLM artifacts if direct load fails
                        cleaned = match.group().strip().strip('`').strip('json').strip()
                        return json.loads(cleaned)
                return {"type": "error", "reason": f"LLM did not return valid JSON structure. Raw response: {response_text[:100]}..."}
            except (json.JSONDecodeError, Exception) as e:
                print(f"⚠️ JSON Parsing failed: {e}")
                return {"type": "error", "reason": f"JSON parsing error: {str(e)}"}
        
        return {"type": "error", "reason": "All models/keys exhausted or failed."}

    async def _execute_action(self, action_obj):
        action = action_obj["action"]
        if action == "navigate":
            await self.navigator.navigate_to(action_obj["details"])
        elif action == "click":
            await self.navigator.click(action_obj["details"])
        elif action == "fill":
            await self.navigator.fill(action_obj["details"], action_obj["value"])
        elif action == "press":
            await self.navigator.press_key(action_obj["details"], action_obj["key"])
        elif action == "scroll":
            await self.navigator.scroll_to(action_obj["details"])
        elif action == "login":
            # Expects action_obj["details"] to be the URL and "value" to be a JSON string of credentials
            import json
            creds = json.loads(action_obj["value"])
            await self.skills.perform_login(action_obj["details"], creds)

async def main():
    agent = NavigatorAgent()
    print("--- TEST: Autonomous Navigation ---")
    await agent.run_goal_oriented_loop("Search for OpenClaw on Google")

if __name__ == "__main__":
    asyncio.run(main())
