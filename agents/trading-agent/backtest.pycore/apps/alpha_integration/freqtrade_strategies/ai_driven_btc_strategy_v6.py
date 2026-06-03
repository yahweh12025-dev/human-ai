from freqtrade.strategy import IStrategy
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import talib

logger = logging.getLogger(__name__)

class AI_Driven_BTC_Strategy_V6(IStrategy):
    """
    AI-Driven Bitcoin Strategy V6 (Volatility-Regime Hybrid).
    
    Logic:
    - Categorize market based on Volatility (BB Width & ATR).
    - Regime 1: Low Volatility (Consolidation) -> Mean Reversion (Buy the bottom of the range).
    - Regime 2: High Volatility (Trending) -> Breakout/Momentum (Buy the breakout).
    - Regime 3: Erratic/Chaos (High ATR + Low BB Width) -> Stay Flat.
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
        dataframe['ema_fast'] = talib.EMA(dataframe['close'], timeperiod=12)
        dataframe['ema_slow'] = talib.EMA(dataframe['close'], timeperiod=26)
        dataframe['ema_200'] = talib.EMA(dataframe['close'], timeperiod=200)
        
        # Momentum Indicators
        dataframe['rsi'] = talib.RSI(dataframe['close'], timeperiod=14)
        macd, macdsignal, macdhist = talib.MACD(dataframe['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe['macd_hist'] = macdhist

        # Volatility Indicators
        dataframe['bb_upper'], dataframe['bb_middle'], dataframe['bb_lower'] = talib.BBANDS(
            dataframe['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
        )
        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle']
        dataframe['bb_width_avg'] = dataframe['bb_width'].rolling(window=20).mean()
        
        dataframe['atr'] = talib.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)
        dataframe['atr_avg'] = dataframe['atr'].rolling(window=20).mean()

        # Regime Detection
        # 0: Consolidation (Low Vol), 1: Trending (High Vol), -1: Chaos (Erratic)
        dataframe['regime'] = 0
        
        # Low Volatility (Consolidation)
        dataframe.loc[
            (dataframe['bb_width'] < dataframe['bb_width_avg'] * 0.8) & 
            (dataframe['atr'] < dataframe['atr_avg']), 
            'regime'
        ] = 0
        
        # High Volatility (Trending)
        dataframe.loc[
            (dataframe['bb_width'] > dataframe['bb_width_avg'] * 1.2) & 
            (dataframe['atr'] > dataframe['atr_avg']), 
            'regime'
        ] = 1
        
        # Chaos (High ATR but low BB width - often means large spikes but no trend)
        dataframe.loc[
            (dataframe['atr'] > dataframe['atr_avg'] * 1.5) & 
            (dataframe['bb_width'] < dataframe['bb_width_avg']), 
            'regime'
        ] = -1

        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        V6 Entry Logic:
        
        1. Consolidation Regime (Regime 0):
           - Mean Reversion: Buy when Close < BB Lower and RSI < 35.
           
        2. Trending Regime (Regime 1):
           - Breakout: Buy when Close > BB Upper and EMA Fast > EMA Slow.
           
        3. Chaos Regime (Regime -1):
           - No Entries.
        """
        
        # Consolidation Entries
        consolidation_entry = (
            (dataframe['regime'] == 0) &
            (dataframe['close'] < dataframe['bb_lower']) &
            (dataframe['rsi'] < 35)
        )

        # Trending Entries
        trending_entry = (
            (dataframe['regime'] == 1) &
            (dataframe['close'] > dataframe['bb_upper']) &
            (dataframe['ema_fast'] > dataframe['ema_slow']) &
            (dataframe['macd_hist'] > 0)
        )

        dataframe.loc[consolidation_entry | trending_entry, 'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        V6 Exit Logic:
        1. Trend Reversal: EMA Fast < EMA Slow
        2. Overbought: RSI > 75
        3. Momentum Loss: MACD Hist < 0
        4. Breakout failure: Close < BB Middle
        """
        dataframe.loc[
            (
                (dataframe['ema_fast'] < dataframe['ema_slow']) |
                (dataframe['rsi'] > 75) |
                (dataframe['macd_hist'] < 0) |
                (dataframe['close'] < dataframe['bb_middle'])
            ),
            'exit_long'] = 1

        return dataframe
