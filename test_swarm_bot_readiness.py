#!/usr/bin/env python3
"""Test to verify the Swarm bot is ready for Telegram communication."""

import os
import sys
from dotenv import load_dotenv

def test_swarm_bot_token():
    """Test that the Swarm bot has a valid token configured."""
    # Load environment variables from the human-ai directory
    load_dotenv("/home/ubuntu/.openclaw/workspace/.env")  # Try workspace first
    load_dotenv("/home/ubuntu/human-ai/.env")           # Then human-ai
    
    swarm_token = os.getenv('SWARM_BOT_TOKEN')
    
    if not swarm_token:
        print("❌ FAIL: SWARM_BOT_TOKEN not found in environment")
        return False
    
    # Basic token format validation
    if not swarm_token.startswith('8681001646:'):
        print(f"❌ FAIL: SWARM_BOT_TOKEN does not match expected format for @Swarm26_bot")
        print(f"   Token: {swarm_token}")
        return False
    
    if len(swarm_token) < 40:  # Telegram tokens are quite long
        print(f"❌ FAIL: SWARM_BOT_TOKEN appears too short")
        print(f"   Token: {swarm_token}")
        return False
    
    print(f"✅ PASS: SWARM_BOT_TOKEN is present and appears valid")
    print(f"   Token prefix: {swarm_token[:20]}...")
    print(f"   Token length: {len(swarm_token)} characters")
    return True

def test_bot_distinction():
    """Test that all three bots have distinct tokens."""
    load_dotenv("/home/ubuntu/human-ai/.env")
    
    swarm_token = os.getenv('SWARM_BOT_TOKEN')
    hermes_token = os.getenv('TELEGRAM_BOT_TOKEN')  # In human-ai/.env, this is for Hermes
    
    # Get OpenClaw bot token from config
    import json
    try:
        with open('/home/ubuntu/.openclaw/openclaw.json', 'r') as f:
            config = json.load(f)
        openclaw_token = config['channels']['telegram']['botToken']
    except Exception as e:
        print(f"❌ FAIL: Could not read OpenClaw config: {e}")
        return False
    
    tokens = {
        'Swarm Bot (@Swarm26_bot)': swarm_token,
        'Hermes Bot (@Hermesonly26_bot)': hermes_token,
        'OpenClaw Bot (@hermesagent26_bot)': openclaw_token
    }
    
    # Check for None values
    for name, token in tokens.items():
        if not token:
            print(f"❌ FAIL: {name} token is missing")
            return False
    
    # Check for duplicates
    token_values = list(tokens.values())
    if len(token_values) != len(set(token_values)):
        print("❌ FAIL: Some bots have duplicate tokens")
        for name, token in tokens.items():
            print(f"   {name}: {token}")
        return False
    
    print("✅ PASS: All three bots have distinct tokens:")
    for name, token in tokens.items():
        print(f"   {name}: {token[:15]}...{token[-10:]}")
    return True

if __name__ == "__main__":
    print("🧪 Testing Swarm Bot Readiness for Telegram Communication")
    print("=" * 60)
    
    test1_pass = test_swarm_bot_token()
    print()
    test2_pass = test_bot_distinction()
    
    print()
    if test1_pass and test2_pass:
        print("🎉 ALL TESTS PASSED - Swarm bot is ready for Telegram communication!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED - Swarm bot may not be ready for Telegram communication")
        sys.exit(1)