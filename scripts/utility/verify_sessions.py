#!/usr/bin/env python3
"""
Verification script for all seeded sessions.
This script checks that you're logged into all services using the seeded Camoufox profile.
"""

from camoufox import Camoufox
import time

def test_service(name, url, logged_in_indicators, logged_out_indicators=None):
    """Test if we're logged into a service"""
    print(f"\nTesting {name}...")
    try:
        with Camoufox(headless=False, persistent_context=True, user_data_dir="./agent_profile") as browser:
            page = browser.new_page()
            page.goto(url)
            time.sleep(3)
            
            content = page.content().lower()
            title = page.title()
            current_url = page.url
            
            print(f"  URL: {current_url}")
            print(f"  Title: {title}")
            
            # Check for logged in indicators
            logged_in = any(indicator in content for indicator in logged_in_indicators)
            
            # Check for logged out indicators (if provided)
            logged_out = False
            if logged_out_indicators:
                logged_out = any(indicator in content for indicator in logged_out_indicators)
            
            if logged_in and not logged_out:
                print(f"  ✓ {name}: LOGGED IN")
                return True
            elif logged_out and not logged_in:
                print(f"  ✗ {name}: LOGGED OUT")
                return False
            else:
                print(f"  ? {name}: UNDETERMINED (found both in/out indicators or neither)")
                return False
                
    except Exception as e:
        print(f"  ✗ {name}: ERROR - {e}")
        return False

def main():
    print("Verifying Seeded Sessions")
    print("=" * 40)
    print("Checking if you're logged into services using the seeded Camoufox profile")
    print("from ./agent_profile\n")
    
    results = {}
    
    # Test Gemini
    results['Gemini'] = test_service(
        'Gemini',
        'https://gemini.google.com/app',
        ['gemini', 'welcome'],  # When logged in
        ['sign in', 'login']    # When logged out
    )
    
    # Test Perplexity
    results['Perplexity'] = test_service(
        'Perplexity',
        'https://www.perplexity.ai',
        ['ask anything', 'your library'],  # When logged in
        ['log in', 'sign up']             # When logged out
    )
    
    # Test DeepSeek
    results['DeepSeek'] = test_service(
        'DeepSeek',
        'https://chat.deepseek.com',
        ['new conversation', 'deepseek'],  # When logged in
        ['log in', 'sign in']              # When logged out
    )
    
    # Test Claude
    results['Claude'] = test_service(
        'Claude',
        'https://claude.ai',
        ['new chat', 'claude'],           # When logged in
        ['log in', 'sign in']             # When logged out
    )
    
    # Summary
    print("\n" + "=" * 40)
    print("SESSION VERIFICATION RESULTS")
    print("=" * 40)
    
    all_good = True
    for service, logged_in in results.items():
        status = "✓ LOGGED IN" if logged_in else "✗ NOT LOGGED IN"
        print(f"{service:<12}: {status}")
        if not logged_in:
            all_good = False
    
    print("\n" + "=" * 40)
    if all_good:
        print("🎉 ALL SERVICES: You are successfully logged into all services!")
        print("   Your seeded Camoufox profile is working correctly.")
        print("\nTo start chatting in Gemini:")
        print("  1. The browser should already be open at https://gemini.google.com/app")
        print("  2. Look for the text input box at the bottom of the screen")
        print("  3. Click in it and start typing your message")
        print("  4. Press Enter to send")
        print("\nIf you don't see the chat input:")
        print("  - Try clicking the 'New chat' button (top left or sidebar)")
        print("  - Or press '/' or 'Tab' to focus the chat input")
    else:
        print("⚠  Some services show as not logged in.")
        print("   This might be due to:")
        print("   - Page loading delays")
        print("   - Different indicator text than expected")
        print("   - Need to complete login for some services")
        print("\nYou can manually verify by:")
        print("  - Checking if you see your account/profile info in the top-right")
        print("  - Looking for logout buttons or account menus")
        print("  - Trying to access features that require login")
    
    print("\n" + "=" * 40)
    print("Tip: You can reuse this profile in any Camoufox script with:")
    print("  Camoufox(headless=False, persistent_context=True, user_data_dir='./agent_profile')")
    
    # Keep browser open if any were tested (last one will stay open)
    print("\nKeeping browser open for 20 seconds for final verification...")
    time.sleep(20)

if __name__ == "__main__":
    main()
