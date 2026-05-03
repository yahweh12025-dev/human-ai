# Strategy Version: Architect-Alpha-1
"""
Unified Trading Strategy vFinal
The definitive consolidated engine for consistent daily yield.
Hard-locked to high-timeframe symmetry and dynamic risk scaling.
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
        self.sma_fast = self.config.get('sma_fast', 10)
        self.sma_slow = self.config.get('sma_slow', 30)
        
        # Surgical targets for $1/day consistency
        self.stop_loss_pct = self.config.get('stop_loss_percent', 2.0)
        self.take_profit_pct = self.config.get('take_profit_percent', 5.0)
        self.max_risk_per_trade = self.config.get('max_risk_per_trade', 2.0)
        # Cycle 6: Volatility-Indexed Exit Params
        self.vol_window = self.config.get('vol_window', 100)


    def _calc_ema(self, values, period):
        if len(values) == 0: return []
        result = [values[0]] * len(values)
        k = 2 / (period + 1)
        for i in range(1, len(values)):
            result[i] = values[i] * k + result[i-1] * (1 - k)
        return result

    def _calc_atr(self, highs, lows, closes, period=10):
        if len(closes) == 0: return []
        tr = [highs[0] - lows[0]] * len(closes)
        for i in range(1, len(closes)):
            tr[i] = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
        return self._calc_ema(tr, period)

    def generate_signal(self, data):
        """Unified Scoring System: Returns score from -5 to 5."""
        if len(data) < max(self.pivot_period, self.sma_slow) + 1:
            return 0

        closes = data['close'].values
        opens = data['open'].values
        highs = data['high'].values
        lows = data['low'].values
        i = len(closes) - 1
        
        score = 0
        # 1. Pivot Bias
        p = (max(highs[-self.pivot_period:]) + min(lows[-self.pivot_period:]) + closes[-2]) / 3
        score += 1 if closes[i] > p else -1
        # 2. Keltner Stretch
        mid = self._calc_ema(closes, self.keltner_period)
        atr = self._calc_atr(highs, lows, closes)
        if closes[i] < (mid[i] - self.keltner_mult * atr[i]): score += 2
        elif closes[i] > (mid[i] + self.keltner_mult * atr[i]): score -= 2
        # 3. Candle Streak
        streak = 0
        for j in range(i, 0, -1):
            if closes[j] > opens[j]: streak += 1
            elif closes[j] < opens[j]: streak -= 1
            else: break
        if streak <= -self.streak_threshold: score += 1
        elif streak >= self.streak_threshold: score -= 1
        # 4. SMA Trend
        sma_f = self._calc_ema(closes, self.sma_fast)[-1]
        sma_s = self._calc_ema(closes, self.sma_slow)[-1]
        score += 1 if sma_f > sma_s else -1

        return score # Return full score for dynamic risk scaling

    def calculate_position_size(self, symbol, entry_price, stop_loss_price, current_equity, starting_equity, score):
        """Symmetry-Based Risk Scaling: More points = more leverage."""
        equity_ratio = current_equity / starting_equity
        
        # Scale risk based on absolute score
        risk_multiplier = {3: 1.0, 4: 1.5, 5: 2.0}.get(abs(score), 1.0)
        dynamic_risk = self.max_risk_per_trade * risk_multiplier * max(0.5, min(1.5, equity_ratio))
        
        risk_amount = current_equity * (dynamic_risk / 100)
        risk_per_share = abs(entry_price - stop_loss_price)
        raw_qty = risk_amount / risk_per_share if risk_per_share > 0 else 0
        return raw_qty

    def check_exit(self, symbol, current_price, entry_price, signal, data=None, current_score=0, hold_time=0, current_equity=None, starting_equity=None):
        """Symmetry-based exits: Signal decay or target hits.
        Cycle 6: Implements Volatility-Indexed Exit Multiplier.
        """
        # 1. Signal Flip or Decay (Close if score drops below 3 or flips sign)
        if current_score == 0 or (current_score * signal <= 0):
            return True
        
        # Calculate Dynamic Take Profit based on Volatility (Cycle 6)
        tp_pct = self.take_profit_pct
        if data is not None and len(data) >= self.vol_window:
            # Normalized Volatility Percentile (0.0 to 1.0)
            closes = data['close'].values
            vol = np.std(np.diff(np.log(closes[-self.vol_window:])))
            all_vols = [np.std(np.diff(np.log(closes[i:i+self.vol_window]))) 
                       for i in range(len(closes) - self.vol_window)]
            
            if all_vols:
                percentile = (sum(1 for v in all_vols if v < vol) / len(all_vols))
                # ExitMultiplier = 1 + normalized_volatility_percentile
                # We map this multiplier to the base take_profit_pct
                tp_pct = self.take_profit_pct * (1 + percentile)
        
        # Risk Guard Modification: Tighten exits when balance < $3.00
        if current_equity is not None and starting_equity is not None:
            if current_equity < 3.00:
                tp_pct = max(1.2, tp_pct * 0.85)

        # 2. Stop Loss / Take Profit
        pnl_pct = ((current_price - entry_price) / entry_price) * signal * 100
        if pnl_pct <= -self.stop_loss_pct or pnl_pct >= tp_pct:
            return True
            
        # 3. Temporal Exit
        if hold_time >= 120:
            return True
            
        return False

