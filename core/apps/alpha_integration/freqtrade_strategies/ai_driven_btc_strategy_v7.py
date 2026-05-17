from freqtrade.strategy import IStrategy
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import talib

logger = logging.getLogger(__name__)

class AI_Driven_BTC_Strategy_V7(IStrategy):
    """
    AI-Driven Bitcoin Strategy V7 (The Dynamic Regime Switcher).
    
    The core concept is to detect the market regime and switch the entire 
    trading logic to match.
    
    Regimes:
    1. TRENDING (High ADX, High BBW): Uses Momentum/Breakout logic.
    2. RANGE (Low ADX, Low BBW): Uses Mean-Reversion/Oscillator logic.
    3. CHAOS (High ATR, Low BBW): No trading (Stay flat).
    """
    # Strategy parameters
    minimal_roi = {
        "0": 0.15,
        "30": 0.10,
        "60": 0.05,
        "120": 0.02,
        "240": 0.01
    }

    stoploss = -0.05
    timeframe = '1h'

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        # --- Common Indicators ---
        dataframe['ema_fast'] = talib.EMA(dataframe['close'], timeperiod=12)
        dataframe['ema_slow'] = talib.EMA(dataframe['close'], timeperiod=26)
        dataframe['ema_200'] = talib.EMA(dataframe['close'], timeperiod=200)
        dataframe['rsi'] = talib.RSI(dataframe['close'], timeperiod=14)
        macd, macdsignal, macdhist = talib.MACD(dataframe['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe['macd_hist'] = macdhist
        
        # --- Volatility/Regime Indicators ---
        dataframe['bb_upper'], dataframe['bb_middle'], dataframe['bb_lower'] = talib.BBANDS(
            dataframe['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
        )
        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle']
        dataframe['bb_width_avg'] = dataframe['bb_width'].rolling(window=20).mean()
        
        dataframe['adx'] = talib.ADX(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)
        dataframe['atr'] = talib.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)
        dataframe['atr_avg'] = dataframe['atr'].rolling(window=20).mean()

        # --- Regime Classification ---
        dataframe['regime'] = 0 # Default: Sideways/Range
        
        # Regime 1: Trending (High ADX and expanding BB Width)
        dataframe.loc[
            (dataframe['adx'] > 25) & (dataframe['bb_width'] > dataframe['bb_width_avg']), 
            'regime'
        ] = 1
        
        # Regime 2: Chaos (High ATR but squeezing BB Width - erratic spikes)
        dataframe.loc[
            (dataframe['atr'] > dataframe['atr_avg'] * 1.5) & (dataframe['bb_width'] < dataframe['bb_width_avg']), 
            'regime'
        ] = -1
        
        # Regime 0: Sideways/Range is the default (everything else)
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        V7 Entry Logic:
        
        If Regime == 1 (Trending):
           - Momentum Breakout: Close > BB Upper AND EMA Fast > EMA Slow AND MACD Hist > 0
           
        If Regime == 0 (Range):
           - Mean Reversion: Close < BB Lower AND RSI < 30
           
        If Regime == -1 (Chaos):
           - No entries.
        """
        
        # 1. Trending Logic (Breakout)
        trending_entry = (
            (dataframe['regime'] == 1) &
            (dataframe['close'] > dataframe['bb_upper']) &
            (dataframe['ema_fast'] > dataframe['ema_slow']) &
            (dataframe['macd_hist'] > 0)
        )

        # 2. Range Logic (Mean Reversion)
        range_entry = (
            (dataframe['regime'] == 0) &
            (dataframe['close'] < dataframe['bb_lower']) &
            (dataframe['rsi'] < 30)
        )

        dataframe.loc[trending_entry | range_entry, 'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        V7 Exit Logic:
        
        - Universal Safety: RSI > 80 (Overbought) OR EMA Fast < EMA Slow (Trend Reversal)
        - Regime-Specific:
            - If in Trend: Exit on MACD Histogram turning negative.
            - If in Range: Exit when Price returns to BB Middle.
        """
        
        # Universal Exits
        universal_exit = (
            (dataframe['rsi'] > 80) |
            (dataframe['ema_fast'] < dataframe['ema_slow'])
        )

        # Regime-Specific Exits
        trending_exit = (
            (dataframe['regime'] == 1) &
            (dataframe['macd_hist'] < 0)
        )
        
        range_exit = (
            (dataframe['regime'] == 0) &
            (dataframe['close'] > dataframe['bb_middle'])
        )

        dataframe.loc[universal_exit | trending_exit | range_exit, 'exit_long'] = 1

        return dataframe
