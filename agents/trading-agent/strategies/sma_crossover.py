"""
SMA Crossover Strategy with RSI Filter and Volume Confirmation

Generates trading signals based on:
- SMA crossover: fast SMA crossing above/below slow SMA
- RSI filter: only take long signals when RSI < overbought, short signals when RSI > oversold
- Volume confirmation: only trade when volume is above average threshold
"""
import pandas as pd
import numpy as np
import logging

class SMACrossover:
    def __init__(self, config):
        """
        Initialize the strategy with timeframe-adaptive SMA periods.
        """
        # Base configuration
        self.base_fast = config.get('fast_period', 10)
        self.base_slow = config.get('slow_period', 30)
        
        # Timeframe-specific overrides (in minutes)
        self.tf_overrides = {
            1:  {'fast': 5,  'slow': 15}, # 1m: Very aggressive
            5:  {'fast': 8,  'slow': 20}, # 5m: Aggressive
            15: {'fast': 10, 'slow': 30}, # 15m: Balanced
            30: {'fast': 12, 'slow': 35}, # 30m: Balanced
            60: {'fast': 15, 'slow': 45}, # 1h: Stable
            120:{'fast': 20, 'slow': 60}, # 2h: Stable
            240:{'fast': 25, 'slow': 80}, # 4h: Conservative
        }
        
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.volume_threshold = config.get('volume_threshold', 1.5)
        self.logger = logging.getLogger(__name__)

    def calculate_indicators(self, data, timeframe_mins=60):
        """
        Calculate SMA, RSI, and volume indicators using adaptive periods.
        """
        df = data.copy()
        
        # Select adaptive periods based on timeframe
        periods = self.tf_overrides.get(timeframe_mins, {'fast': self.base_fast, 'slow': self.base_slow})
        fast = periods['fast']
        slow = periods['slow']
        
        df['sma_fast'] = df['Close'].rolling(window=fast).mean()
        df['sma_slow'] = df['Close'].rolling(window=slow).mean()

        # Calculate RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Calculate volume average for confirmation
        df['volume_avg'] = df['Volume'].rolling(window=20).mean()
        
        return df

    def generate_signal(self, data, timeframe_mins=60):
        """
        Generate trading signal using adaptive SMA, RSI, and volume confirmation.
        """
        # Need enough data for the longest adaptive period (up to 80 for 4h)
        if len(data) < 80:
            return 0

        df = self.calculate_indicators(data, timeframe_mins)
        last = df.iloc[-1]
        prev = df.iloc[-2]

        # Volume confirmation
        volume_confirmed = last['Volume'] > (last['volume_avg'] * self.volume_threshold)
        if not volume_confirmed:
            return 0

        signal = 0
        if prev['sma_fast'] <= prev['sma_slow'] and last['sma_fast'] > last['sma_slow']:
            if last['rsi'] < self.rsi_overbought:
                signal = 1
        elif prev['sma_fast'] >= prev['sma_slow'] and last['sma_fast'] < last['sma_slow']:
            if last['rsi'] > self.rsi_oversold:
                signal = -1

        return signal