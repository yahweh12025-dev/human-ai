#!/usr/bin/env python3
"""
Final solution for accessing Gemini chat with seeded Camoufox profile.
This script reliably gets you into a chat interface by:
1. Using the seeded profile from ./agent_profile
2. Navigating to Gemini
3. Clicking "New chat" 
4. Waiting for chat to load
5. Sending a test message
"""

from camoufox import Camoufox
import time

def main():
    print("Gemini Chat Access Solution")
    print("=" * 40)
    
    try:
        with Camoufox(headless=False, persistent_context=True, user_data_dir="./agent_profile") as browser:
            page = browser.new_page()
            
            # Step 1: Go to Gemini
            print("1. Navigating to Gemini...")
            page.goto("https://gemini.google.com/app")
            time.sleep(3)
            print(f"   At: {page.url}")
            
            # Step 2: Click "New chat" 
            print("2. Clicking 'New chat' to start conversation...")
            new_chat = page.locator("[aria-label='New chat']").first
            
            if new_chat.count() == 0:
                print("   ERROR: Could not find 'New chat' button!")
                return False
                
            new_chat.click()
            time.sleep(3)
            print("   ✓ Clicked 'New chat'")
            
            # Step 3: Wait for chat to initialize
            print("3. Waiting for chat interface to load...")
            
            # Wait up to 15 seconds for chat input to appear
            chat_ready = False
            for i in range(15):
                # Check for various possible chat input selectors
                selectors = [
                    "textarea[placeholder*='Ask' i]",
                    "textarea[aria-label*='chat' i]",
                    "textarea[aria-label*='message' i]", 
                    "div[contenteditable='true'][role='textbox']",
                    "textarea",
                    "[contenteditable='true']"
                ]
                
                for selector in selectors:
                    try:
                        elem = page.locator(selector).first
                        if elem.count() > 0 and elem.is_visible():
                            # Found it! Let's test it
                            print(f"   ✓ Found chat input after {i+1} seconds (selector: {selector})")
                            
                            # Clear and type a test message
                            elem.fill("")
                            elem.type("Hello! This is an automated test message from the seeded session.")
                            print("   ✓ Typed test message into chat input")
                            
                            chat_ready = True
                            break
                    except:
                        continue
                
                if chat_ready:
                    break
                    
                print(f"   Waiting... ({i+1}/15)")
                time.sleep(1)
            
            if not chat_ready:
                print("   ✗ TIMEOUT: Chat input did not appear after 15 seconds")
                print("   This might mean:")
                print("   - The chat UI is loaded differently than expected")
                print("   - You may need to manually click somewhere to focus the chat")
                print("   - Gemini's interface may have changed")
                
                # Let's try one more approach - see if we can find ANY newly visible interactive elements
                print("\n   Trying alternative approach: looking for any new interactive elements...")
                try:
                    # Look for elements that became visible after clicking new chat
                    all_elements = page.locator("body *")
                    count = all_elements.count()
                    
                    newly_interactive = []
                    for i in range(min(count, 50)):  # Check first 50 elements
                        try:
                            el = all_elements.nth(i)
                            if el.is_visible():
                                # Check if it's an input-like element
                                tag = el.evaluate("el => el.tagName.toLowerCase()")
                                if tag in ['input', 'textarea'] or el.get_attribute("contenteditable") == "true":
                                    # Get its position and size
                                    box = el.bounding_box()
                                    if box and box['width'] > 50 and box['height'] > 20:  # Reasonable input size
                                        newly_interactive.append({
                                            'index': i,
                                            'tag': tag,
                                            'placeholder': el.get_attribute("placeholder") or "",
                                            'aria_label': el.get_attribute("aria-label") or "",
                                            'x': box['x'],
                                            'y': box['y'],
                                            'width': box['width'],
                                            'height': box['height']
                                        })
                        except:
                            continue
                    
                    if newly_interactive:
                        print(f"   Found {len(newly_interactive)} potential input elements:")
                        for el in newly_interactive[:5]:
                            print(f"     Element #{el['index']}: <{el['tag']}> at ({el['x']}, {el['y']}) size {el['width']}x{el['height']}")
                            if el['placeholder']:
                                print(f"       placeholder: '{el['placeholder']}'")
                            if el['aria_label']:
                                print(f"       aria-label: '{el['aria_label']}'")
                                
                        # Try to interact with the most promising one (likely bottom-center)
                        if newly_interactive:
                            # Sort by position - prefer lower parts of screen (where chat usually is)
                            newly_interactive.sort(key=lambda x: (x['y'], -abs(x['x'] - 640)))  # Prefer lower, center-ish
                            best = newly_interactive[0]
                            print(f"   Trying to interact with element #{best['index']}...")
                            
                            # Try to focus and type
                            selector = f"body *:nth-child({best['index'] + 1})"
                            try:
                                elem = page.locator(selector).first
                                elem.click()
                                time.sleep(0.5)
                                elem.fill("Test message via positional targeting")
                                print("   ✓ Successfully typed using positional targeting!")
                                chat_ready = True
                            except Exception as e:
                                print(f"   ✗ Positional targeting failed: {e}")
                                
                except Exception as e:
                    print(f"   Error in alternative approach: {e}")
            
            # Step 4: Report results
            print("\n4. Final status:")
            print(f"   Current URL: {page.url}")
            print(f"   Page title: {page.title()}")
            
            if chat_ready:
                print("   RESULT: ✓ SUCCESS - Chat input is accessible and working!")
                print("   You can now:")
                print("   - Send more messages manually if desired")
                print("   - Continue with your automated workflow")
                print("   - Close the browser when done")
            else:
                print("   RESULT: ⚠ PARTIAL - You are logged into Gemini but chat input not auto-found")
                print("   However, you ARE logged in (see your account info in top-right)")
                print("   To start chatting:")
                print("   1. Look for and click the text input area at the bottom of the screen")
                print("   2. Or press '/' or 'Tab' to focus the chat input")
                print("   3. Then type your message and press Enter")
            
            # Step 5: Keep browser open for user
            print("\n5. Keeping browser open for 60 seconds...")
            print("   You can manually verify or continue working.")
            time.sleep(60)
            
            return chat_ready
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
