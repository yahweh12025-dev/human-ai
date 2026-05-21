#!/usr/bin/env python3
"""
Test script to verify Gemini session is working with seeded profile.
This script:
1. Loads the seeded Camoufox profile from ./agent_profile
2. Navigates to Gemini
3. Clicks "New chat" to start a conversation
4. Waits for the chat input to appear
5. Sends a test message
6. Keeps the browser open for manual verification
"""

from camoufox import Camoufox
import time

def test_gemini_session():
    print("Testing Gemini session from seeded profile...")
    print("=" * 50)
    
    try:
        with Camoufox(headless=False, persistent_context=True, user_data_dir="./agent_profile") as browser:
            # Create a new page
            page = browser.new_page()
            
            # Navigate to Gemini app
            print("Step 1: Navigating to Gemini...")
            page.goto("https://gemini.google.com/app")
            time.sleep(3)
            
            print(f"   Current URL: {page.url}")
            print(f"   Page title: {page.title()}")
            
            # Click "New chat" to start a conversation
            print("\nStep 2: Clicking 'New chat' to start conversation...")
            new_chat_btn = page.locator("[aria-label='New chat']").first
            
            if new_chat_btn.count() > 0:
                new_chat_btn.click()
                print("   ✓ Clicked 'New chat' button")
                time.sleep(3)  # Wait for chat UI to load
            else:
                print("   ✗ Could not find 'New chat' button")
                # Try alternative selectors
                alt_selectors = [
                    "text=New chat",
                    "button:has-text('New chat')",
                    "[aria-label*='new chat' i]"
                ]
                for selector in alt_selectors:
                    try:
                        alt_btn = page.locator(selector).first
                        if alt_btn.count() > 0:
                            alt_btn.click()
                            print(f"   ✓ Clicked 'New chat' using selector: {selector}")
                            time.sleep(3)
                            break
                    except:
                        continue
                else:
                    print("   ✗ All attempts to find 'New chat' button failed")
            
            # Wait for and find the chat input
            print("\nStep 3: Waiting for chat input to appear...")
            chat_input = None
            
            # Common selectors for Gemini chat input
            input_selectors = [
                "textarea[placeholder*='Ask' i]",
                "textarea[aria-label*='chat' i]", 
                "textarea[aria-label*='message' i]",
                "div[contenteditable='true'][role='textbox']",
                "textarea",
                "[contenteditable='true']"
            ]
            
            # Wait up to 10 seconds for input to appear
            for i in range(10):
                for selector in input_selectors:
                    try:
                        inp = page.locator(selector).first
                        if inp.count() > 0 and inp.is_visible():
                            chat_input = inp
                            print(f"   ✓ Found chat input with selector: {selector}")
                            break
                    except:
                        continue
                if chat_input:
                    break
                time.sleep(1)
                print(f"   Waiting... ({i+1}/10)")
            
            if chat_input:
                # Test typing a message
                print("\nStep 4: Testing chat input...")
                try:
                    # Clear any existing content and type a test message
                    chat_input.fill("")
                    chat_input.type("Hello! This is a test message from the automated session tester.")
                    print("   ✓ Successfully typed test message")
                    
                    # Optional: Try to send the message (press Enter)
                    # Uncomment the next lines if you want to actually send the message
                    # print("   Sending message...")
                    # chat_input.press("Enter")
                    # time.sleep(2)
                    # print("   ✓ Message sent")
                    
                except Exception as e:
                    print(f"   ✗ Error typing in chat input: {e}")
            else:
                print("   ✗ Could not find visible chat input after waiting")
                print("   This might mean:")
                print("   - The chat UI didn't load properly")
                print("   - You need to manually click somewhere to focus the chat")
                print("   - The page structure has changed")
            
            print("\nStep 5: Session test complete!")
            print(f"   Final URL: {page.url}")
            print(f"   Final title: {page.title()}")
            print("\nThe browser will remain open for 30 seconds for manual inspection.")
            print("You can:")
            print("  - Verify you're logged into Gemini")
            print("  - Check if the chat input is visible and usable")
            print("  - Try sending a message manually if needed")
            
            # Keep browser open for manual verification
            time.sleep(30)
            
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gemini_session()
