# Trading Research Brief v1
**Date:** 2026-05-02  
**Author:** Trading Research Liaison (Subagent)  
**Purpose:** Bridge the Strategy Architect and Research Swarm by synthesizing the current strategy state and identified drawdown issues (Cycle 6) to guide targeted research questions.

---

## 1. Current Strategy Version
**Version Tag:** `Architect-Alpha-1` (Unified Trading Strategy vFinal)  
**Core File:** `trading_strategy.py`  
**Key Characteristics:**
- Unified scoring system (range -5 to 5) combining pivot bias, Keltner stretch, candle streak, and SMA trend.
- Symmetry‑based risk scaling: higher absolute scores → higher leverage (risk multiplier 1.0/1.5/2.0 for |score| = 3/4/5).
- Dynamic take‑profit based on volatility percentile (Cycle 6 feature).
- Volatility‑indexed exit multiplier: `tp_pct = base_take_profit_pct * (1 + percentile)` where percentile is the normalized volatility rank over the last `vol_window` (default 100) periods.
- Risk guard modification: when `current_equity < $3.00`, tighten TP by 15% (multiply by 0.85) and floor at 1.2%.
- Stop‑loss fixed at 2% per trade; temporal exit at 120 minutes.

---

## 2. Backtest Evidence (Cycle 6 – Latest Run)
**Backtest File:** `backtest_logs/run_20260426_220138.json`  
**Period:** 2026‑04‑23 → 2026‑04‑26 (and longer histories up to 2026‑03‑27).  
**Observations:**
- Reported `max_drawdown_pct` is **0.0%** for all symbol‑level series, indicating the drawdown metric is either not being calculated correctly or the per‑symbol equity series never dips below its previous peak (possible reset per trade).
- Despite the zero drawdown claim, the **equity trajectory shows substantial drawdowns** when aggregating across symbols (e.g., BTC/USDT short position from 2026‑04‑02 to 2026‑04‑26 reduces equity from 1.0 to **0.868**; combined BTC & ETH shorts drive equity as low as **0.843**).  
- Large losses occur on **trending markets** where the strategy takes a short position (signal = -1) but the market continues upward (BTC +17.7%, ETH +15.1% over the same period).  
- The **win‑rate** for longer‑term windows (16‑19 trades) drops to **~50%**, with average losses far exceeding average wins (avg loss ≈ -0.028 vs avg win ≈ +0.010).

---

## 3. Specific Drawdown Issues Identified in Cycle 6
1. **Trend‑Adverse Signal Bias**  
   - The strategy’s scoring system can generate strong short signals (-5 to -3) during sustained bull runs, especially when pivot and Keltner bands indicate “over‑extension” while SMA trend is negative.  
   - Result: systematic short exposure in trending markets leads to large, sustained losses that erode equity.

2. **Insufficient Stop‑Loss for High‑Volatility Moves**  
   - Fixed 2% stop‑loss is easily breached when BTC/ETH swing >5% within a few hours. The backtest shows losses of 7–13% on single positions, indicating the stop‑loss is either not being triggered (possibly due to intra‑bar execution logic) or is too wide relative to the actual risk per trade.

3. **Volatility‑Indexed Take‑Profit May Exacerbate Losses**  
   - In high‑volatility regimes, the percentile rank of volatility approaches 1.0, inflating TP to `2 * base_tp` (up to 10%). This widens the profit target while the market continues moving against the position, increasing drawdown duration and magnitude.

4. **Equity‑Guard Threshold Mis‑calibrated**  
   - The guard `current_equity < $3.00` is never triggered when starting equity per symbol is $1.00, rendering the intended safety net ineffective. This suggests a parameter‑scope confusion (account‑level vs. symbol‑level equity).

5. **Drawdown Metric Not Capturing True Risk**  
   - `max_drawdown_pct = 0.0` across all series indicates the metric is computed on a reset‑per‑trade basis rather than on the cumulative equity curve. This masks the real drawdown experienced by a portfolio holding multiple concurrent positions.

6. **Position‑Sizing Leverage Amplifies Drawdowns**  
   - The risk multiplier (up to 2.0) combined with equity‑ratio scaling can increase position size when equity is low (since `equity_ratio = current_equity / starting_equity` < 1). This raises risk per trade exactly when the account is under stress, creating a negative feedback loop.

---

## 4. Recommended Research Questions for the Swarm
**For DeepSeek (volume/pattern analysis):**
- Which market regimes (volatility percentiles, trend strength) correlate with the largest drawdown episodes?  
- Can we identify a pattern in the timing of stop‑loss breaches (e.g., after N consecutive candles in the same direction)?

**For Claude (high‑reasoning/logic):**
- How should the scoring system be modified to avoid strong short signals in confirmed uptrends?  
- Propose a dynamic stop‑loss mechanism that scales with recent volatility (ATR‑based) while preserving the 2% risk cap per trade.

**For Gemini (vision/market‑broad analysis):**
- Visualize the equity curve across all symbols and overlay key drawdown periods with macro events (e.g., BTC breakout).  
- Compare the strategy’s performance on BTC/ETH vs. alt‑coins to assess asset‑class bias.

---

## 5. Immediate Action Items for Strategy Architect
1. Verify and correct the drawdown calculation to reflect portfolio‑level equity.
2. Review the equity‑guard threshold and align it with actual starting capital (e.g., change `$3.00` to `$0.03` if per‑symbol equity is $1.00).
3. Consider adding a trend‑filter (e.g., require SMA fast > SMA slow for long signals, opposite for shorts) or at least attenuate short scores in strong uptrends.
4. Test a volatility‑scaled stop‑loss (e.g., `stop_loss_pct = max(1.5%, 0.5 * ATR / entry_price * 100)`).
5. Re‑evaluate the leverage multiplier: cap risk multiplier at 1.0 when `equity_ratio < 0.8` to avoid over‑exposure during drawdowns.

---

*End of brief. Ready for distribution to research agents.*
