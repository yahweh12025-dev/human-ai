#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time, os

profile_dir = "/home/yahwehatwork/.browser-profile/google"
opts = Options()
opts.add_argument(f"--user-data-dir={profile_dir}")
opts.add_argument("--disable-blink-features=AutomationControlled")
opts.add_experimental_option("excludeSwitches", ["enable-automation"])
opts.add_experimental_option("useAutomationExtension", False)
opts.add_argument("--window-size=1280,800")
# opts.add_argument("--headless=new")  # keep headed to see
driver = webdriver.Chrome(options=opts)
try:
    driver.get("https://claude.ai/chat")
    time.sleep(5)
    title = driver.title
    print(f"Title: {title}")
    # save screenshot
    screenshot_path = "/tmp/claude_debug.png"
    driver.save_screenshot(screenshot_path)
    print(f"Screenshot saved to {screenshot_path}")
    # save page source snippet
    source = driver.page_source
    with open("/tmp/claude_debug_source.html", "w", encoding="utf-8") as f:
        f.write(source)
    print("Page source saved to /tmp/claude_debug_source.html (first 2000 chars):")
    print(source[:2000])
finally:
    driver.quit()