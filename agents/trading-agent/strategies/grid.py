"""
Grid Trading Strategy
Places buy and sell orders at predefined intervals above and below a set price.
Improved version with dynamic grid adjustment and profit taking.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional

class GridStrategy:
    def __init__(self, config):
        """Initialize the grid strategy."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Grid parameters
        self.grid_size_percent = config.get('grid_size_percent', 0.5)  # 0.5% per grid
        self.num_grids = config.get('num_grids', 10)  # Number of grids above and below
        self.base_price = config.get('base_price', None)  # If None, use current price
        self.total_investment = config.get('total_investment', 1000)  # USDT to allocate
        self.symbol = config.get('symbol', '')  # Current symbol being traded
        self.leverage = config.get('leverage', 3)  # Leverage for grid trading
        self.profit_target_percent = config.get('profit_target_percent', 0.2)  # 0.2% profit target per grid
        self.stop_loss_percent = config.get('stop_loss_percent', 2.0)  # 2% stop loss
        
        # State tracking
        self.grid_levels = []  # List of price levels
        self.buy_orders = {}   # price -> quantity
        self.sell_orders = {}  # price -> quantity
        self.filled_buys = []  # List of filled buy prices
        self.filled_sells = [] # List of filled sell prices
        self.active_buys = {}  # price -> quantity (active buy orders)
        self.active_sells = {} # price -> quantity (active sell orders)
        self.position_size = 0 # Current position size
        self.entry_price = 0   # Average entry price
        
        self.logger.info(f"Grid strategy initialized: {self.num_grids} grids, {self.grid_size_percent}% size, leverage {self.leverage}x")
    
    def initialize_grid(self, current_price: float):
        """Initialize grid levels based on current price."""
        if self.base_price is None:
            self.base_price = current_price
        
        # Calculate grid prices
        self.grid_levels = []
        for i in range(-self.num_grids, self.num_grids + 1):
            price = self.base_price * (1 + i * self.grid_size_percent / 100)
            self.grid_levels.append(round(price, 8))
        
        self.grid_levels.sort()
        self.logger.info(f"Grid initialized with base price {self.base_price}. Levels: {self.grid_levels[:5]}...{self.grid_levels[-5:]}")
        
        # Distribute investment across grids
        # We'll place orders at each grid level
        grids_to_trade = len(self.grid_levels)
        amount_per_grid = self.total_investment / grids_to_trade if grids_to_trade > 0 else 0
        
        # For each grid level, calculate quantity based on leverage
        for price in self.grid_levels:
            # Calculate quantity for this grid level
            # Using leverage: quantity = (investment_per_grid * leverage) / price
            quantity = (amount_per_grid * self.leverage) / price
            quantity = round(quantity, 6)  # Round to reasonable precision
            
            # Initialize order tracking
            self.active_buys[price] = quantity
            self.active_sells[price] = quantity
            
        self.logger.info(f"Initialized {len(self.grid_levels)} grid levels with {quantity} quantity per level")
    
    def calculate_indicators(self, data):
        """Return data for compatibility - no additional indicators needed for basic grid."""
        # We could add volatility indicators for dynamic grid adjustment here
        return data
    
    def generate_signal(self, data):
        """Generate signal based on grid strategy with dynamic grid adjustment."""
        if len(data) < 1:
            return 0
        
        current_price = data['Close'].iloc[-1]
        
        # Initialize grid if not done
        if not self.grid_levels:
            self.initialize_grid(current_price)
        
        # Check if we need to adjust grid based on significant price movement
        price_change_percent = abs((current_price - self.base_price) / self.base_price * 100)
        if price_change_percent > (self.num_grids * self.grid_size_percent * 0.8):  # If price moved 80% of grid range
            self.logger.info(f"Price moved {price_change_percent:.2f}% from base, reinitializing grid")
            self.initialize_grid(current_price)
        
        # Generate trading signals based on grid interactions
        signal = 0
        
        # Check if price crossed any grid levels from previous close
        if len(data) >= 2:
            prev_price = data['Close'].iloc[-2]
            
            # Check for upward crosses (sell signals)
            for level in self.grid_levels:
                if prev_price < level <= current_price:
                    # Price crossed above this level - consider selling
                    signal = -1
                    break
            
            # Check for downward crosses (buy signals)
            for level in reversed(self.grid_levels):  # Check from high to low
                if prev_price > level >= current_price:
                    # Price crossed below this level - consider buying
                    signal = 1
                    break
        
        # If no clear cross, use mean reversion within grid
        if signal == 0:
            # Find where price is in the grid
            if current_price < self.grid_levels[0]:
                # Below grid - buy signal
                signal = 1
            elif current_price > self.grid_levels[-1]:
                # Above grid - sell signal
                signal = -1
            else:
                # Within grid - look for mean reversion opportunities
                # Find nearest grid levels
                above_levels = [level for level in self.grid_levels if level > current_price]
                below_levels = [level for level in self.grid_levels if level < current_price]
                
                if above_levels and below_levels:
                    nearest_above = min(above_levels)
                    nearest_below = max(below_levels)
                    
                    # Calculate distance to nearest levels as percentage of grid spacing
                    grid_spacing = self.base_price * (self.grid_size_percent / 100)
                    dist_to_above = (nearest_above - current_price) / grid_spacing
                    dist_to_below = (current_price - nearest_below) / grid_spacing
                    
                    # If closer to upper level, slight buy bias (mean reversion down)
                    # If closer to lower level, slight sell bias (mean reversion up)
                    if dist_to_above < dist_to_below:
                        signal = 1  # Buy bias
                    else:
                        signal = -1  # Sell bias
                    # Scale signal by confidence (how far we are from center)
                    confidence = abs(dist_to_above - dist_to_below) / (self.num_grids * 2)
                    if confidence < 0.3:  # Not confident enough
                        signal = 0
        
        return signal

# For backward compatibility with existing agent interface
def generate_signal(data, config=None):
    """Function interface for compatibility."""
    if config is None:
        config = {}
    strategy = GridStrategy(config)
    return strategy.generate_signal(data)
