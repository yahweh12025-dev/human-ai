"""
SMA Crossover Strategy with RSI Filter

Generates trading signals based on:
- SMA crossover: fast SMA crossing above/below slow SMA
- RSI filter: only take long signals when RSI < overbought, short signals when RSI > oversold
"""
import pandas as pd
import numpy as np
import logging

class SMACrossover:
    def __init__(self, config):
        """
        Initialize the strategy.
        :param config: Dictionary containing strategy parameters.
        """
        self.fast_period = config.get('fast_period', 10)
        self.slow_period = config.get('slow_period', 30)
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.logger = logging.getLogger(__name__)

    def calculate_indicators(self, data):
        """
        Calculate SMA and RSI indicators.
        :param data: pandas DataFrame with OHLCV data.
        :return: DataFrame with added indicator columns.
        """
        df = data.copy()
        # Calculate SMAs
        df['sma_fast'] = df['Close'].rolling(window=self.fast_period).mean()
        df['sma_slow'] = df['Close'].rolling(window=self.slow_period).mean()

        # Calculate RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        return df

    def generate_signal(self, data):
        """
        Generate trading signal based on SMA crossover and RSI.
        :param data: pandas DataFrame with OHLCV data.
        :return: integer signal: 1 (buy), -1 (sell), 0 (hold)
        """
        if len(data) < max(self.slow_period, self.rsi_period):
            return 0  # Not enough data

        df = self.calculate_indicators(data)
        # Get the last two rows to detect crossover
        last = df.iloc[-1]
        prev = df.iloc[-2]

        # Initialize signal as hold
        signal = 0

        # Check for bullish crossover: fast SMA crosses above slow SMA
        if prev['sma_fast'] <= prev['sma_slow'] and last['sma_fast'] > last['sma_slow']:
            # Bullish crossover
            # Only take if RSI is not overbought (we allow buying in normal or oversold conditions)
            if last['rsi'] < self.rsi_overbought:
                signal = 1
        # Check for bearish crossover: fast SMA crosses below slow SMA
        elif prev['sma_fast'] >= prev['sma_slow'] and last['sma_fast'] < last['sma_slow']:
            # Bearish crossover
            # Only take if RSI is not oversold (we allow selling in normal or overbought conditions)
            if last['rsi'] > self.rsi_oversold:
                signal = -1

        return signal