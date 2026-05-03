#!/usr/bin/env python3
"""
Swarm Telegram Bot for inter-agent communication.
Listens for commands to send and retrieve messages between agents.
"""

import logging
import json
import os
import re
from datetime import datetime
from typing import Optional, Dict, Any

from dotenv import load_dotenv
load_dotenv()

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

logger = logging.getLogger(__name__)

class SwarmTelegramBot:
    def __init__(self):
        self.logger = logger
        self.messages_dir = "/tmp/swarm_bot_messages"
        self.ensure_messages_dir()
        
        # Bot token from environment
        self.token = os.getenv('SWARM_BOT_TOKEN')
        if not self.token:
            raise ValueError("SWARM_BOT_TOKEN environment variable not set")
        
        # Authorized users (agent usernames or IDs) - can be extended
        self.authorized_users = self._get_authorized_users()
        
        self.application = None
        self.running = False
    
    def ensure_messages_dir(self):
        """Ensure the messages directory exists"""
        os.makedirs(self.messages_dir, exist_ok=True)
    
    def _get_authorized_users(self) -> list:
        """Get authorized users from environment variable"""
        users_env = os.getenv('SWARM_AUTHORIZED_USERS', '')
        if users_env:
            return [u.strip() for u in users_env.split(',') if u.strip()]
        else:
            # Default to empty - must be configured
            return []
    
    def is_authorized(self, user_username: str, user_id: int) -> bool:
        """Check if user is authorized to use the bot"""
        if not self.authorized_users:
            # If no authorized users configured, allow all (for testing)
            return True
        
        # Check by username (without @) or by user ID
        if user_username and user_username.lower() in [u.lower().lstrip('@') for u in self.authorized_users]:
            return True
        if str(user_id) in self.authorized_users:
            return True
        return False
    
    def save_message(self, to_agent: str, from_agent: str, message: str):
        """Save a message for an agent"""
        try:
            # Sanitize agent name for filename
            safe_to_agent = re.sub(r'[^\w\-_.]', '_', to_agent)
            message_file = os.path.join(self.messages_dir, f"{safe_to_agent}.json")
            
            # Load existing messages
            messages = []
            if os.path.exists(message_file):
                with open(message_file, 'r') as f:
                    try:
                        messages = json.load(f)
                    except json.JSONDecodeError:
                        messages = []
            
            # Add new message
            message_obj = {
                "from": from_agent,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            messages.append(message_obj)
            
            # Keep only last 100 messages per agent
            if len(messages) > 100:
                messages = messages[-100:]
            
            # Save back
            with open(message_file, 'w') as f:
                json.dump(messages, f, indent=2)
            
            self.logger.info(f"Saved message for {to_agent} from {from_agent}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save message: {e}")
            return False
    
    def get_messages(self, agent_name: str) -> list:
        """Retrieve and clear messages for an agent"""
        try:
            safe_agent = re.sub(r'[^\w\-_.]', '_', agent_name)
            message_file = os.path.join(self.messages_dir, f"{safe_agent}.json")
            
            if not os.path.exists(message_file):
                return []
            
            with open(message_file, 'r') as f:
                try:
                    messages = json.load(f)
                except json.JSONDecodeError:
                    messages = []
            
            # Clear the file after reading
            with open(message_file, 'w') as f:
                json.dump([], f)
            
            return messages
        except Exception as e:
            self.logger.error(f"Failed to get messages: {e}")
            return []
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        if not self.is_authorized(user.username or "", user.id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
        
        await update.message.reply_text(
            "🤖 Swarm Telegram Bot\n\n"
            "Commands:\n"
            "/send <agent_name> <message> - Send a message to another agent\n"
            "/getmessages - Retrieve your messages\n"
            "/help - Show this help"
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user = update.effective_user
        if not self.is_authorized(user.username or "", user.id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
        
        await update.message.reply_text(
            "🤖 Swarm Telegram Bot Help\n\n"
            "Send messages between agents:\n"
            "/send <agent_name> <message> - Send a message to another agent\n"
            "/getmessages - Retrieve messages sent to you\n\n"
            "Example:\n"
            "/send trading-agent Buy signal detected on BTC"
        )
    
    async def send_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /send command"""
        user = update.effective_user
        if not self.is_authorized(user.username or "", user.id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
        
        # Parse command: /send <agent_name> <message>
        text = update.message.text
        match = re.match(r'^/send\s+(\S+)\s+(.+)$', text, re.IGNORECASE)
        if not match:
            await update.message.reply_text(
                "❌ Invalid format. Use: /send <agent_name> <message>"
            )
            return
        
        to_agent = match.group(1)
        message = match.group(2)
        from_agent = user.username or f"user_{user.id}"
        
        if self.save_message(to_agent, from_agent, message):
            await update.message.reply_text(
                f"✅ Message sent to {to_agent}"
            )
        else:
            await update.message.reply_text(
                "❌ Failed to send message"
            )
    
    async def getmessages_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /getmessages command"""
        user = update.effective_user
        if not self.is_authorized(user.username or "", user.id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
        
        agent_name = user.username or f"user_{user.id}"
        messages = self.get_messages(agent_name)
        
        if not messages:
            await update.message.reply_text(
                "📭 No messages for you."
            )
            return
        
        # Format messages
        msg_text = f"📬 You have {len(messages)} message(s):\n\n"
        for i, msg in enumerate(messages, 1):
            msg_text += (
                f"{i}. From: {msg['from']}\n"
                f"   Time: {msg['timestamp']}\n"
                f"   Message: {msg['message']}\n\n"
            )
        
        await update.message.reply_text(msg_text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle any other messages (for logging or future use)"""
        # We can log or ignore non-command messages
        user = update.effective_user
        if update.message and update.message.text and not update.message.text.startswith('/'):
            self.logger.info(
                f"Non-command message from {user.username or user.id}: {update.message.text[:50]}..."
            )
    
    def run(self):
        """Start the bot"""
        if not self.token:
            self.logger.error("Swarm Telegram bot token not configured")
            return False
        
        try:
            self.logger.info("Starting Swarm Telegram Bot...")
            
            # Create the Application
            self.application = Application.builder().token(self.token).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("send", self.send_command))
            self.application.add_handler(CommandHandler("getmessages", self.getmessages_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Start the Bot
            self.application.run_polling(allowed_updates=["message", "command"])
            
        except Exception as e:
            self.logger.error(f"Error in Swarm Telegram bot: {e}", exc_info=True)
            return False
        return True

def main():
    """Main function to run the Swarm Telegram bot"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/home/yahwehatwork/human-ai/logs/swarm_telegram_bot.log'),
            logging.StreamHandler()
        ]
    )
    
    try:
        bot = SwarmTelegramBot()
        bot.run()
    except Exception as e:
        logger.error(f"Fatal error in Swarm Telegram bot: {e}", exc_info=True)

if __name__ == "__main__":
    main()