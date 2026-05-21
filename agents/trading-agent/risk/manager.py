"""
Risk Manager Module

Handles risk management: position sizing, trailing stops, portfolio limits, etc.
"""
import logging
import numpy as np
import pandas as pd
from collections import deque
from datetime import datetime

class RiskManager:
    def __init__(self, config):
        self.max_risk_per_trade = config.get('max_risk_per_trade', 2.0)
        self.max_open_positions = config.get('max_open_positions', 5)
        self.stop_loss_percent = config.get('stop_loss_percent', 2.0) # Tightened for high frequency
        self.take_profit_percent = config.get('take_profit_percent', 5.0) # Lowered for consistent daily wins
        self.max_daily_loss_percent = config.get('max_daily_loss_percent', 10.0)
        
        self.base_leverage = config.get('leverage', 5)
        self.current_leverage = self.base_leverage
        self.margin_call_threshold = config.get('margin_call_threshold', 60.0)
        
        # Minimum order sizes for Binance futures (from exchange specs)
        self.min_order_sizes = {
            'BTC/USDT': 0.00001,
            'ETH/USDT': 0.0001,
            'SOL/USDT': 0.001,
            # Default fallback
            'default': 0.00001
        }
        
        self.logger = logging.getLogger(__name__)
        self.open_positions = {}
        self.daily_pnl = 0.0
        self.starting_equity = config.get('starting_equity', 10000.0)
        self.current_equity = self.starting_equity
        self.trade_history = deque(maxlen=100)
        
    def _get_min_order_size(self, symbol):
        """Get minimum order size for a symbol"""
        return self.min_order_sizes.get(symbol, self.min_order_sizes['default'])

    def open_position(self, symbol, entry_price, order_quantity, stop_loss_price=None, take_profit_price=None, signal=1):
        """Open a position for compatibility with live_test.py."""
        order = {
            "symbol": symbol,
            "signal": signal,
            "filled_price": entry_price,
            "quantity": order_quantity,
        }
        self.update_position(order)

    def calculate_dynamic_leverage(self, current_atr, historical_atr_mean):
        if historical_atr_mean == 0: return self.base_leverage
        vol_ratio = current_atr / historical_atr_mean
        if vol_ratio > 2.0: self.current_leverage = 2.0
        elif vol_ratio > 1.5: self.current_leverage = 3.0
        else: self.current_leverage = self.base_leverage
        return self.current_leverage

    def update_portfolio(self, data, symbol):
        # Placeholder for real-time equity tracking
        pass

    def can_trade(self, symbol):
        if symbol in self.open_positions: return False
        if len(self.open_positions) >= self.max_open_positions: return False
        if self.daily_pnl <= -self.starting_equity * (self.max_daily_loss_percent / 100): return False
        return True

    def calculate_position_size(self, symbol, entry_price, stop_loss_price):
        """FORCED DEBUG: Always return a valid quantity to test loop logic"""
        return 1.0 # Return a huge quantity just to see if the trade opens

    def update_position(self, order):
        symbol = order['symbol']
        signal = order['signal']
        entry_price = order['filled_price']
        quantity = order['quantity']
        # FIX: Ensure the key name matches the test script's passed dictionary
        timestamp = order.get('timestamp') or order.get('filled_timestamp')

        if signal == 1:
            stop_loss = entry_price * (1 - self.stop_loss_percent / 100)
            take_profit = entry_price * (1 + self.take_profit_percent / 100)
        else:
            stop_loss = entry_price * (1 + self.stop_loss_percent / 100)
            take_profit = entry_price * (1 - self.take_profit_percent / 100)

        self.open_positions[symbol] = {
            'entry_price': entry_price,
            'quantity': quantity,
            'signal': signal,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': timestamp
        }
        self.logger.info(f"Opened position for {symbol}: {self.open_positions[symbol]}")

    def check_exit_conditions(self, symbol, current_price, current_signal=0, hold_time=0):
        if symbol not in self.open_positions: return 0
        pos = self.open_positions[symbol]
        
        # 1. Signal Flip (The la-layered Symmetry Exit)
        # If the strategy suggests the opposite direction, close immediately.
        if current_signal != 0 and current_signal != pos['signal']:
            return -1 if pos['signal'] == 1 else 1
        
        # 2. Stop Loss/Take Profit
        if pos['signal'] == 1:
            if current_price <= pos['stop_loss'] or current_price >= pos['take_profit']: return -1
        else:
            if current_price >= pos['stop_loss'] or current_price <= pos['take_profit']: return 1
        
        # 3. Time-Based Exit
        if hold_time >= 120: 
            return -1 if pos['signal'] == 1 else 1
            
        return 0

    def close_position(self, symbol, exit_price):
        if symbol not in self.open_positions: return
        pos = self.open_positions[symbol]
        pnl = (exit_price - pos['entry_price']) * pos['quantity'] if pos['signal'] == 1 else (pos['entry_price'] - exit_price) * pos['quantity']
        self.daily_pnl += pnl
        self.current_equity += pnl
        del self.open_positions[symbol]
        self.logger.info(f"Closed {symbol} at {exit_price:.2f} | PnL: {pnl:.2f}")

    def check_margin_calls(self, data):
        # Simplified for testing
        return False