#!/usr/bin/env python3
"""
Telegram Signal Listener for Trading Agent Integration
Listens to Telegram channels for trading signals and writes them to the trading bridge
"""

import asyncio
import logging
import json
import os
import re
from datetime import datetime
from typing import Optional, Dict, Any
import asyncio

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Try to import telethon, fallback to basic HTTP if not available
try:
    from telethon import TelegramClient, events
    from telethon.tl.types import Channel, Chat
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    logging.warning("Telethon not available. Install with: pip install telethon")

logger = logging.getLogger(__name__)

class TelegramSignalListener:
    def __init__(self):
        self.logger = logger
        self.command_file = "/tmp/trading-bridge/command.json"
        self.ensure_bridge_dir()
        
        # Telegram configuration from environment
        self.api_id = os.getenv('TELEGRAM_API_ID')
        self.api_hash = os.getenv('TELEGRAM_API_HASH')
        self.phone_number = os.getenv('TELEGRAM_PHONE_NUMBER')
        self.session_name = os.getenv('TELEGRAM_SESSION_NAME', 'trading_signal_session')
        
        # Channels to monitor (can be usernames or IDs)
        self.channels_to_monitor = self._get_channels_to_monitor()
        
        # Signal parsing patterns
        self.signal_patterns = [
            # Pattern 1: BUY BTC/USDT @ 76000 TP: 78000 SL: 75000
            r'(?i)(BUY|SELL|LONG|SHORT)\s+([A-Z]+/[A-Z]+)\s*[@:]?\s*([\d.]+)\s*(?:TP|TARGET|TP1):?\s*([\d.]+)\s*(?:SL|STOP|STOPLOSS):?\s*([\d.]+)',
            
            # Pattern 2: BTC/USDT LONG 76000 → TP1: 76500 TP2: 77000 SL: 75500
            r'(?i)([A-Z]+/[A-Z]+)\s+(BUY|SELL|LONG|SHORT)\s+([\d.]+)\s*(?:→|->|ARROW)\s*(?:TP|TARGET|TP1):?\s*([\d.]+)\s*(?:TP2|TARGET2):?\s*([\d.]+)\s*(?:SL|STOP|STOPLOSS):?\s*([\d.]+)',
            
            # Pattern 3: 🚀 BTC/USDT BUY SIGNAL 🚀\nEntry: 76000\nTarget 1: 76500\nTarget 2: 77000\nStop Loss: 75500
            r'(?i)(?:🚀|BELL|SIGNAL).*?([A-Z]+/[A-Z]+).*?(BUY|SELL|LONG|SHORT).*?Entry:?\s*([\d.]+).*?(?:Target\s*1|TP1):?\s*([\d.]+).*?(?:Target\s*2|TP2):?\s*([\d.]+).*?(?:Stop\s*Loss|SL):?\s*([\d.]+)',
        ]
        
        self.client = None
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
        """Write a command to the bridge file (synchronous, locked)"""
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
            "source": "telegram_signal",
            "raw_text": match.group(0)[:200]  # Store first 200 chars of original signal
        }
        
        return command
    
    async def start_listening(self):
        """Start listening to Telegram channels"""
        if not TELETHON_AVAILABLE:
            self.logger.error("Telethon not available. Cannot start Telegram listener.")
            return False
            
        if not all([self.api_id, self.api_hash, self.phone_number]):
            self.logger.error("Telegram credentials not configured. Set TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE_NUMBER")
            return False
        
        try:
            self.logger.info("Starting Telegram signal listener...")
            
            # Create the client
            self.client = TelegramClient(
                self.session_name, 
                int(self.api_id), 
                self.api_hash
            )
            
            # Start the client
            await self.client.start(phone=self.phone_number)
            
            if not await self.client.is_user_authorized():
                self.logger.error("Telegram client not authorized. Please check your credentials.")
                return False
            
            self.logger.info("Telegram client authorized successfully")
            
            # Get the channels/entities to monitor
            channels = []
            for channel_identifier in self.channels_to_monitor:
                try:
                    self.logger.debug(f"Trying to get entity for: {repr(channel_identifier)}")
                    entity = await self.client.get_entity(channel_identifier)
                    channels.append(entity)
                    self.logger.info(f"Added channel to monitor: {getattr(entity, 'title', entity.id)}")
                except Exception as e:
                    self.logger.error(f"Could not find channel '{channel_identifier}': {e}")
            
            if not channels:
                self.logger.error("No valid channels to monitor")
                return False
            
            # Register event handler for new messages
            @self.client.on(events.NewMessage(chats=channels))
            async def handle_new_message(event):
                try:
                    message = event.message
                    if not message.text:
                        return
                    
                    self.logger.debug(f"Received message from {getattr(event.chat, 'title', 'unknown')}: {message.text[:100]}...")
                    
                    # Parse the signal
                    signal_command = self.parse_signal(message.text)
                    if signal_command:
                        # Add channel information
                        signal_command['source_channel'] = getattr(event.chat, 'title', str(event.chat.id))
                        signal_command['message_id'] = message.id
                        
                        # Write to bridge
                        self.write_command(signal_command)
                    else:
                        self.logger.debug("No trading signal detected in message")
                        
                except Exception as e:
                    self.logger.error(f"Error processing Telegram message: {e}")
            
            self.running = True
            self.logger.info("Telegram signal listener started. Waiting for messages...")
            
            # Keep the client running
            await self.client.run_until_disconnected()
            
        except Exception as e:
            self.logger.error(f"Error in Telegram listener: {e}")
            return False
        finally:
            self.running = False
            if self.client:
                await self.client.disconnect()
    
    def stop(self):
        """Stop the listener"""
        self.running = False
        if self.client:
            asyncio.create_task(self.client.disconnect())

def main():
    """Main function to run the Telegram signal listener"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/home/yahwehatwork/human-ai/logs/telegram_signal_listener.log'),
            logging.StreamHandler()
        ]
    )
    
    listener = TelegramSignalListener()
    
    try:
        # Run the listener
        asyncio.run(listener.start_listening())
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        listener.stop()
    except Exception as e:
        logger.error(f"Fatal error in Telegram signal listener: {e}")

if __name__ == "__main__":
    main()