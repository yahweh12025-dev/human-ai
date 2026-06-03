#!/usr/bin/env python3
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ---- persistent profile location ----
profile_dir = Path.home() / ".browser-profile" / "google"
profile_dir.mkdir(parents=True, exist_ok=True)

# ---- Chrome options that hide automation ----
chrome_opts = Options()
chrome_opts.add_argument(f"--user-data-dir={profile_dir}")
chrome_opts.add_argument("--disable-blink-features=AutomationControlled")
chrome_opts.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_opts.add_experimental_option("useAutomationExtension", False)
chrome_opts.add_argument("--window-size=1280,800")
chrome_opts.add_argument(
    "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# ---- launch Chrome ----
driver = webdriver.Chrome(options=chrome_opts)

# Hide the webdriver flag from JS (extra safety)
driver.execute_cdp_cmd(
    "Page.addScriptToEvaluateOnNewDocument",
    {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
)

# ---- open Google sign‑in page ----
driver.get("https://accounts.google.com/signin")
print("\n=== Please log in to your Google account in the opened Chrome window ===")
print("After you have successfully signed in, press ENTER in this terminal to close the browser.\n")

# Wait for you to hit Enter
input()   # blocks until you press Enter

# ---- clean up ----
driver.quit()
print("Browser closed. Your session is saved under:", profile_dir)