#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from pathlib import Path

profile_dir = str(Path.home() / ".browser-profile" / "google")
options = Options()
options.add_argument(f"--user-data-dir={profile_dir}")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--window-size=1280,800")
# options.add_argument("--headless=new")  # keep headed for manual solve

driver = webdriver.Chrome(options=options)
driver.get("https://claude.ai/chat")
print("\n=== Manual Cloudflare solve ===")
print("A Chrome window has opened to https://claude.ai/chat")
print("If you see a Cloudflare challenge (\"Just a moment...\" with a checkbox),")
print("please solve it manually (click the checkbox or complete any puzzle).")
print("After the challenge clears and you see the Claude chat input box,")
print("press ENTER in this terminal to close the browser and save the profile.\n")
input()  # wait for user
driver.quit()
print("Browser closed. Profile updated at:", profile_dir)