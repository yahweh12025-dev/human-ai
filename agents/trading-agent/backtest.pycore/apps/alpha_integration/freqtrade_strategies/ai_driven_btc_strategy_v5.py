from freqtrade.strategy import IStrategy
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import talib

logger = logging.getLogger(__name__)

class AI_Driven_BTC_Strategy_V5(IStrategy):
    """
    AI-Driven Bitcoin Strategy V5 (Regime Adaptive).
    
    Logic:
    - Determine Regime:
        - Bullish: EMA 50 > EMA 200
        - Bearish: EMA 50 < EMA 200
        - Sideways: EMA 50 is near EMA 200 (using a threshold)
    - Strategy Selection:
        - Bull Regime: Trend Following + RSI Dip Buying
        - Sideways Regime: Mean Reversion (Bollinger Bands)
        - Bear Regime: Stay Flat (No Longs)
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
        # Trend Indicators
        dataframe['ema_50'] = talib.EMA(dataframe['close'], timeperiod=50)
        dataframe['ema_200'] = talib.EMA(dataframe['close'], timeperiod=200)
        
        # Regime Detection
        # Threshold for "nearness" can be based on percentage
        dataframe['regime_gap'] = (dataframe['ema_50'] - dataframe['ema_200']) / dataframe['ema_200']
        dataframe['regime'] = 0 # 0: Sideways, 1: Bull, -1: Bear
        dataframe.loc[dataframe['regime_gap'] > 0.01, 'regime'] = 1
        dataframe.loc[dataframe['regime_gap'] < -0.01, 'regime'] = -1

        # Momentum Indicators
        dataframe['rsi'] = talib.RSI(dataframe['close'], timeperiod=14)
        macd, macdsignal, macdhist = talib.MACD(dataframe['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe['macd_hist'] = macdhist

        # Volatility Indicators
        dataframe['bb_upper'], dataframe['bb_middle'], dataframe['bb_lower'] = talib.BBANDS(
            dataframe['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
        )
        
        # Trend Strength
        dataframe['adx'] = talib.ADX(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)

        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        V5 Entry Logic:
        
        1. Bull Regime (EMA 50 > EMA 200):
           - Buy when RSI < 40 (Buying the dip in a trend)
           - OR EMA 50 crosses above EMA 200 (Golden Cross)
           
        2. Sideways Regime (|Regime Gap| < 1%):
           - Buy when Price < BB Lower (Mean Reversion)
           - AND RSI < 35
           
        3. Bear Regime:
           - No Long Entries
        """
        
        # 1. Bullish Entries
        bull_dip = (
            (dataframe['regime'] == 1) &
            (dataframe['rsi'] < 40)
        )
        
        bull_cross = (
            (dataframe['regime'] == 1) &
            (dataframe['ema_50'] > dataframe['ema_50'].shift(1)) &
            (dataframe['ema_200'] < dataframe['ema_200'].shift(1))
        )

        # 2. Sideways Entries
        sideways_reversion = (
            (dataframe['regime'] == 0) &
            (dataframe['close'] < dataframe['bb_lower']) &
            (dataframe['rsi'] < 35)
        )

        dataframe.loc[bull_dip | bull_cross | sideways_reversion, 'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        V5 Exit Logic:
        1. Trend Reversal: EMA 50 < EMA 200
        2. Overbought: RSI > 75
        3. Momentum Loss: MACD Hist < 0
        """
        dataframe.loc[
            (
                (dataframe['ema_50'] < dataframe['ema_200']) |
                (dataframe['rsi'] > 75) |
                (dataframe['macd_hist'] < 0)
            ),
            'exit_long'] = 1

        return dataframe
