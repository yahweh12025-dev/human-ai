#!/usr/bin/env python3
"""
Telegram Signal Listener using Bot API (python-telegram-bot)
Listens to Telegram channels (where the bot is an admin) for trading signals and writes them to the trading bridge
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
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logger = logging.getLogger(__name__)

class TelegramSignalListenerBot:
    def __init__(self):
        self.logger = logger
        self.command_file = "/tmp/trading-bridge/command.json"
        self.ensure_bridge_dir()
        
        # Bot token from environment
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        
        # Channels to monitor (can be usernames or IDs)
        self.channels_to_monitor = self._get_channels_to_monitor()
        
        # Signal parsing patterns (same as before)
        self.signal_patterns = [
            # Pattern 1: BUY BTC/USDT @ 76000 TP: 78000 SL: 75000
            r'(?i)(BUY|SELL|LONG|SHORT)\s+([A-Z]+/[A-Z]+)\s*[@:]?\s*([\d.]+)\s*(?:TP|TARGET|TP1):?\s*([\d.]+)\s*(?:SL|STOP|STOPLOSS):?\s*([\d.]+)',
            
            # Pattern 2: BTC/USDT LONG 76000 → TP1: 76500 TP2: 77000 SL: 75500
            r'(?i)([A-Z]+/[A-Z]+)\s+(BUY|SELL|LONG|SHORT)\s+([\d.]+)\s*(?:→|->|ARROW)\s*(?:TP|TARGET|TP1):?\s*([\d.]+)\s*(?:TP2|TARGET2):?\s*([\d.]+)\s*(?:SL|STOP|STOPLOSS):?\s*([\d.]+)',
            
            # Pattern 3: 🚀 BTC/USDT BUY SIGNAL 🚀\nEntry: 76000\nTarget 1: 76500\nTarget 2: 77000\nStop Loss: 75500
            r'(?i)(?:🚀|BELL|SIGNAL).*?([A-Z]+/[A-Z]+).*?(BUY|SELL|LONG|SHORT).*?Entry:?\s*([\d.]+).*?(?:Target\s*1|TP1):?\s*([\d.]+).*?(?:Target\s*2|TP2):?\s*([\d.]+).*?(?:Stop\s*Loss|SL):?\s*([\d.]+)',
        ]
        
        self.application = None
        self.running = False
        
    def ensure_bridge_dir(self):
        """Ensure the command directory exists"""
        os.makedirs(os.path.dirname(self.command_file), exist_ok=True)
        
    def _get_channels_to_monitor(self) -> list:
        """Get channels to monitor from environment variable"""
        channels_env = os.getenv('TELEGRAM_CHANNELS_TO_MONITOR', '')
        if channels_env:
            return [ch.strip() for ch in channels_env.split(',') if ch.strip()]
        else:
            # Default channels - can be overridden
            return ['EveningTrader', 'CryptoSignals', 'TradingView']
    
    def write_command(self, command: Dict[str, Any]):
        """Write a command to the bridge file"""
        self.ensure_bridge_dir()
        try:
            # Add timestamp if not present
            if 'timestamp' not in command:
                command['timestamp'] = datetime.now().isoformat()
                
            with open(self.command_file, 'w') as f:
                json.dump(command, f, indent=2)
            self.logger.info(f"Wrote command to bridge: {command}")
        except Exception as e:
            self.logger.error(f"Failed to write command: {e}")
    
    def parse_signal(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse trading signal from text"""
        if not text:
            return None
            
        self.logger.debug(f"Parsing signal text: {text[:100]}...")
        
        for i, pattern in enumerate(self.signal_patterns):
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                self.logger.info(f"Matched signal pattern {i+1}")
                try:
                    return self._extract_signal_from_match(match, i+1)
                except Exception as e:
                    self.logger.error(f"Error extracting signal from match: {e}")
                    continue
        
        self.logger.debug("No signal pattern matched")
        return None
    
    def _extract_signal_from_match(self, match: re.Match, pattern_num: int) -> Dict[str, Any]:
        """Extract signal data from regex match"""
        groups = match.groups()
        
        if pattern_num == 1:
            # Pattern: BUY BTC/USDT @ 76000 TP: 78000 SL: 75000
            action, symbol, entry, tp, sl = groups
            signal = 1 if action.upper() in ['BUY', 'LONG'] else -1
            
        elif pattern_num == 2:
            # Pattern: BTC/USDT LONG 76000 → TP1: 76500 TP2: 77000 SL: 75500
            symbol, action, entry, tp1, tp2, sl = groups
            signal = 1 if action.upper() in ['BUY', 'LONG'] else -1
            # Use TP1 as the primary target
            tp = tp1
            
        elif pattern_num == 3:
            # Pattern: 🚀 BTC/USDT BUY SIGNAL 🚀\nEntry: 76000\nTarget 1: 76500\nTarget 2: 77000\nStop Loss: 75500
            symbol, action, entry, tp1, tp2, sl = groups
            signal = 1 if action.upper() in ['BUY', 'LONG'] else -1
            # Use TP1 as the primary target
            tp = tp1
            
        else:
            raise ValueError(f"Unknown pattern number: {pattern_num}")
        
        # Validate and convert to appropriate types
        try:
            entry_price = float(entry)
            tp_price = float(tp)
            sl_price = float(sl)
            
            # Basic validation
            if entry_price <= 0 or tp_price <= 0 or sl_price <= 0:
                raise ValueError("Prices must be positive")
                
            # For long signals: TP > Entry > SL
            # For short signals: TP < Entry < SL
            if signal == 1:  # Long
                if not (tp_price > entry_price > sl_price):
                    self.logger.warning(f"Invalid long signal prices: Entry={entry_price}, TP={tp_price}, SL={sl_price}")
            else:  # Short
                if not (tp_price < entry_price < sl_price):
                    self.logger.warning(f"Invalid short signal prices: Entry={entry_price}, TP={tp_price}, SL={sl_price}")
                    
        except ValueError as e:
            self.logger.error(f"Invalid price values: {e}")
            raise
        
        command = {
            "action": "override",
            "symbol": symbol.upper(),
            "signal": signal,
            "entry_price": entry_price,
            "take_profit": tp_price,
            "stop_loss": sl_price,
            "timestamp": datetime.now().isoformat(),
            "source": "telegram_signal_bot",
            "raw_text": match.group(0)[:200]  # Store first 200 chars of original signal
        }
        
        return command
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        try:
            message = update.effective_message
            if not message or not message.text:
                return
            
            # Get the chat where the message was sent
            chat = update.effective_chat
            chat_title = getattr(chat, 'title', None)
            chat_username = getattr(chat, 'username', None)
            chat_id = chat.id
            
            # Check if this chat is in our monitored list
            # We'll check by username (without @) or by ID (as string)
            chat_identifier = None
            if chat_username:
                chat_identifier = chat_username.lower()
            # Also consider the chat ID as a string for private channels without username
            
            # Normalize monitored channels for comparison
            monitored_normalized = [ch.lower().lstrip('@') for ch in self.channels_to_monitor]
            
            # Check if current chat is in monitored list
            is_monitored = False
            if chat_identifier and chat_identifier in monitored_normalized:
                is_monitored = True
            # Also check by chat ID if we stored IDs (but we store usernames/names)
            # For simplicity, we'll also allow matching by chat title (case insensitive)
            chat_title_lower = chat_title.lower() if chat_title else ''
            if any(ch.lower() == chat_title_lower for ch in self.channels_to_monitor):
                is_monitored = True
            
            if not is_monitored:
                self.logger.debug(f"Message from unmonitored chat: {chat_title} (ID: {chat_id})")
                return
            
            self.logger.debug(f"Received message from {chat_title} (ID: {chat_id}): {message.text[:100]}...")
            
            # Parse the signal
            signal_command = self.parse_signal(message.text)
            if signal_command:
                # Add channel information
                signal_command['source_channel'] = chat_title or chat_username or str(chat_id)
                signal_command['message_id'] = message.message_id
                
                # Write to bridge
                self.write_command(signal_command)
                self.logger.info(f"Processed trading signal from {chat_title}")
            else:
                self.logger.debug("No trading signal detected in message")
                
        except Exception as e:
            self.logger.error(f"Error processing Telegram message: {e}", exc_info=True)
    
    def run(self):
        """Start the bot listener"""
        if not self.token:
            self.logger.error("Telegram bot token not configured")
            return False
        
        try:
            self.logger.info("Starting Telegram signal listener bot...")
            
            # Create the Application
            self.application = Application.builder().token(self.token).build()
            
            # Add handler for text messages (excluding commands)
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
            )
            
            # Start the Bot
            self.application.run_polling(allowed_updates=["message"])
            
        except Exception as e:
            self.logger.error(f"Error in Telegram listener bot: {e}", exc_info=True)
            return False
        return True

def main():
    """Main function to run the Telegram signal listener bot"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/home/yahwehatwork/human-ai/logs/telegram_signal_listener_bot.log'),
            logging.StreamHandler()
        ]
    )
    
    try:
        listener = TelegramSignalListenerBot()
        listener.run()
    except Exception as e:
        logger.error(f"Fatal error in Telegram signal listener bot: {e}", exc_info=True)

if __name__ == "__main__":
    main()