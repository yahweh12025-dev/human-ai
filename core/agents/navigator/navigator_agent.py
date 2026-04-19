#!/usr/bin/env python3
import asyncio
import os
import sys
import random
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()
WORK_DIR = os.getenv("WORK_DIR", "/home/ubuntu/human-ai")

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
        js_script = "() => { const elements = document.querySelectorAll('button, a, input, select, textarea, [role=\"button\"], [role=\"link\"]'); return Array.from(elements).map(el => { return { tag: el.tagName, text: el.innerText || el.placeholder || el.value || 'No text', role: el.getAttribute('role') || 'none', id: el.id, className: el.className, ariaLabel: el.getAttribute('aria-label') || '' }; }); }"
        try: return json.dumps(await self.page.evaluate(js_script), indent=2)
        except Exception as e: return f"Error: {str(e)}"

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
        # AdaptiveRouter is kept for goal classification, but the execution path is now unified to Browser.
        from utils.adaptive_router import AdaptiveRouter
        self.router = AdaptiveRouter()

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
                print("🤔 Thinking (Browser-First)...")
                
                # STRICT BROWSER-FIRST ROUTING:
                # We bypass all direct API calls and use the browser-based LLM interface.
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
        prompt = f"GOAL: {goal}\\n\\nPAGE TEXT:\\n{content[:2000]}\\n\\nSEMANTIC MAP:\\n{tree}\\n\\nRespond with a JSON object: {{\"type\": \"navigate\"|\"click\"|\"fill\"|\"press\"|\"scroll\"|\"complete\"|\"error\", \"action\": \"name\", \"details\": \"selector/url\", \"value\": \"text\", \"key\": \"key\", \"reason\": \"why\"}}"
        
        # STRICT BROWSER ROUTING: No more requests.post to OpenRouter.
        try:
            browser_res = await self.skills.query_llm_via_browser(prompt)
            match = re.search(r'\{.*\}', browser_res, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            print(f"⚠️ Browser-LLM failure: {e}")
            
        return {"type": "error", "reason": "Browser-based LLM decision failed."}

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

# --- START OF AUTONOMOUSLY ADDED NAVIGATOR ENGINE ---
# Based on the design finalized in /home/ubuntu/human-ai/research/navigator/playwright_patterns.md
# This implementation provides the core State-Machine and Action-Observation Loop.

import json
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from playwright.async_api import Page, BrowserContext

# Import the hybrid LLM router for all reasoning and evaluation steps
# Note: The import path is relative to the project root when PYTHONPATH is set correctly.
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from core.utils.hybrid_llm_router import HybridLLMRouter

@dataclass
class NavigatorState:
    """Holds the state of the navigation process."""
    current_url: str = ""
    goal: str = ""
    history: List[Dict[str, Any]] = field(default_factory=list)
    browser_context: Optional[BrowserContext] = None
    page: Optional[Page] = None
    step_count: int = 0
    max_steps: int = 15
    goal_met: bool = False

class NavigatorEngine:
    """Encapsulates the Action-Observation Loop for autonomous web navigation."""
    
    def __init__(self):
        self.router = HybridLLMRouter()
        self.action_library = {
            "navigate_to": self._navigate_to,
            "click_selector": self._click_selector,
            "type_text": self._type_text,
            "extract_text": self._extract_text,
            "wait_for_selector": self._wait_for_selector,
            "go_back": self._go_back,
            "refresh": self._refresh,
        }

    async def run(self, goal: str, browser_context: BrowserContext) -> Dict[str, Any]:
        """
        Main public method to execute the navigation task.
        Returns a dictionary with the result status and data.
        """
        state = self._initialize_state(goal, browser_context)
        
        while not state.goal_met and state.step_count < state.max_steps:
            state = await self._action_observation_loop(state)
        
        return self._finalize_result(state)

    def _initialize_state(self, goal: str, browser_context: BrowserContext) -> NavigatorState:
        """Sets up the initial state for the navigation task."""
        # Start on a blank page or a known search engine? For now, we start fresh.
        page = await browser_context.new_page()
        # A reasonable default start is a search engine.
        await page.goto("https://www.google.com")
        
        return NavigatorState(
            goal=goal,
            browser_context=browser_context,
            page=page,
            current_url=page.url
        )

    async def _action_observation_loop(self, state: NavigatorState) -> NavigatorState:
        """Executes one full cycle of Observe -> Plan -> Act -> Evaluate."""
        
        # --- 1. OBSERVE ---
        observation = await self._get_observation(state.page)
        
        # Log the observation to history before planning
        state.history.append({
            "step": state.step_count,
            "type": "observation",
            "content": observation,
            "url": state.current_url
        })
        
        # --- 2. PLAN (LLM as the Brain) ---
        action_json = await self._plan_next_action(state.goal, state.history)
        
        # --- 3. ACT (Execute with Playwright) ---
        state = await self._execute_action(state, action_json)
        
        # --- 4. EVALUATE (LLM as the Judge) ---
        state.goal_met = await self._evaluate_goal(state.goal, state.history)
        
        return state

    async def _get_observation(self, page: Page) -> str:
        """Creates a concise, text-based summary of the current page state for the LLM."""
        try:
            # Get a summary of the visible text and key interactive elements
            # This is a simplified observation; a more advanced version would use
            # accessibility trees or screenshot analysis.
            title = await page.title()
            url = page.url
            
            # Get text content of common interactive elements to understand the page's purpose
            input_placeholders = await page.eval_on_selector_all(
                "input, textarea", 
                "elements => elements.map(el => el.placeholder || el.ariaLabel || '').filter(p => p.length > 0)"
            )
            button_texts = await page.eval_on_selector_all(
                "button, [role='button']", 
                "elements => elements.map(el => el.textContent || el.ariaLabel || '').filter(t => t.length > 0)"
            )
            
            obs_parts = [
                f"Page Title: '{title}'",
                f"Current URL: {url}",
                f"Visible Input Placeholders: {', '.join(input_placeholders[:3]) if input_placeholders else 'None'}",
                f"Visible Button Texts: {', '.join(button_texts[:3]) if button_texts else 'None'}"
            ]
            return " | ".join(obs_parts)
        except Exception as e:
            return f"Error observing page: {str(e)}"

    async def _plan_next_action(self, goal: str, history: List[Dict]) -> Dict[str, Any]:
        """Uses the LLM to decide the next single action to take."""
        # Format history for the prompt
        history_str = "\n".join([
            f"Step {h['step']}: {h['type']} - {h.get('content', 'N/A')}" 
            for h in history[-5:]  # Use last 5 steps to keep prompt concise
        ]) if history else "No prior steps."
        
        prompt = f"""
You are an expert web navigation agent. Your sole objective is to achieve the user's goal by selecting the NEXT SINGLE ACTION from the provided action library.

User's Goal: "{goal}"

History of Actions and Observations:
{history_str}

Available Actions:
- navigate_to: {{"action": "navigate_to", "arguments": {{"url": "https://example.com"}}}}
- click_selector: {{"action": "click_selector", "arguments": {{"selector": "css-selector-here"}}}}
- type_text: {{"action": "type_text", "arguments": {{"selector": "css-selector-here", "text": "text to type"}}}}
- wait_for_selector: {{"action": "wait_for_selector", "arguments": {{"selector": "css-selector-here", "timeout": 5000}}}}
- go_back: {{"action": "go_back", "arguments": {{}}}}
- refresh: {{"action": "refresh", "arguments": {{}}}}
- extract_text: {{"action": "extract_text", "arguments": {{"selector": "css-selector-here"}}}}

Based SOLELY on the goal and the history, what is the single best action to take now?
Respond with ONLY a valid JSON object containing the "action" and "arguments" keys.
Do not add any explanations, apologies, or extra text.
"""
        
        try:
            # Use the hybrid router to get the LLM's decision
            response = await self.router.route_task(prompt, task_type="reasoning")
            # The router returns the text response; we need to parse it as JSON.
            # We'll find the first and last curly braces to extract the JSON.
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                # Fallback if JSON parsing fails: try a simple refresh
                print(f"WARNING: LLM did not return valid JSON. Response: {response}")
                return {"action": "refresh", "arguments": {}}
        except Exception as e:
            print(f"ERROR in _plan_next_action: {e}")
            return {"action": "refresh", "arguments": {}}

    async def _execute_action(self, state: NavigatorState, action_json: Dict[str, Any]) -> NavigatorState:
        """Executes the action decided by the LLM."""
        action_name = action_json.get("action")
        arguments = action_json.get("arguments", {})
        
        if action_name not in self.action_library:
            print(f"WARNING: Unknown action '{action_name}' chosen by LLM. Defaulting to wait_for_selector.")
            action_name = "wait_for_selector"
            arguments = {"selector": "body", "timeout": 2000}
        
        # Execute the action
        try:
            await self.action_library[action_name](state.page, **arguments)
        except Exception as e:
            print(f"ERROR executing action {action_name}: {e}")
            # On failure, we might want to try a recovery action like go_back or refresh
            # For now, we'll just log it and continue; the observation step will reflect the error.
            pass
        
        # Update state after action
        state.step_count += 1
        state.current_url = state.page.url
        
        return state

    async def _evaluate_goal(self, goal: str, history: List[Dict]) -> bool:
        """Uses the LLM to judge if the goal has been met based on the full history."""
        # Format history for the prompt
        history_str = "\n".join([
            f"Step {h['step']}: {h['type']} - {h.get('content', 'N/A')}" 
            for h in history
        ]) if history else "No steps taken."
        
        prompt = f"""
You are an expert judge evaluating whether a web navigation task has been successfully completed.

User's Original Goal: "{goal}"

Complete History of Actions and Observations:
{history_str}

Based ONLY on the goal and the complete history, has the goal been successfully achieved?
Answer with ONLY the word 'YES' or 'NO'.
Do not add any explanations, apologies, or extra text.
"""
        
        try:
            response = await self.router.route_task(prompt, task_type="reasoning")
            # Clean up the response to get just YES or NO
            cleaned_response = response.strip().upper()
            if cleaned_response == "YES":
                return True
            elif cleaned_response == "NO":
                return False
            else:
                # If the LLM is unclear, we assume the goal is NOT met to be safe.
                print(f"WARNING: LLM returned unclear evaluation: '{response}'. Assuming goal NOT met.")
                return False
        except Exception as e:
            print(f"ERROR in _evaluate_goal: {e}")
            return False

    # --- Action Library Implementations ---
    async def _navigate_to(self, page: Page, url: str):
        await page.goto(url, wait_until="networkidle")

    async def _click_selector(self, page: Page, selector: str):
        await page.click(selector, timeout=5000)
        await page.wait_for_load_state("networkidle")

    async def _type_text(self, page: Page, selector: str, text: str):
        await page.fill(selector, text, timeout=5000)
        await page.wait_for_load_state("networkidle")

    async def _extract_text(self, page: Page, selector: str) -> str:
        return await page.text_content(selector, timeout=5000)

    async def _wait_for_selector(self, page: Page, selector: str, timeout: int = 5000):
        await page.wait_for_selector(selector, timeout=timeout, state="visible")

    async def _go_back(self, page: Page):
        await page.go_back()
        await page.wait_for_load_state("networkidle")

    async def _refresh(self, page: Page):
        await page.reload(wait_until="networkidle")

    def _finalize_result(self, state: NavigatorState) -> Dict[str, Any]:
        """Prepares the final result dictionary to be returned by the engine."""
        if state.goal_met:
            status = "SUCCESS"
            message = f"Goal '{state.goal}' achieved in {state.step_count} steps."
        else:
            status = "FAILURE"
            message = f"Goal '{state.goal}' not achieved after {state.step_count} steps (max steps: {state.max_steps})."
        
        # Extract any final data from the history if needed (e.g., last extracted text)
        extracted_data = None
        for h in reversed(state.history):
            if h["type"] == "observation" and "Extracted Text:" in h.get("content", ""):
                # This is a simplified extraction; a real system would have a dedicated extract action
                pass # Placeholder for more sophisticated data extraction
        
        return {
            "status": status,
            "message": message,
            "goal": state.goal,
            "steps_taken": state.step_count,
            "final_url": state.current_url,
            "history": state.history,
            "extracted_data": extracted_data
        }
# --- END OF AUTONOMOUSLY ADDED NAVIGATOR ENGINE ---
