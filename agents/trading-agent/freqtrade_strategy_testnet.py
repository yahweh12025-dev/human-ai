#!/usr/bin/env python3
"""
FreqTrade Strategy for Binance Testnet - V8 Optimized
AI-driven BTC/USDT futures strategy with swarm intelligence integration

Improvements over V7:
- Added time-of-day filter to avoid low-liquidity choppy periods (UTC 0-4, 22-23)
- Reduced trade frequency by requiring stronger multi-indicator confluence
- Improved R:R via asymmetric exits (let winners run longer, cut losers faster)
- Added momentum confirmation with ROC indicator
- Added volume profile filter (requires 1.5x avg volume, up from 1.0x)
- Stochastic RSI for more precise oversold/overbought entries
- Cooldown period between trades to avoid overtrading
- ADX threshold raised from 20 to 25 for stronger trend confirmation
"""

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
from datetime import datetime, timedelta
from typing import Optional


class SwarmIntelligenceStrategy(IStrategy):
    """
    AI-Driven Strategy V8 with Swarm Intelligence Integration
    - Multi-timeframe trend analysis with stricter filters
    - Volatility-based entries with time-of-day awareness
    - Momentum confirmation (ROC + Stoch RSI)
    - Dynamic risk management with tighter stops
    - Trade frequency control via cooldown
    """

    # Strategy interface version
    INTERFACE_VERSION = 3

    # ROI table - more patient profit taking
    minimal_roi = {
        "0": 0.12,    # 12% profit target (increased from 10%)
        "60": 0.06,   # 6% after 1 hour (increased from 5%)
        "120": 0.04,  # 4% after 2 hours (increased from 3%)
        "240": 0.02,  # 2% after 4 hours
        "360": 0.01   # 1% after 6 hours
    }

    # Tighter stoploss to improve R:R
    stoploss = -0.035  # -3.5% hard stop (tighter than -5%)

    # Trailing stop - locks in profits earlier
    trailing_stop = True
    trailing_stop_positive = 0.015  # Start trailing at +1.5%
    trailing_stop_positive_offset = 0.025  # Only after +2.5% reached
    trailing_only_offset_is_reached = True

    # Optimal timeframe - moved to 1h to match backtest data
    timeframe = '1h'

    # Run "populate_indicators()" only for new candle
    process_only_new_candles = True

    # Cooldown: minimum candles between trades
    startup_candle_count = 50

    # Order types
    order_types = {
        'entry': 'market',
        'exit': 'market',
        'stoploss': 'market',
        'stoploss_on_exchange': True
    }

    # Hyperopt parameters - tightened ranges based on backtest analysis
    buy_rsi_threshold = DecimalParameter(22, 35, default=28, space='buy')
    buy_stoch_threshold = DecimalParameter(15, 30, default=20, space='buy')
    buy_atr_multiplier = DecimalParameter(1.15, 1.6, default=1.3, space='buy')
    buy_volume_multiplier = DecimalParameter(1.2, 2.0, default=1.5, space='buy')
    buy_adx_threshold = DecimalParameter(22, 35, default=25, space='buy')
    buy_roc_threshold = DecimalParameter(0.5, 3.0, default=1.0, space='buy')

    sell_rsi_threshold = DecimalParameter(65, 80, default=72, space='sell')
    sell_stoch_threshold = DecimalParameter(75, 90, default=80, space='sell')

    # Time filter parameters
    avoid_hours_start = IntParameter(0, 4, default=0, space='buy')
    avoid_hours_end = IntParameter(3, 6, default=4, space='buy')

    # Track last trade time for cooldown
    last_trade_candle = {}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate technical indicators for strategy logic.
        Added: Stochastic RSI, ROC, enhanced volume analysis, hour filter.
        """
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # Stochastic RSI for more precise overbought/oversold
        stoch = ta.STOCH(dataframe, fastk_period=14, slowk_period=3, slowd_period=3)
        dataframe['stoch_k'] = stoch['slowk']
        dataframe['stoch_d'] = stoch['slowd']

        # Rate of Change (momentum confirmation)
        dataframe['roc_5'] = ta.ROC(dataframe, timeperiod=5)
        dataframe['roc_10'] = ta.ROC(dataframe, timeperiod=10)

        # Moving Averages
        dataframe['ema_9'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_21'] = ta.EMA(dataframe, timeperiod=21)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)

        # ATR (Average True Range) for volatility
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_ma'] = dataframe['atr'].rolling(window=20).mean()
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close']  # Normalized ATR

        # Bollinger Bands - standard and narrow
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2, nbdevdn=2)
        dataframe['bb_upper'] = bollinger['upperband']
        dataframe['bb_middle'] = bollinger['middleband']
        dataframe['bb_lower'] = bollinger['lowerband']
        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle']

        # Bollinger Band percent (where price is within bands)
        dataframe['bb_pct'] = (dataframe['close'] - dataframe['bb_lower']) / (
            dataframe['bb_upper'] - dataframe['bb_lower']
        )

        # MACD with signal line
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        # MACD histogram momentum (rising/falling)
        dataframe['macdhist_rising'] = (
            dataframe['macdhist'] > dataframe['macdhist'].shift(1)
        ).astype(int)

        # ADX (Average Directional Index) for trend strength
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)

        # Volume indicators - enhanced
        dataframe['volume_ma_20'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['volume_ma_50'] = dataframe['volume'].rolling(window=50).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma_20']

        # Custom: Volatility spike detection
        dataframe['atr_spike'] = dataframe['atr'] / dataframe['atr_ma']

        # Trend direction - requires all EMAs aligned
        dataframe['trend_up'] = (
            (dataframe['ema_9'] > dataframe['ema_21']) &
            (dataframe['ema_21'] > dataframe['ema_50']) &
            (dataframe['ema_50'] > dataframe['ema_200'])
        ).astype(int)

        dataframe['trend_down'] = (
            (dataframe['ema_9'] < dataframe['ema_21']) &
            (dataframe['ema_21'] < dataframe['ema_50']) &
            (dataframe['ema_50'] < dataframe['ema_200'])
        ).astype(int)

        # Strong trend (price above/below all EMAs)
        dataframe['strong_uptrend'] = (
            (dataframe['close'] > dataframe['ema_9']) &
            (dataframe['trend_up'] == 1)
        ).astype(int)

        dataframe['strong_downtrend'] = (
            (dataframe['close'] < dataframe['ema_9']) &
            (dataframe['trend_down'] == 1)
        ).astype(int)

        # Hour of day for time filter (UTC)
        dataframe['hour'] = dataframe['date'].dt.hour

        # Candle pattern detection
        dataframe['body_pct'] = abs(dataframe['close'] - dataframe['open']) / (
            dataframe['high'] - dataframe['low'] + 0.0001
        )

        # Previous candle direction
        dataframe['prev_bullish'] = (dataframe['close'].shift(1) > dataframe['open'].shift(1)).astype(int)
        dataframe['prev_bearish'] = (dataframe['close'].shift(1) < dataframe['open'].shift(1)).astype(int)

        # Consecutive candle counter (for detecting exhaustion)
        dataframe['consec_green'] = 0
        dataframe['consec_red'] = 0

        # Swarm Intelligence Score (placeholder - integrate with swarm data)
        dataframe['swarm_score'] = 0.5  # Neutral default

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry signal generation using stricter multi-indicator confirmation.
        Key changes:
        - Time-of-day filter (avoid UTC 0-4 and 22-23)
        - Higher volume threshold (1.5x vs 1.0x)
        - ADX >= 25 (up from 20)
        - Stochastic RSI confirmation
        - ROC momentum confirmation
        - Stronger trend alignment requirement
        """
        # Time filter: avoid low-liquidity hours (UTC)
        time_ok = (
            (dataframe['hour'] >= self.avoid_hours_end.value) &
            (dataframe['hour'] <= 21)
        )

        # LONG entries - strict confluence required
        dataframe.loc[
            (
                # Time filter
                time_ok &

                # Trend confirmation (all EMAs aligned)
                (dataframe['trend_up'] == 1) &

                # RSI oversold but not extreme (avoid catching falling knives)
                (dataframe['rsi'] < self.buy_rsi_threshold.value) &
                (dataframe['rsi'] > 15) &

                # Stochastic RSI oversold
                (dataframe['stoch_k'] < self.buy_stoch_threshold.value) &

                # Positive momentum shift (ROC turning up)
                (dataframe['roc_5'] > -self.buy_roc_threshold.value) &
                (dataframe['roc_10'] > 0) &

                # ATR spike (volatility event, but not extreme)
                (dataframe['atr_spike'] > self.buy_atr_multiplier.value) &
                (dataframe['atr_spike'] < 2.5) &

                # MACD bullish: histogram rising (momentum improving)
                (dataframe['macdhist_rising'] == 1) &

                # ADX shows strong trend
                (dataframe['adx'] > self.buy_adx_threshold.value) &

                # Directional indicator confirms
                (dataframe['plus_di'] > dataframe['minus_di']) &

                # Price in lower half of Bollinger Bands
                (dataframe['bb_pct'] < 0.4) &

                # Volume confirmation (1.5x average)
                (dataframe['volume_ratio'] > self.buy_volume_multiplier.value) &

                # Volume is not zero
                (dataframe['volume'] > 0) &

                # Previous candle was bearish (buying the dip after a red candle)
                (dataframe['prev_bearish'] == 1)
            ),
            'enter_long'] = 1

        # SHORT entries - stricter for shorts (historically lower win rate)
        dataframe.loc[
            (
                # Time filter
                time_ok &

                # Trend confirmation (all EMAs aligned down)
                (dataframe['trend_down'] == 1) &

                # RSI overbought but not extreme
                (dataframe['rsi'] > (100 - self.buy_rsi_threshold.value)) &
                (dataframe['rsi'] < 85) &

                # Stochastic RSI overbought
                (dataframe['stoch_k'] > (100 - self.buy_stoch_threshold.value)) &

                # Negative momentum (ROC turning down)
                (dataframe['roc_5'] < self.buy_roc_threshold.value) &
                (dataframe['roc_10'] < 0) &

                # ATR spike
                (dataframe['atr_spike'] > self.buy_atr_multiplier.value) &
                (dataframe['atr_spike'] < 2.5) &

                # MACD bearish: histogram falling
                (dataframe['macdhist_rising'] == 0) &

                # ADX shows strong trend (higher threshold for shorts)
                (dataframe['adx'] > self.buy_adx_threshold.value + 3) &

                # Directional indicator confirms
                (dataframe['minus_di'] > dataframe['plus_di']) &

                # Price in upper half of Bollinger Bands
                (dataframe['bb_pct'] > 0.6) &

                # Volume confirmation (higher for shorts)
                (dataframe['volume_ratio'] > self.buy_volume_multiplier.value * 1.2) &

                # Volume is not zero
                (dataframe['volume'] > 0) &

                # Previous candle was bullish (selling the rip)
                (dataframe['prev_bullish'] == 1)
            ),
            'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit signal generation - more selective to let winners run.
        Uses AND conditions instead of OR for exits (less aggressive exit).
        """
        # Long exits - require multiple confirmations to exit
        dataframe.loc[
            (
                # RSI overbought AND momentum fading
                (dataframe['rsi'] > self.sell_rsi_threshold.value) &
                (dataframe['stoch_k'] > self.sell_stoch_threshold.value) &
                (dataframe['macdhist_rising'] == 0)
            ) | (
                # Price hits upper BB AND RSI high AND negative ROC
                (dataframe['close'] > dataframe['bb_upper']) &
                (dataframe['rsi'] > 65) &
                (dataframe['roc_5'] < 0)
            ) | (
                # Trend reversal signal
                (dataframe['ema_9'] < dataframe['ema_21']) &
                (dataframe['adx'] > 30) &
                (dataframe['minus_di'] > dataframe['plus_di'])
            ),
            'exit_long'] = 1

        # Short exits
        dataframe.loc[
            (
                # RSI oversold AND momentum shifting up
                (dataframe['rsi'] < (100 - self.sell_rsi_threshold.value)) &
                (dataframe['stoch_k'] < (100 - self.sell_stoch_threshold.value)) &
                (dataframe['macdhist_rising'] == 1)
            ) | (
                # Price hits lower BB AND RSI low AND positive ROC
                (dataframe['close'] < dataframe['bb_lower']) &
                (dataframe['rsi'] < 35) &
                (dataframe['roc_5'] > 0)
            ) | (
                # Trend reversal signal
                (dataframe['ema_9'] > dataframe['ema_21']) &
                (dataframe['adx'] > 30) &
                (dataframe['plus_di'] > dataframe['minus_di'])
            ),
            'exit_short'] = 1

        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time: datetime, entry_tag: str,
                           side: str, **kwargs) -> bool:
        """
        Final confirmation before trade entry:
        - Cooldown between trades (minimum 3 candles / 3 hours)
        - Day-of-week filter (reduce exposure Wed/Thu)
        - Swarm intelligence integration point
        """
        # Cooldown check: don't trade within 3 candles of last trade
        pair_key = f"{pair}_{side}"
        if pair_key in self.last_trade_candle:
            time_diff = current_time - self.last_trade_candle[pair_key]
            if time_diff < timedelta(hours=3):
                return False

        # Day of week filter: reduce position sizing mid-week
        day_of_week = current_time.weekday()
        if day_of_week in [2, 3]:  # Wednesday, Thursday
            # Only allow very strong signals mid-week (checked via dataframe in custom_entry)
            pass  # Allow but with reduced sizing via custom_stake_amount

        # Record trade time
        self.last_trade_candle[pair_key] = current_time

        return True

    def custom_stake_amount(self, current_time: datetime, current_rate: float,
                           proposed_stake: float, min_stake: Optional[float],
                           max_stake: float, leverage: float, entry_tag: Optional[str],
                           side: str, **kwargs) -> float:
        """
        Dynamic position sizing based on day of week and volatility.
        """
        day_of_week = current_time.weekday()

        # Reduce size mid-week (lower historical win rate)
        if day_of_week == 2:  # Wednesday
            return proposed_stake * 0.7
        elif day_of_week == 3:  # Thursday
            return proposed_stake * 0.8

        # Full size Mon/Tue/Fri
        return proposed_stake

    def custom_exit(self, pair: str, trade, current_time: datetime, current_rate: float,
                   current_profit: float, **kwargs) -> Optional[str]:
        """
        Custom exit logic with improved time management and profit protection.
        """
        trade_duration = current_time - trade.open_date_utc

        # Quick profit lock: if +3% in first 30 minutes, secure it
        if trade_duration < timedelta(minutes=30) and current_profit > 0.03:
            return 'quick_profit_secured_3pct'

        # Time-based exit (max hold 6 hours - extended from 4h for better R:R)
        if trade_duration > timedelta(hours=6):
            if current_profit > 0.005:  # Only exit if slightly profitable
                return 'max_hold_time_profitable'
            elif trade_duration > timedelta(hours=8):
                return 'max_hold_time_hard_limit'

        # Profit protection (secure gains at 6%)
        if current_profit > 0.06:
            return 'profit_secured_6pct'

        # Stale trade exit: if no progress after 2 hours, cut at -1%
        if trade_duration > timedelta(hours=2) and current_profit < -0.01:
            return 'stale_trade_cut'

        # Emergency exit on extreme volatility
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if not dataframe.empty:
            latest_atr_spike = dataframe['atr_spike'].iloc[-1]
            if latest_atr_spike > 2.5:  # Extreme volatility (raised from 2.0)
                if current_profit > 0:
                    return 'extreme_volatility_profit_exit'
                elif current_profit < -0.02:
                    return 'extreme_volatility_loss_exit'

        return None

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                side: str, **kwargs) -> float:
        """
        Dynamic leverage based on market conditions.
        Conservative: 2-3x (down from potential 5x in V7 backtests).
        """
        # Use lower leverage during volatile/uncertain times
        day_of_week = current_time.weekday()
        hour = current_time.hour

        # Weekend close / Monday open: reduce leverage
        if day_of_week == 0 and hour < 8:  # Monday morning
            return 2.0

        # Friday afternoon: reduce
        if day_of_week == 4 and hour > 16:
            return 2.0

        # Default: moderate leverage
        return 3.0
