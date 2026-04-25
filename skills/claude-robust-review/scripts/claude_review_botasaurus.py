#!/usr/bin/env python3
"""
Botasaurus-powered Claude.ai agent for tasks like code review.
This serves as a fallback when the primary hybrid router method fails due to Cloudflare.
"""

import json
import os
import sys
import time

# Add Botasaurus to path
sys.path.insert(0, '/home/yahwehatwork/human-ai/botasaurus')
sys.path.insert(0, '/home/yahwehatwork/.local/lib/python3.11/site-packages')

from botasaurus.browser import browser, Driver

@browser
def claude_review_botasaurus(driver: Driver, data):
    """
    Use Botasaurus to access Claude.ai for a given prompt (e.g., code review).
    """
    prompt = data.get('prompt', '')
    trading_agent_path = data.get('trading_agent_path', 
                               '/home/yahwehatwork/human-ai/agents/trading-agent/trading_agent.py')
    
    # If no prompt provided, create a default code review prompt for the trading agent
    if not prompt:
        try:
            with open(trading_agent_path, 'r') as f:
                trading_code = f.read()
        except FileNotFoundError:
            return {
                "status": "error",
                "message": f"Trading agent file not found at {trading_agent_path}",
                "method": "botasaurus_claude_fallback"
            }
        
        prompt = f"""
        Please review this trading agent code and provide detailed feedback on:
        1. Code structure and organization
        2. Potential bugs or issues
        3. Best practices and improvements
        4. Security considerations
        5. Performance optimizations
        
        Here's the code:
        
        {trading_code}
        
        Please provide a comprehensive, professional code review.
        """
    
    print("🤖 Initializing Botasaurus Claude agent...")
    
    try:
        # Navigate to Claude with Cloudflare bypass
        print("🌐 Navigating to Claude.ai...")
        driver.google_get("https://claude.ai/chats", bypass_cloudflare=True)
        
        # Wait for the chat interface to be ready
        print("⏳ Waiting for chat interface...")
        driver.wait_for_element('[data-testid="chat-input"], [role="textbox"], textarea[placeholder*="Message"]', timeout=15)
        
        # Type the prompt
        print("📝 Typing prompt...")
        driver.type('[data-testid="chat-input"], [role="textbox"], textarea[placeholder*="Message"]', prompt)
        
        # Submit the prompt
        print("🚀 Submitting prompt...")
        driver.press("Enter")
        
        # Wait for response to start and then complete
        print("⏳ Waiting for Claude's response...")
        
        # Wait for the response to begin (stop button appears or response starts)
        start_time = time.time()
        timeout = 120  # 2 minutes for response
        
        # First, wait for the stop button to appear (indicating response is generating)
        while time.time() - start_time < timeout:
            try:
                if driver.is_element_visible('.stop-button', timeout=1):
                    break
            except:
                pass
            time.sleep(1)
        
        # Now wait for the stop button to disappear (indicating response is done)
        while time.time() - start_time < timeout:
            try:
                if not driver.is_element_visible('.stop-button', timeout=1):
                    # Response likely done, get the latest message
                    # Wait a bit more to ensure complete
                    time.sleep(2)
                    messages = driver.select_all('.message')
                    if messages:
                        latest_response = messages[-1].get_text()
                        if len(latest_response.strip()) > 30:  # Arbitrary threshold for meaningful response
                            return {
                                "status": "success",
                                "review": latest_response.strip(),
                                "method": "botasaurus_claude_fallback",
                                "prompt_used": prompt[:100] + "..." if len(prompt) > 100 else prompt
                            }
            except:
                pass
            time.sleep(2)
        
        # If we reach here, timeout occurred
        return {
            "status": "timeout",
            "message": "Response generation timed out after 2 minutes",
            "method": "botasaurus_claude_fallback"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Botasaurus Claude agent failed: {str(e)}",
            "method": "botasaurus_claude_fallback"
        }

if __name__ == "__main__":
    # Example usage: python3 claude_review_botasaurus.py --prompt "Your prompt" --trading-agent-path "/path/to/file"
    import argparse
    
    parser = argparse.ArgumentParser(description='Use Botasaurus to access Claude.ai for code review or other tasks.')
    parser.add_argument('--prompt', type=str, help='The prompt to send to Claude')
    parser.add_argument('--trading-agent-path', type=str, 
                       default='/home/yahwehatwork/human-ai/agents/trading-agent/trading_agent.py',
                       help='Path to the trading agent file for default code review prompt')
    parser.add_argument('--output', type=str, help='Output file for the result (JSON)')
    
    args = parser.parse_args()
    
    data = {
        'prompt': args.prompt,
        'trading_agent_path': args.trading_agent_path
    }
    
    result = claude_review_botasaurus(data)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Result saved to {args.output}")
    else:
        print(json.dumps(result, indent=2))