"""
Grid Trading Strategy - Scalping Optimized
High-frequency grid placement with volatility-based spacing and trend-following filters.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional

class GridStrategy:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Base parameters
        self.num_grids = config.get('num_grids', 20)  # Increased for scalping density
        self.base_leverage = config.get('leverage', 5)
        self.total_investment = config.get('total_investment', 1000.0)
        
        # Adaptive Parameters
        self.base_grid_spacing = config.get('grid_size_percent', 0.3)  # Tighter spacing for scalping
        self.atr_multiplier = config.get('atr_multiplier', 1.5) # Spacing based on ATR
        
        # State tracking
        self.grid_levels = []
        self.base_price = None
        self.atr_val = 0.0
        self.logger.info(f"Scalping Grid initialized: {self.num_grids} levels, {self.base_grid_spacing}% base spacing")

    def _calculate_adaptive_spacing(self, current_price, atr):
        """Calculates spacing based on volatility to avoid grid exhaustion."""
        if atr == 0:
            return current_price * (self.base_grid_spacing / 100)
        # Scale spacing: higher volatility = wider levels; lower volatility = tighter levels
        # We cap the scale to keep it within a reasonable range for scalping
        vol_factor = max(0.5, min(3.0, atr / (current_price * 0.01))) 
        return atr * self.atr_multiplier * vol_factor

    def initialize_grid(self, current_price, atr):
        """Initialize adaptive grid levels."""
        self.base_price = current_price
        self.atr_val = atr
        
        spacing = self._calculate_adaptive_spacing(current_price, atr)
        self.logger.info(f"Adaptive spacing calculated: {spacing:.4f} (ATR: {atr:.4f})")
        
        self.grid_levels = []
        # Create symmetric grid around current price
        half_grids = self.num_grids // 2
        for i in range(-half_grids, half_grids + 1):
            level = current_price + (i * spacing)
            self.grid_levels.append(round(level, 8))
        
        self.grid_levels.sort()
        self.logger.info(f"Scalping grid initialized at {current_price}. Levels: {len(self.grid_levels)}")

    def generate_signal(self, data, trend_data=None):
        """
        Generate high-frequency scalping signals.
        Includes Trend Filtering to prevent trading against momentum.
        """
        if len(data) < 30: return 0
        
        current_price = data['Close'].iloc[-1]
        
        # 1. Initialize or Re-center Grid
        if not self.grid_levels or abs(current_price - self.base_price) / self.base_price > 0.05:
            # Recalculate ATR for adaptive spacing
            high_low = data['High'] - data['Low']
            atr = high_low.rolling(window=14).mean().iloc[-1]
            self.initialize_grid(current_price, atr)
            return 0 # Wait for next candle to avoid immediate reentry

        # 2. Multi-Timeframe Trend Filter (to avoid 'fighting the trend')
        is_bullish_trend = True
        if trend_data is not None:
            # Use 4h SMA to confirm macro trend
            macro_sma = trend_data['Close'].rolling(window=20).mean().iloc[-1]
            is_bullish_trend = current_price > macro_sma

        # 3. Scalping Signal Logic (Mean Reversion within Grid)
        signal = 0
        
        # Find current position in grid
        # Buy if price drops below a level, Sell if it rises above
        lower_levels = [l for l in self.grid_levels if l < current_price]
        upper_levels = [l for l in self.grid_levels if l > current_price]
        
        if lower_levels:
            nearest_below = max(lower_levels)
            # If price is bouncing off a lower level in a bullish trend
            if is_bullish_trend and current_price > nearest_below:
                signal = 1
        
        if upper_levels:
            nearest_above = min(upper_levels)
            # If price is bouncing off an upper level in a bearish trend
            if not is_bullish_trend and current_price < nearest_above:
                signal = -1

        return signal

# Legacy support
def generate_signal(data, config=None):
    if config is None: config = {}
    strategy = GridStrategy(config)
    return strategy.generate_signal(data)
