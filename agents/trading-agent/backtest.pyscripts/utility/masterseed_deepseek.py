import time
from camoufox import Camoufox

def seed_deepseek_profile():
    # Unified path for DeepSeek agent to use
    profile_path = "/home/yahwehatwork/human-ai/data/browser_profiles/deepseek"
    
    print(f"Launching Camoufox in headed mode on your RDP desktop for DEEPSEEK SEED...")
    print(f"Saving profile to: {profile_path}")
    print("Please log in to DeepSeek and solve any CAPTCHAs.")
    print("Close the browser window manually when you are finished.")
    
    # Launch headed browser with persistent context, saving cookies/fingerprint to the DeepSeek folder
    with Camoufox(headless=False, persistent_context=True, user_data_dir=profile_path) as browser:
        page = browser.new_page()
        
        # Open DeepSeek login page only
        page.goto("https://chat.deepseek.com/auth/login")
        
        # Keep script running until user closes the browser
        print("Waiting for you to complete DeepSeek login...")
        try:
            page.wait_for_event("close", timeout=0)
        except Exception:
            pass
        
    print(f"Browser closed. DeepSeek profile successfully seeded in '{profile_path}'.")

if __name__ == "__main__":
    seed_deepseek_profile()