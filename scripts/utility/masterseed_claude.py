#!/usr/bin/env python3
"""
Master seed script for Claude.ai persistent profile using Camoufox.
This script creates and maintains a persistent browser profile for Claude.ai
to enable automated access without repeated login prompts.
"""

import time
from camoufox import Camoufox

def seed_claude_profile():
    # Unified path for Claude agent to use
    profile_path = "/home/yahwehatwork/human-ai/data/browser_profiles/claude"
    
    print(f"Launching Camoufox in headed mode on your RDP desktop for CLAUDE SEED...")
    print(f"Saving profile to: {profile_path}")
    print("Please log in to Claude.ai using your Google account and solve any CAPTCHAs.")
    print("Close the browser window manually when you are finished.")
    
    # Launch headed browser with persistent context, saving cookies/fingerprint to the Claude folder
    with Camoufox(headless=False, persistent_context=True, user_data_dir=profile_path) as browser:
        page = browser.new_page()
        
        # Open Claude.ai login page only
        page.goto("https://claude.ai")
        
        # Keep script running until user closes the browser
        print("Waiting for you to complete Claude.ai login...")
        try:
            page.wait_for_event("close", timeout=0)
        except Exception:
            pass
    
    print(f"Browser closed. Claude profile successfully seeded in '{profile_path}'.")

if __name__ == "__main__":
    seed_claude_profile()