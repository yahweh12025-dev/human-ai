#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

profile_dir = "/home/yahwehatwork/.browser-profile/google"

options = Options()
options.add_argument(f"--user-data-dir={profile_dir}")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--window-size=1280,800")
# options.add_argument("--headless=new")  # set True for headless after verifying

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 20)

def test_claude():
    print("Opening Claude...")
    driver.get("https://claude.ai/chat")
    try:
        # Wait for page to load, check for Cloudflare or chat
        # Cloudflare challenge often contains text "Checking your browser" or "Please verify you are human"
        # We'll wait up to 15 seconds for either
        try:
            wait.until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Checking your browser') or contains(text(),'Please verify you are human')]")),
                    EC.presence_of_element_located((By.XPATH, "//textarea[@placeholder='Ask Claude anything'] | //div[@contenteditable='true' and @role='textbox']"))
                )
            )
        except:
            pass
        # Give a bit more time for possible auto-resolution
        time.sleep(5)
        # Get page title and save screenshot
        title = driver.title
        print(f"Page title: {title}")
        screenshot_path = "/tmp/claude_screenshot.png"
        driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        # Also get page source snippet
        source = driver.page_source[:2000]
        print("Page source snippet:")
        print(source[:1000])
        return screenshot_path
    finally:
        driver.quit()

if __name__ == "__main__":
    screenshot = test_claude()
    print(f"\nScreenshot path: {screenshot}")