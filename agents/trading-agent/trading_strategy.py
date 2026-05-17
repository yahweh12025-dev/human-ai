# Strategy Version: Architect-Alpha-2 (Optimized)
"""
Unified Trading Strategy vFinal (Optimized)
Hard-locked to high-timeframe symmetry, dynamic risk scaling,
and vectorized indicator logic.
"""

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class TradingStrategy:
    def __init__(self, config=None):
        self.config = config or {}
        self.pivot_period = self.config.get('pivot_period', 48)
        self.keltner_period = self.config.get('keltner_period', 20)
        self.keltner_mult = self.config.get('keltner_mult', 1.2)
        self.streak_threshold = self.config.get('streak_threshold', 3)

        # Renamed to EMA to reflect actual calculation used
        self.ema_fast = self.config.get('ema_fast', 10)
        self.ema_slow = self.config.get('ema_slow', 30)

        # Surgical targets
        self.stop_loss_pct = self.config.get('stop_loss_percent', 2.0)
        self.take_profit_pct = self.config.get('take_profit_percent', 5.0)
        self.max_risk_per_trade = self.config.get('max_risk_per_trade', 2.0)

        # Cycle 6: Volatility-Indexed Exit Params
        self.vol_window = self.config.get('vol_window', 100)
        self.temporal_exit_bars = self.config.get('temporal_exit_bars', 120)
        self.equity_danger_threshold = self.config.get('equity_danger_threshold', 0.3) # 30% of starting equity

    def generate_signal(self, data: pd.DataFrame) -> int:
        """Unified Scoring System: Returns score from -5 to 5. Optimized with Pandas."""
        if len(data) < max(self.pivot_period, self.ema_slow, self.keltner_period) + 1:
            return 0

        # We only need to calculate indicators for the final rows to save processing time
        # In a live environment, passing only a sliced DataFrame (e.g., last 200 rows) is recommended
        closes = data['close']
        highs = data['high']
        lows = data['low']
        opens = data['open']

        current_close = closes.iloc[-1]
        prev_close = closes.iloc[-2]

        # Calculate RSI
        rsi_period = 14
        delta = closes.diff()
        gains = delta[delta > 0]
        losses = -delta[delta < 0]
        avg_gain = gains.rolling(window=rsi_period).mean()
        avg_loss = losses.rolling(window=rsi_period).mean()
        rs = avg_gain.iloc[-1] / avg_loss.iloc[-1] if avg_loss.iloc[-1] != 0 else 50
        rsi = 100 - (100 / (1 + rs)) if avg_loss.iloc[-1] != 0 else 50


        score = 0

        # 1. Pivot Bias
        recent_high = highs.tail(self.pivot_period).max()
        recent_low = lows.tail(self.pivot_period).min()
        pivot = (recent_high + recent_low + prev_close) / 3
        score += 1 if current_close > pivot else -1

        # 2. Keltner Stretch (Vectorized EMA & ATR)
        # Calculate ATR using Pandas
        tr0 = highs - lows
        tr1 = (highs - closes.shift(1)).abs()
        tr2 = (lows - closes.shift(1)).abs()
        tr = pd.concat([tr0, tr1, tr2], axis=1).max(axis=1)
        atr = tr.ewm(span=10, adjust=False).mean().iloc[-1]

        mid = closes.ewm(span=self.keltner_period, adjust=False).mean().iloc[-1]

        if current_close < (mid - self.keltner_mult * atr): 
            score += 2
        elif current_close > (mid + self.keltner_mult * atr): 
            score -= 2

        # 3. Candle Streak (Fixed logic)
        streak = 0
        last_dir = np.sign(current_close - opens.iloc[-1])
        
        if last_dir != 0:
            for j in range(len(closes)-1, max(-1, len(closes)-20), -1):
                current_dir = np.sign(closes.iloc[j] - opens.iloc[j])
                if current_dir == last_dir:
                    streak += current_dir
                else:
                    break
                    
        if streak <= -self.streak_threshold: score += 1
        elif streak >= self.streak_threshold: score -= 1

        # 4. Moving Average Trend
        ema_f = closes.ewm(span=self.ema_fast, adjust=False).mean().iloc[-1]
        ema_s = closes.ewm(span=self.ema_slow, adjust=False).mean().iloc[-1]
        score += 1 if ema_f > ema_s else -1

        # 5. RSI Adjustment
        if rsi > 70:  # Overbought
            score -= 1
        elif rsi < 30:  # Oversold
            score += 1

        return score

    def calculate_position_size(self, symbol: str, entry_price: float, stop_loss_price: float,
                                current_equity: float, starting_equity: float, score: int) -> float:
        """Symmetry-Based Risk Scaling: More points = more leverage."""
        if entry_price == stop_loss_price:
            logger.warning("Entry price equals stop loss price. Cannot calculate position size.")
            return 0.0

        equity_ratio = current_equity / starting_equity if starting_equity > 0 else 1.0

        # Default to 0 risk for scores below 3 to prevent weak signal entry
        risk_multiplier = {3: 1.0, 4: 1.5, 5: 2.0}.get(abs(score), 0.0)

        if risk_multiplier == 0.0:
            return 0.0

        dynamic_risk = self.max_risk_per_trade * risk_multiplier * max(0.5, min(1.5, equity_ratio))
        risk_amount = current_equity * (dynamic_risk / 100)
        risk_per_share = abs(entry_price - stop_loss_price)

        return risk_amount / risk_per_share

    def check_exit(self, symbol: str, current_price: float, entry_price: float, signal: int,
                   data: pd.DataFrame=None, current_score: int=0, hold_time: int=0,
                   current_equity: float=None, starting_equity: float=None) -> bool:
        """Symmetry-based exits: Signal decay or target hits."""

        # 1. Signal Flip or Decay
        if current_score == 0 or (current_score * signal <= 0):
            return True

        tp_pct = self.take_profit_pct

        # 2. Vectorized Volatility Percentile (Optimized)
        if data is not None and len(data) >= self.vol_window + 1:
            closes = data['close']
            # Using log returns for accurate volatility
            log_returns = np.log(closes / closes.shift(1)).dropna()

            if len(log_returns) >= self.vol_window:
                rolling_vol = log_returns.rolling(window=self.vol_window).std()
                current_vol = rolling_vol.iloc[-1]

                # Approximate percentile using the last 500 periods (prevent memory bloat)
                lookback_vols = rolling_vol.tail(500).dropna()
                if not lookback_vols.empty:
                    percentile = (lookback_vols < current_vol).mean()
                    tp_pct = self.take_profit_pct * (1 + percentile)

        # 3. Dynamic Risk Guard (Replaced hardcoded $3.00)
        if current_equity is not None and starting_equity is not None:
            if current_equity < (starting_equity * self.equity_danger_threshold):
                tp_pct = max(self.take_profit_pct * 0.5, tp_pct * 0.85)

        # 4. Stop Loss / Take Profit
        pnl_pct = ((current_price - entry_price) / entry_price) * signal * 100
        if pnl_pct <= -self.stop_loss_pct or pnl_pct >= tp_pct:
            return True

        # 5. Temporal Exit
        if hold_time >= self.temporal_exit_bars:
            return True

        return False