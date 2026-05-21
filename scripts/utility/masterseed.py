import time
from camoufox import Camoufox

def seed_profiles():
    # Unified path for the swarm to use
    profile_path = "/home/yahwehatwork/human-ai/data/browser_profiles/master_profile"
    
    print(f"Launching Camoufox in headed mode on your RDP desktop for MASTER SEED...")
    print(f"Saving profile to: {profile_path}")
    print("Please log in to the websites and solve any CAPTCHAs.")
    print("Close the browser window manually when you are finished.")
    
    # Launch headed browser with persistent context, saving cookies/fingerprint to the unified swarm folder
    with Camoufox(headless=False, persistent_context=True, user_data_dir=profile_path) as browser:
        page = browser.new_page()
        
        # Open targets in tabs - using actual login pages where applicable
        page.goto("https://claude.ai/login")
        page.wait_for_timeout(2000)
        
        # Open Perplexity login page
        page2 = browser.new_page()
        page2.goto("https://www.perplexity.ai/account/login")
        
        # Open DeepSeek login page
        page3 = browser.new_page()
        page3.goto("https://chat.deepseek.com/auth/login")
        
        # Open Gemini login page (Google login)
        page4 = browser.new_page()
        page4.goto("https://gemini.google.com/app")
        
        # Keep script running until user closes the browser
        print("Waiting for you to complete logins...")
        try:
            page.wait_for_event("close", timeout=0)
        except Exception:
            pass
            
    print(f"Browser closed. MASTER SEED profile successfully seeded in '{profile_path}'.")

if __name__ == "__main__":
    seed_profiles()
