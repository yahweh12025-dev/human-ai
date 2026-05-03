#!/usr/bin/env python3
import asyncio
import os
import sys
import random
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()
WORK_DIR = os.getenv("WORK_DIR", "/home/yahwehatwork/human-ai")

class WebNavigator:
    def __init__(self):
        self.pw, self.browser, self.context, self.page = None, None, None, None
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    async def start(self):
        self.pw = await async_playwright().start()
        user_data_dir = os.path.join(WORK_DIR, "session", "navigator_profile")
        os.makedirs(user_data_dir, exist_ok=True)
        self.context = await self.pw.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=os.getenv("BROWSER_HEADLESS", "True").lower() == "true",
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--disable-blink-features=AutomationControlled', '--window-size=1280,720'],
            user_agent=self.user_agent, viewport={'width': 1280, 'height': 720},
            locale='en-US', timezone_id='America/New_York',
        )
        self.page = await self.context.new_page()
        self.browser = self.context.browser

    async def navigate_to(self, url: str):
        await self.page.goto(url, wait_until="networkidle")
        await self.page.wait_for_timeout(2000)

    async def click(self, selector: str):
        await self.page.click(selector)
        await self.page.wait_for_load_state("networkidle")

    async def fill(self, selector: str, text: str):
        await self.page.fill(selector, text)
        await self.page.wait_for_timeout(500)

    async def press_key(self, selector: str, key: str):
        await self.page.focus(selector)
        await self.page.keyboard.press(key)
        await self.page.wait_for_load_state("networkidle")

    async def scroll_to(self, selector: str):
        await self.page.locator(selector).scroll_into_view_if_needed()

    async def get_accessibility_tree(self) -> str:
        js_script = """
        () => { 
            const interactive = [];
            const selectors = 'button, a, input, select, textarea, [role="button"], [role="link"], [onclick]';
            document.querySelectorAll(selectors).forEach((el, i) => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    interactive.push({
                        id: i,
                        tag: el.tagName,
                        text: (el.innerText || el.placeholder || el.value || 'No text').trim().substring(0, 50),
                        role: el.getAttribute('role') || 'none',
                        ariaLabel: el.getAttribute('aria-label') || '',
                        selector: el.id ? `#${el.id}` : `[${el.tagName.toLowerCase()}]:nth-child(${Array.from(el.parentNode.children).indexOf(el)+1})`
                    });
                }
            });
            return interactive;
        }
        """
        try: 
            res = await self.page.evaluate(js_script)
            return json.dumps(res, indent=2)
        except Exception as e: 
            return f"Error: {str(e)}"


    async def get_visible_text(self) -> str:
        return await self.page.evaluate("document.body.innerText")

    async def close(self):
        if self.context: await self.context.close()
        if self.pw: await self.pw.stop()

class NavigatorAgent:
    def __init__(self):
        self.navigator = WebNavigator()
        from .navigator_skills import NavigatorSkills
        self.skills = NavigatorSkills(self.navigator)
        from core.agents.hybrid_llm_router import HybridLLMRouter
        self.router = HybridLLMRouter()

    async def run_goal_oriented_loop(self, goal: str, max_steps: int = 10):
        print(f"🎯 GOAL: {goal}")
        log_file = Path(WORK_DIR) / "logs" / "navigator_loop.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        await self.navigator.start()
        try:
            for step in range(max_steps):
                print(f"--- Loop Iteration {step+1}/{max_steps} ---")
                tree = await self.navigator.get_accessibility_tree()
                content = await self.navigator.get_visible_text()
                print("🤔 Thinking (Hybrid-Brain)...")
                
                action_decided = await self._get_llm_decision(goal, tree, content)
                
                if action_decided["type"] == "complete":
                    return {"status": "success", "reason": action_decided["reason"]}
                if action_decided["type"] == "error":
                    raise Exception(action_decided["reason"])
                print(f"🚀 Executing: {action_decided['action']} ({action_decided['details']})")
                await self._execute_action(action_decided)
            return {"status": "timeout", "reason": "Max steps reached."}
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {"status": "error", "error": str(e)}
        finally:
            await self.navigator.close()

    async def _get_llm_decision(self, goal, tree, content):
        prompt = f"GOAL: {goal}\\n\\nPAGE TEXT:\\n{content[:2000]}\\n\\nSEMANTIC MAP:\\n{tree}\\n\\nYou MUST respond with ONLY a valid JSON object. No conversation, no preamble. Format: {{\"type\": \"navigate\"|\"click\"|\"fill\"|\"press\"|\"scroll\"|\"complete\"|\"error\", \"action\": \"name\", \"details\": \"selector/url\", \"value\": \"text\", \"key\": \"key\", \"reason\": \"why\"}}"
        
        try:
            # CORRECT ASYNC CALL to the HybridLLMRouter
            result = await self.router.route_task(prompt)
            
            # The router returns a dictionary: {"status": "success", "response": "...", ...}
            if isinstance(result, dict) and result.get("status") == "success":
                decision_str = result.get("response", "")
            else:
                decision_str = str(result)
                
            match = re.search(r'\{.*\}', decision_str, re.DOTALL)
            if match:
                return json.loads(match.group())
            else:
                print(f"⚠️ LLM returned non-JSON: {decision_str[:100]}...")
        except Exception as e:
            print(f"⚠️ LLM Router failure: {e}")
            
        return {"type": "error", "reason": "LLM failed to provide a valid JSON action."}

    async def _execute_action(self, action_obj):
        action = action_obj["action"]
        if action == "navigate": await self.navigator.navigate_to(action_obj["details"])
        elif action == "click": await self.navigator.click(action_obj["details"])
        elif action == "fill": await self.navigator.fill(action_obj["details"], action_obj["value"])
        elif action == "press": await self.navigator.press_key(action_obj["details"], action_obj["key"])
        elif action == "scroll": await self.navigator.scroll_to(action_obj["details"])

async def main():
    agent = NavigatorAgent()
    await agent.run_goal_oriented_loop("Search for OpenClaw on Google")

if __name__ == "__main__":
    asyncio.run(main())
