from freqtrade.strategy import IStrategy
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import talib

logger = logging.getLogger(__name__)

class AI_Driven_BTC_Strategy_V4(IStrategy):
    """
    AI-Driven Bitcoin Strategy V4.
    Implements:
    - Macro Trend (EMA 200)
    - Volatility Squeeze detection (Bollinger Band Width)
    - Momentum confirmation (MACD Histogram)
    - Adaptive RSI thresholds
    """
    # Strategy parameters
    minimal_roi = {
        "0": 0.15,
        "30": 0.10,
        "60": 0.05,
        "120": 0.02,
        "240": 0.01
    }

    stoploss = -0.04
    timeframe = '1h'

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        # Get periods from config or use defaults
        ema_fast_p = self.config.get('ema_fast_period', 12)
        ema_slow_p = self.config.get('ema_slow_period', 26)
        ema_200_p = self.config.get('ema_200_period', 200)
        rsi_p = self.config.get('rsi_period', 14)
        macd_fast = self.config.get('macd_fast_period', 12)
        macd_slow = self.config.get('macd_slow_period', 26)
        macd_signal = self.config.get('macd_signal_period', 9)
        bb_p = self.config.get('bb_period', 20)
        bb_dev = self.config.get('bb_deviation', 2)
        adx_p = self.config.get('adx_period', 14)

        # Trend Indicators
        dataframe['ema_fast'] = talib.EMA(dataframe['close'], timeperiod=ema_fast_p)
        dataframe['ema_slow'] = talib.EMA(dataframe['close'], timeperiod=ema_slow_p)
        dataframe['ema_200'] = talib.EMA(dataframe['close'], timeperiod=ema_200_p)
        
        # Momentum Indicators
        dataframe['rsi'] = talib.RSI(dataframe['close'], timeperiod=rsi_p)
        macd, macdsignal, macdhist = talib.MACD(dataframe['close'], fastperiod=macd_fast, slowperiod=macd_slow, signalperiod=macd_signal)
        dataframe['macd_hist'] = macdhist

        # Volatility Indicators
        dataframe['bb_upper'], dataframe['bb_middle'], dataframe['bb_lower'] = talib.BBANDS(
            dataframe['close'], timeperiod=bb_p, nbdevup=bb_dev, nbdevdn=bb_dev, matype=0
        )
        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle']
        
        # Trend Strength
        dataframe['adx'] = talib.ADX(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=adx_p)

        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        V4 Entry Logic:
        1. Macro Trend: Close > EMA 200
        2. Micro Trend: EMA Fast > EMA Slow
        3. Momentum: MACD Histogram > 0 (Increasing momentum)
        4. Volatility: BB Width > rolling mean of BB Width (Avoiding extreme squeeze/flatness)
        5. Strength: ADX > 25
        6. Not Overbought: RSI < 65
        """
        # Get thresholds from config or use defaults
        adx_threshold = self.config.get('adx_threshold', 25)
        rsi_upper = self.config.get('rsi_upper_threshold', 65)
        rsi_lower = self.config.get('rsi_lower_threshold', 35)

        # Calculate a rolling mean of BB Width to identify expanding volatility
        dataframe['bb_width_avg'] = dataframe['bb_width'].rolling(window=20).mean()

        dataframe.loc[
            (
                (dataframe['close'] > dataframe['ema_200']) &
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                (dataframe['macd_hist'] > 0) &
                (dataframe['bb_width'] > dataframe['bb_width_avg']) &
                (dataframe['adx'] > adx_threshold) &
                (dataframe['rsi'] < rsi_upper) &
                (dataframe['rsi'] > rsi_lower)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        V4 Exit Logic:
        1. Trend Reversal: EMA Fast < EMA Slow
        2. Overbought: RSI > 75
        3. Momentum Loss: MACD Histogram < 0
        4. Volatility Collapse: Close < BB Lower
        """
        rsi_upper_exit = self.config.get('rsi_upper_exit', 75)

        dataframe.loc[
            (
                (dataframe['ema_fast'] < dataframe['ema_slow']) |
                (dataframe['rsi'] > rsi_upper_exit) |
                (dataframe['macd_hist'] < 0) |
                (dataframe['close'] < dataframe['bb_lower'])
            ),
            'exit_long'] = 1

        return dataframe
