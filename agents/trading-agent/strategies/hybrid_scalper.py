"""
Hybrid Trading Strategy: Trend + Grid
Combines SMA Crossover for trending markets and Adaptive Grid for ranging markets.
"""
import pandas as pd
import numpy as np
import logging

class HybridScalpingStrategy:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Adaptive SMA parameters
        self.base_fast = config.get('fast_period', 10)
        self.base_slow = config.get('slow_period', 30)
        self.tf_overrides = {
            1:  {'fast': 5,  'slow': 15},
            5:  {'fast': 8,  'slow': 20},
            15: {'fast': 10, 'slow': 30},
            30: {'fast': 12, 'slow': 35},
            60: {'fast': 15, 'slow': 45},
            120:{'fast': 20, 'slow': 60},
            240:{'fast': 25, 'slow': 80},
        }
        
        # Grid parameters
        self.grid_spacing = config.get('grid_size_percent', 0.3)
        self.num_grids = config.get('num_grids', 20)
        
        # Regime thresholds
        self.adx_threshold = config.get('adx_threshold', 25)

    def get_regime(self, adx_value):
        if adx_value > self.adx_threshold:
            return "TRENDING"
        return "RANGING"

    def generate_signal(self, data, timeframe_mins=60, adx_value=None, trend_data=None):
        """
        Hybrid decision engine:
        1. Detect regime via ADX
        2. If TRENDING -> Use SMA Crossover
        3. If RANGING -> Use Grid Mean Reversion
        """
        if len(data) < 50: return 0
        
        regime = "RANGING"
        if adx_value and adx_value > self.adx_threshold:
            regime = "TRENDING"
        
        # Base Indicators
        periods = self.tf_overrides.get(timeframe_mins, {'fast': self.base_fast, 'slow': self.base_slow})
        df = data.copy()
        df['sma_fast'] = df['Close'].rolling(window=periods['fast']).mean()
        df['sma_slow'] = df['Close'].rolling(window=periods['slow']).mean()
        
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        
        if regime == "TRENDING":
            # SMA Crossover logic
            last = df.iloc[-1]
            prev = df.iloc[-2]
            if prev['sma_fast'] <= prev['sma_slow'] and last['sma_fast'] > last['sma_slow']:
                return 1
            elif prev['sma_fast'] >= prev['sma_slow'] and last['sma_fast'] < last['sma_slow']:
                return -1
            return 0
            
        else: # RANGING
            # Grid/Mean Reversion logic
            # In ranging, we want to buy low (near lower grid) and sell high (near upper grid)
            # Simplified: if price is near a level, return signal
            # For backtest simulation, we return a 'grid_buy' or 'grid_sell' concept
            # We'll map these to 1 and -1 for the agent
            
            # Adaptive grid center
            grid_center = df['Close'].rolling(window=20).mean().iloc[-1]
            dist_from_center = (current_price - grid_center) / grid_center
            
            if dist_from_center < -0.005: # Price is low relative to mean
                return 1
            elif dist_from_center > 0.005: # Price is high relative to mean
                return -1
            return 0
