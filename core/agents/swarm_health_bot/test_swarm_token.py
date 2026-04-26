#!/usr/bin/env python3
"""Quick test to verify the Swarm Health Bot loads the correct token."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/home/yahwehatwork/human-ai/.env")

# Check what token the Swarm Health Bot would use
swarm_token = os.getenv('SWARM_BOT_TOKEN')
openclaw_token = os.getenv('TELEGRAM_BOT_TOKEN')  # This is the Hermes bot token in human-ai/.env

print(f"SWARM_BOT_TOKEN: {swarm_token}")
print(f"TELEGRAM_BOT_TOKEN (Hermes bot in human-ai/.env): {openclaw_token}")

# Verify they are different
if swarm_token and openclaw_token and swarm_token != openclaw_token:
    print("✅ SUCCESS: Swarm Bot is configured to use its own distinct token")
    print(f"   Swarm Bot (@Swarm26_bot) token ends in: ...{swarm_token[-10:]}")
    print(f"   Hermes Bot (@Hermesonly26_bot) token ends in: ...{openclaw_token[-10:]}")
else:
    print("❌ ERROR: Tokens are missing or identical")

# Also verify the OpenClaw gateway's token is different (should be @hermesagent26_bot)
import json
with open('/home/ubuntu/.openclaw/openclaw.json', 'r') as f:
    openclaw_config = json.load(f)
openclaw_gateway_token = openclaw_config['channels']['telegram']['botToken']
print(f"OpenClaw Gateway Bot (@hermesagent26_bot) token: ...{openclaw_gateway_token[-10:]}")

# Verify all three are distinct
tokens = [swarm_token, openclaw_token, openclaw_gateway_token]
if len(set(tokens)) == 3 and all(tokens):
    print("✅ SUCCESS: All three bots have distinct tokens:")
    print(f"   1. Swarm Bot (@Swarm26_bot): ...{swarm_token[-10:]}")
    print(f"   2. Hermes Bot (@Hermesonly26_bot): ...{openclaw_token[-10:]}")
    print(f"   3. OpenClaw Bot (@hermesagent26_bot): ...{openclaw_gateway_token[-10:]}")
else:
    print("❌ ERROR: Some tokens are missing or duplicated")