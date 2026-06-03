import time
from camoufox import Camoufox

def seed_google_profile():
    # Path for Google agent to use
    profile_path = "/home/yahwehatwork/human-ai/data/browser_profiles/google"
    
    print(f"Launching Camoufox in headed mode on your RDP desktop for GOOGLE SEED...")
    print(f"Saving profile to: {profile_path}")
    print("Please log in to Google and solve any CAPTCHAs.")
    print("Close the browser window manually when you are finished.")
    
    # Launch headed browser with persistent context, saving cookies/fingerprint to the Google folder
    with Camoufox(headless=False, persistent_context=True, user_data_dir=profile_path) as browser:
        page = browser.new_page()
        
        # Open Google login page
        page.goto("https://accounts.google.com/signin")
        
        # Keep script running until user closes the browser
        print("Waiting for you to complete Google login...")
        try:
            page.wait_for_event("close", timeout=0)
        except Exception:
            pass
        
    print(f"Browser closed. Google profile successfully seeded in '{profile_path}'.")

if __name__ == "__main__":
    seed_google_profile()