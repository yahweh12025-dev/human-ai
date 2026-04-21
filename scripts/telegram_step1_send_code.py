#!/usr/bin/env python3
"""
Step 1: Send code request for Telegram login
"""

import os
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv('/home/ubuntu/human-ai/infrastructure/configs/.env')

api_id = int(os.getenv('TELEGRAM_API_ID'))
api_hash = os.getenv('TELEGRAM_API_HASH')
phone = os.getenv('TELEGRAM_PHONE')

async def main():
    client = TelegramClient('/home/ubuntu/human-ai/telegram_export_session', api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print("Sending code request...")
        await client.send_code_request(phone)
        print("CODE_SENT: Please check your Telegram app for the login code and provide it.")
    else:
        print("Already authorized.")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())