#!/usr/bin/env python3
"""
Prompt DeepSeek using Camoufox in headless mode with virtual display.
Accepts a question via --prompt or DEEPSEEK_PROMPT env var and saves response.

Usage:
  python3 prompt_deepseek.py "What are the best gold trading strategies?"
  DEEPSEEK_PROMPT="..." python3 prompt_deepseek.py
"""

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# Ensure virtual display is set before importing Camoufox
_DISPLAY = os.environ.get("DISPLAY", ":11")
os.environ["DISPLAY"] = _DISPLAY

try:
    from camoufox import Camoufox
except ImportError:
    print("ERROR: camoufox not installed — run: pip install camoufox")
    sys.exit(1)

from dotenv import load_dotenv
_PROJECT_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
if _PROJECT_ROOT_ENV.exists():
    load_dotenv(_PROJECT_ROOT_ENV)

PROJECT_ROOT  = Path(__file__).resolve().parents[2]
PROFILE_DIR   = Path.home() / "agent_profile"
RESEARCH_DIR  = PROJECT_ROOT / "research"
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

# DeepSeek credentials (set in .env as DEEPSEEK_EMAIL / DEEPSEEK_PASSWORD)
DS_EMAIL    = os.getenv("DEEPSEEK_EMAIL", "")
DS_PASSWORD = os.getenv("DEEPSEEK_PASSWORD", "")

# ── Max wait for DeepSeek to finish generating ────────────────
MAX_WAIT_S = 90

# ── Selectors ─────────────────────────────────────────────────
INPUT_SELECTORS = [
    "textarea[placeholder*='Message DeepSeek' i]",
    "textarea[placeholder*='Message' i]",
    "textarea#chat-input",
    "textarea[placeholder*='Send' i]",
    "div[contenteditable='true'][role='textbox']",
    "div[contenteditable='true']",
    "textarea",
    "[placeholder*='Message' i]",
]
RESPONSE_SELECTORS = [
    ".ds-markdown",                          # primary — confirmed working
    "[class*='assistant'] .ds-markdown",     # assistant bubble
    "[class*='markdown']",                   # fallback
    "[class*='content'] .ds-markdown",
]


def prompt_deepseek(question: str, save_path: str = None) -> str:
    """
    Open DeepSeek in headless Camoufox, submit question, wait for response.
    Returns the response text (also saves to file if save_path given).
    """
    print(f"[DeepSeek] Display: {_DISPLAY} | headless=True")
    print(f"[DeepSeek] Profile: {PROFILE_DIR}")
    print(f"[DeepSeek] Question: {question[:100]}")

    if not PROFILE_DIR.exists():
        print(f"[DeepSeek] WARNING: profile dir not found at {PROFILE_DIR}")
        print("[DeepSeek] Browser may require manual login on first run")

    # Always use the profile dir (create if missing) so sessions persist across runs
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # headless=True with an active Xvfb display works for Camoufox
        ctx_kwargs = {
            "headless": True,
            "persistent_context": True,
            "user_data_dir": str(PROFILE_DIR),
        }

        with Camoufox(**ctx_kwargs) as browser:
            page = browser.new_page()
            page.set_default_timeout(20_000)

            print("[DeepSeek] Navigating to chat.deepseek.com ...")
            page.goto("https://chat.deepseek.com", wait_until="domcontentloaded", timeout=30_000)
            time.sleep(4)

            # Check login status — auto-login if credentials available
            html = page.content().lower()
            needs_login = any(s in html for s in ("sign in", "log in", "login", "phone number"))
            if needs_login:
                if DS_EMAIL and DS_PASSWORD:
                    print("[DeepSeek] Not logged in — attempting auto-login...")
                    try:
                        email_inp = page.locator("input[type='email'], input[placeholder*='email' i], input[placeholder*='phone' i]").first
                        if email_inp.is_visible():
                            email_inp.fill(DS_EMAIL)
                        pwd_inp = page.locator("input[type='password']").first
                        if pwd_inp.is_visible():
                            pwd_inp.fill(DS_PASSWORD)
                        page.locator("button:has-text('Log in'), button[type='submit']").first.click()
                        time.sleep(6)
                        # Refresh HTML — check we're on chat page (not login page)
                        html = page.content().lower()
                        still_on_login = ("phone number" in html or
                                          ("log in" in html and "new chat" not in html))
                        if still_on_login:
                            print("[DeepSeek] Login may have failed — check DEEPSEEK_EMAIL/DEEPSEEK_PASSWORD in .env")
                        else:
                            print("[DeepSeek] Auto-login succeeded — saving session")
                            # Save session so future runs skip login
                            if not PROFILE_DIR.exists():
                                PROFILE_DIR.mkdir(parents=True, exist_ok=True)
                    except Exception as e_login:
                        print(f"[DeepSeek] Auto-login error: {e_login}")
                else:
                    print("[DeepSeek] Not logged in. Add DEEPSEEK_EMAIL and DEEPSEEK_PASSWORD to .env")
                    print("[DeepSeek] Or run: python3 scripts/utility/seed_deepseek_session.py to log in once")
                    page.screenshot(path="/tmp/deepseek_login_needed.png")
                    return ""

            # Always click "New chat" to get a clean conversation
            try:
                nc = page.locator("a:has-text('New chat'), button:has-text('New chat'), [aria-label*='New chat' i]")
                if nc.count() > 0 and nc.first.is_visible():
                    nc.first.click()
                    time.sleep(2)
                    print("[DeepSeek] Clicked New chat")
            except Exception:
                pass

            # Find chat input — wait briefly for page to settle
            time.sleep(1)
            chat_input = None
            for sel in INPUT_SELECTORS:
                try:
                    loc = page.locator(sel)
                    if loc.count() > 0 and loc.first.is_visible():
                        chat_input = loc.first
                        print(f"[DeepSeek] Input found: {sel}")
                        break
                except Exception:
                    continue

            if not chat_input:
                page.screenshot(path="/tmp/deepseek_debug.png")
                print("[DeepSeek] ERROR: could not find chat input (screenshot: /tmp/deepseek_debug.png)")
                return ""

            # Submit the question
            print("[DeepSeek] Submitting question...")
            chat_input.click()
            chat_input.fill(question)
            time.sleep(0.5)
            chat_input.press("Enter")

            # Wait for response
            print(f"[DeepSeek] Waiting up to {MAX_WAIT_S}s for response...")
            start = time.time()
            response = ""
            last_len = 0
            stable_count = 0

            while time.time() - start < MAX_WAIT_S:
                # Get ALL .ds-markdown elements and use the LAST one (assistant reply)
                # Skip the first one which contains the user's own message
                cur_text = ""
                for sel in RESPONSE_SELECTORS:
                    try:
                        els = page.locator(sel)
                        n = els.count()
                        if n > 0:
                            # Collect all non-empty texts, skip ones that match our question
                            for i in range(n - 1, -1, -1):  # iterate from last
                                try:
                                    t = els.nth(i).inner_text().strip()
                                    # Skip if it's just our prompt echoed back
                                    q_words = question.lower().split()[:5]
                                    if t and len(t) > 15 and not all(w in t.lower() for w in q_words[:3]):
                                        cur_text = t
                                        break
                                except Exception:
                                    continue
                        if cur_text:
                            break
                    except Exception:
                        continue

                # Check if still generating (stop button visible)
                try:
                    stop = page.locator("button[aria-label*='stop' i], button:has-text('Stop')")
                    generating = stop.count() > 0 and stop.first.is_visible()
                except Exception:
                    generating = False

                if cur_text:
                    if not generating:
                        # Not generating + have text: check it's stable
                        if len(cur_text) == last_len:
                            stable_count += 1
                            if stable_count >= 2:
                                response = cur_text
                                print(f"[DeepSeek] Response complete: {time.time()-start:.1f}s ({len(response)} chars)")
                                break
                        else:
                            stable_count = 0
                            last_len = len(cur_text)
                    else:
                        # Still generating — reset stability
                        stable_count = 0
                        last_len = len(cur_text)

                elapsed = int(time.time() - start)
                if elapsed % 15 == 0 and elapsed > 0:
                    print(f"[DeepSeek] Still waiting... {elapsed}s | generating={generating} | text_len={len(cur_text)}")
                time.sleep(2)

            if not response and cur_text:
                response = cur_text  # use whatever we have on timeout

    except Exception as e:
        print(f"[DeepSeek] Browser error: {e}")
        import traceback
        traceback.print_exc()
        return ""

    if not response:
        print("[DeepSeek] No response received")
        return ""

    # Save to file
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_text(
            f"# DeepSeek Research\n**Question:** {question}\n\n---\n\n{response}\n"
        )
        print(f"[DeepSeek] Saved to: {save_path}")
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        auto_path = RESEARCH_DIR / f"deepseek_{ts}.md"
        auto_path.write_text(
            f"# DeepSeek Research\n**Question:** {question}\n\n---\n\n{response}\n"
        )
        print(f"[DeepSeek] Auto-saved to: {auto_path}")

    return response


def main():
    parser = argparse.ArgumentParser(description="Prompt DeepSeek in headless browser mode")
    parser.add_argument("prompt", nargs="?", default="", help="Question to ask DeepSeek")
    parser.add_argument("--save", "-s", default="", help="Path to save response")
    args = parser.parse_args()

    question = args.prompt or os.environ.get("DEEPSEEK_PROMPT", "")
    if not question:
        print("Usage: python3 prompt_deepseek.py 'Your question here'")
        print("   or: DEEPSEEK_PROMPT='...' python3 prompt_deepseek.py")
        sys.exit(1)

    save_path = args.save or os.environ.get("DEEPSEEK_SAVE_PATH", "")
    response = prompt_deepseek(question, save_path or None)

    if response:
        print("\n--- RESPONSE ---")
        print(response[:500] + ("..." if len(response) > 500 else ""))
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
