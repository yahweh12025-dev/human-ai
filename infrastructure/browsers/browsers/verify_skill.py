#!/usr/bin/env python3
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---- Configuration ----
PROFILE_DIR = "/home/yahwehatwork/.browser-profile/google"
BYPASS_URL = "http://127.0.0.1:8000/cookies"
TARGET_URL = "https://claude.ai/chat"

# ---- Step 1: Get fresh Cloudflare cookie from bypass server ----
print("[+] Fetching Cloudflare cookie from bypass server...")
resp = requests.get(BYPASS_URL, params={"url": TARGET_URL}, timeout=15)
resp.raise_for_status()
data = resp.json()
cookies = data.get("cookies", {})
ua = data.get("user_agent")
cf_clearance = cookies.get("cf_clearance")
print(f"[+] Got {len(cookies)} cookies")
print(f"[+] CF clearance present: {bool(cf_clearance)}")
print(f"[+] User agent: {ua}")

# ---- Step 2: Set up Chrome with persistent profile ----
chrome_opts = Options()
chrome_opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
chrome_opts.add_argument("--disable-blink-features=AutomationControlled")
chrome_opts.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_opts.add_experimental_option("useAutomationExtension", False)
chrome_opts.add_argument("--window-size=1280,800")
# Match the user agent used by the bypass server (important for Cloudflare binding)
chrome_opts.add_argument(f"user-agent={ua}")
# Keep browser visible for verification; switch to headless after success
# chrome_opts.add_argument("--headless=new")

driver = webdriver.Chrome(options=chrome_opts)
wait = WebDriverWait(driver, 20)

try:
    # ---- Step 3: Prepare cookie context ----
    print("[+] Visiting claude.ai to set cookie context...")
    driver.get("https://claude.ai")  # any subdomain to set cookie for
    time.sleep(1)
    # Remove any existing cf_clearance to avoid conflict
    driver.delete_cookie("cf_clearance")
    # Add the fresh cf_clearance
    driver.add_cookie({
        "name": "cf_clearance",
        "value": cf_clearance,
        "domain": ".claude.ai",
        "path": "/",
    })
    # Optionally add other cookies from bypass (may help)
    for name, value in cookies.items():
        if name != "cf_clearance":
            driver.add_cookie({
                "name": name,
                "value": value,
                "domain": ".claude.ai",
                "path": "/",
            })
    print("[+] Added cookies to browser")

    # ---- Step 4: Navigate to chat and verify ----
    print("[+] Navigating to Claude chat...")
    driver.get(TARGET_URL)
    print("[+] Waiting for chat input to appear...")
    chat_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//textarea[@placeholder='Ask Claude anything'] | //div[@contenteditable='true' and @role='textbox']")
        )
    )
    print("[+] SUCCESS: Chat input is visible – you are logged in and past Cloudflare!")
    # Optional: send a test message to verify interactivity
    chat_input.send_keys("Test from Hermes skill verification")
    chat_input.submit()
    print("[+] Test message sent.")
    time.sleep(3)  # let you see the result
    # Save screenshot for proof
    driver.save_screenshot("/tmp/claude_success.png")
    print("[+] Screenshot saved to /tmp/claude_success.png")

except Exception as e:
    print(f"[!] Error: {e}")
    # Save debug info
    driver.save_screenshot("/tmp/claude_error.png")
    print("[+] Error screenshot saved to /tmp/claude_error.png")
    raise
finally:
    driver.quit()