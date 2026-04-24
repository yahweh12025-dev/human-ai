"""
SMA Crossover Strategy - Scalping Optimized
Optimized for high-frequency trading with tighter parameters and reduced filters.
"""

import pandas as pd
import numpy as np
import logging

class SMACrossover:
    def __init__(self, config):
        # Base parameters - reduced for faster signals
        self.base_fast = config.get('fast_period', 5)      # Was 10
        self.base_slow = config.get('slow_period', 15)     # Was 30
        
        # Timeframe overrides - more aggressive for scalping
        self.tf_overrides = {
            1:  {'fast': 3,  'slow': 8},    # 1m chart
            5:  {'fast': 5,  'slow': 12},   # 5m chart  
            15: {'fast': 8,  'slow': 20},   # 15m chart
            30: {'fast': 10, 'slow': 25},   # 30m chart
            60: {'fast': 12, 'slow': 30},   # 1h chart
            120:{'fast': 15, 'slow': 40},   # 2h chart
            240:{'fast': 20, 'slow': 50},   # 4h chart
        }
        
        # RSI parameters - less extreme for more signals
        self.rsi_period = config.get('rsi_period', 10)     # Was 14
        self.rsi_overbought = config.get('rsi_overbought', 75)  # Was 70
        self.rsi_oversold = config.get('rsi_oversold', 25)    # Was 30
        self.volume_threshold = config.get('volume_threshold', 1.2)  # Was 1.5
        self.adx_threshold = config.get('adx_threshold', 20)  # Was 25 - lower to catch more trends
        self.logger = logging.getLogger(__name__)

    def calculate_indicators(self, data, timeframe_mins=60):
        df = data.copy()
        periods = self.tf_overrides.get(timeframe_mins, {'fast': self.base_fast, 'slow': self.base_slow})
        
        df['sma_fast'] = df['Close'].rolling(window=periods['fast']).mean()
        df['sma_slow'] = df['Close'].rolling(window=periods['slow']).mean()

        # RSI Calculation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ADX Calculation (Simplified)
        df['tr'] = np.maximum(df['High'] - df['Low'], 
                             np.maximum(abs(df['High'] - df['Close'].shift(1)), 
                                      abs(df['Low'] - df['Close'].shift(1))))
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        # Directional Movement
        df['up_move'] = df['High'] - df['High'].shift(1)
        df['down_move'] = df['Low'].shift(1) - df['Low']
        
        df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
        df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
        
        df['plus_di'] = 100 * (df['plus_dm'].rolling(window=14).mean() / df['atr'])
        df['minus_di'] = 100 * (df['minus_dm'].rolling(window=14).mean() / df['atr'])
        
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].rolling(window=14).mean()
        
        df['volume_avg'] = df['Volume'].rolling(window=20).mean()
        return df

    def generate_signal(self, data, timeframe_mins=60, trend_data=None):
        if len(data) < 30: return 0  # Reduced from 80 for faster startup

        df = self.calculate_indicators(data, timeframe_mins)
        last = df.iloc[-1]
        prev = df.iloc[-2]

        # 1. ADX Regime Filter - slightly relaxed
        if last['adx'] < self.adx_threshold:
            return 0

        # 2. Volume Confirmation - relaxed
        if last['Volume'] <= (last['volume_avg'] * self.volume_threshold):
            return 0

        # 3. Multi-Timeframe Trend Filter
        if trend_data is not None:
            tf_high_sma = trend_data['Close'].rolling(window=20).mean().iloc[-1]
            current_price_high = trend_data['Close'].iloc[-1]
            trend_bullish = current_price_high > tf_high_sma
            
            signal = 0
            if prev['sma_fast'] <= prev['sma_slow'] and last['sma_fast'] > last['sma_slow']:
                if last['rsi'] < self.rsi_overbought and trend_bullish:
                    signal = 1
            elif prev['sma_fast'] >= prev['sma_slow'] and last['sma_fast'] < last['sma_slow']:
                if last['rsi'] > self.rsi_oversold and not trend_bullish:
                    signal = -1
            return signal
        else:
            signal = 0
            if prev['sma_fast'] <= prev['sma_slow'] and last['sma_fast'] > last['sma_slow']:
                if last['rsi'] < self.rsi_overbought: signal = 1
            elif prev['sma_fast'] >= prev['sma_slow'] and last['sma_fast'] < last['sma_slow']:
                if last['rsi'] > self.rsi_oversold: signal = -1
            return signal
