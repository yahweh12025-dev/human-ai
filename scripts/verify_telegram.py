import os
import requests
from dotenv import load_dotenv

load_dotenv('/home/ubuntu/human-ai/.env')
token = os.getenv('TELEGRAM_BOT_TOKEN')

if not token:
    print("❌ Error: TELEGRAM_BOT_TOKEN not found in .env")
    exit(1)

url = f"https://api.telegram.org/bot{token}/getMe"
try:
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Telegram Bot Verified: @{data['result']['username']}")
    else:
        print(f"❌ Telegram API Error: {resp.status_code} - {resp.text}")
except Exception as e:
    print(f"❌ Connection Error: {e}")
