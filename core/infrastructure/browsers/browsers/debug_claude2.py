#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time, requests

PROFILE_DIR = "/home/yahwehatwork/.browser-profile/google"

# fetch cookies
resp = requests.get("http://127.0.0.1:8000/cookies", params={"url": "https://claude.ai/chat"}, timeout=15)
data = resp.json()
cookies = data.get("cookies", {})
ua = data.get("user_agent")
print("Cookies keys:", list(cookies.keys()))
print("UA:", ua)

opts = Options()
opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
opts.add_argument("--disable-blink-features=AutomationControlled")
opts.add_experimental_option("excludeSwitches", ["enable-automation"])
opts.add_experimental_option("useAutomationExtension", False)
opts.add_argument("--window-size=1280,800")
opts.add_argument(f"user-agent={ua}")

driver = webdriver.Chrome(options=opts)
try:
    driver.get("https://claude.ai")
    # clear existing cookies for domain
    for c in driver.get_cookies():
        if c['domain'] and '.claude.ai' in c['domain']:
            driver.delete_cookie(c['name'])
    # add all
    for name, value in cookies.items():
        driver.add_cookie({"name": name, "value": value, "domain": ".claude.ai", "path": "/"})
    driver.get("https://claude.ai/chat")
    time.sleep(5)
    print("Title:", driver.title)
    print("Current URL:", driver.current_url)
    # save screenshot
    driver.save_screenshot("/tmp/claude_debug.png")
    print("Screenshot saved to /tmp/claude_debug.png")
    # get page source snippet
    src = driver.page_source[:2000]
    print("Source snippet:", src)
finally:
    driver.quit()