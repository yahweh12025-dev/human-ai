#!/usr/bin/env python3
"""
Custom script to export Telegram chats using Telethon
Exports messages from specified chats to text files
"""

import os
import asyncio
from telethon import TelegramClient
from telethon.tl.types import PeerUser, PeerChat, PeerChannel
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/home/ubuntu/human-ai/infrastructure/configs/.env')

# Telegram API credentials
api_id = int(os.getenv('TELEGRAM_API_ID'))
api_hash = os.getenv('TELEGRAM_API_HASH')
phone = os.getenv('TELEGRAM_PHONE')

# Create exports directory
exports_dir = '/home/ubuntu/human-ai/docs/telegram_exports'
os.makedirs(exports_dir, exist_ok=True)

async def export_chat(client, entity, chat_name):
    """Export messages from a chat/entity to a text file"""
    print(f"Exporting chat: {chat_name}")
    
    filename = os.path.join(exports_dir, f"{chat_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Telegram Chat Export: {chat_name}\n")
        f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*50 + "\n\n")
        
        message_count = 0
        async for message in client.iter_messages(entity, limit=1000):  # Limit to 1000 messages for safety
            if message.text:
                sender = await message.get_sender()
                sender_name = getattr(sender, 'first_name', 'Unknown') if sender else 'Unknown'
                if hasattr(sender, 'last_name') and sender.last_name:
                    sender_name += f" {sender.last_name}"
                if hasattr(sender, 'username') and sender.username:
                    sender_name += f" (@{sender.username})"
                
                timestamp = message.date.strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] {sender_name}: {message.text}\n\n")
                message_count += 1
                
        f.write(f"\nTotal messages exported: {message_count}\n")
    
    print(f"Exported {message_count} messages to {filename}")
    return filename

async def main():
    # Create client
    client = TelegramClient('session_name', api_id, api_hash)
    
    # Start client
    await client.start(phone)
    print("Client connected successfully!")
    
    # Get me to verify
    me = await client.get_me()
    print(f"Logged in as: {me.first_name} (@{me.username})")
    
    # Define chats to export (we'll look for Hermes and OpenClaw bot chats)
    target_chats = []
    
    # Get dialogs
    print("Fetching dialogs...")
    async for dialog in client.iter_dialogs():
        # Look for chats that might contain bot names
        if dialog.name:
            name_lower = dialog.name.lower()
            if any(keyword in name_lower for keyword in ['hermes', 'openclaw', 'swarm', 'bot']):
                target_chats.append((dialog.entity, dialog.name))
                print(f"Found target chat: {dialog.name}")
    
    # If no specific bot chats found, export recent chats
    if not target_chats:
        print("No specific bot chats found. Exporting recent chats...")
        count = 0
        async for dialog in client.iter_dialogs(limit=10):  # Export first 10 chats
            if dialog.name and not dialog.is_user:  # Skip personal chats for now
                target_chats.append((dialog.entity, dialog.name))
                count += 1
                if count >= 5:  # Limit to 5 chats
                    break
    
    # Export each target chat
    exported_files = []
    for entity, chat_name in target_chats:
        try:
            filename = await export_chat(client, entity, chat_name)
            exported_files.append(filename)
        except Exception as e:
            print(f"Error exporting chat '{chat_name}': {e}")
    
    # Disconnect
    await client.disconnect()
    print(f"\nExport complete! Exported {len(exported_files)} chat(s).")
    print(f"Files saved in: {exports_dir}")

if __name__ == '__main__':
    asyncio.run(main())