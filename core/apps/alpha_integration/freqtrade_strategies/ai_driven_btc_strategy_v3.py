from freqtrade.strategy import IStrategy
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import talib

logger = logging.getLogger(__name__)

class AI_Driven_BTC_Strategy_V3(IStrategy):
    """
    AI-Driven Bitcoin Strategy V3.
    Improved selectivity with a Macro Trend Filter (EMA 200) 
    and stricter Trend Strength (ADX > 25) requirements.
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
        # EMA for trend
        dataframe['ema_fast'] = talib.EMA(dataframe['close'], timeperiod=12)
        dataframe['ema_slow'] = talib.EMA(dataframe['close'], timeperiod=26)
        dataframe['ema_200'] = talib.EMA(dataframe['close'], timeperiod=200)
        
        # RSI for mean reversion/overbought/oversold
        dataframe['rsi'] = talib.RSI(dataframe['close'], timeperiod=14)
        
        # MACD for momentum
        macd, macdsignal, macdhist = talib.MACD(dataframe['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe['macd'] = macd
        dataframe['macd_signal'] = macdsignal
        dataframe['macd_hist'] = macdhist

        # Bollinger Bands for volatility/range
        dataframe['bb_upper'], dataframe['bb_middle'], dataframe['bb_lower'] = talib.BBANDS(
            dataframe['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
        )

        # ADX for trend strength
        dataframe['adx'] = talib.ADX(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)

        # ATR for volatility
        dataframe['atr'] = talib.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)

        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        V3 Entry Logic:
        1. Macro Trend: Close > EMA 200
        2. Micro Trend: EMA Fast > EMA Slow
        3. Momentum: MACD > MACD Signal
        4. Strength: ADX > 25 (Stronger trend requirement)
        5. Not Overbought: RSI < 60
        6. Price Position: Close > BB Middle
        """
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['ema_200']) &
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                (dataframe['macd'] > dataframe['macd_signal']) &
                (dataframe['adx'] > 25) &
                (dataframe['rsi'] < 60) &
                (dataframe['close'] > dataframe['bb_middle'])
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        V3 Exit Logic:
        1. Trend Reversal: EMA Fast < EMA Slow
        2. Overbought: RSI > 75
        3. Momentum Loss: MACD < MACD Signal
        4. Extreme Downside: Close < BB Lower
        """
        dataframe.loc[
            (
                (dataframe['ema_fast'] < dataframe['ema_slow']) |
                (dataframe['rsi'] > 75) |
                (dataframe['macd'] < dataframe['macd_signal']) |
                (dataframe['close'] < dataframe['bb_lower'])
            ),
            'exit_long'] = 1

        return dataframe
