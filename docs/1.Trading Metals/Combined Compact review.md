**Combined Summary of Precious Metals Mean Reversion Strategy**

Your core objective is to manually execute a refined, intraday relative-value mean reversion strategy for the precious metals basket (XAUUSD/Gold, XAGUSD/Silver, XPTUSD/Platinum). The strategy exploits temporary price dislocations when the normally high correlation (0.85-0.95) between these metals breaks down, betting on subsequent convergence. Empirical analysis of 94 historical trades shows an 86.2% win rate and $3,014,763 profit, validating the edge.

The strategy's logic is explicitly hierarchical: **Correlation** is the gatekeeper, **Volatility Expansion** is the trigger, and **Relative Dislocation (Z-Score Spread)** is the direction selector.

**Entry requires five mandatory, concurrent conditions:**
1.  **Correlation Stress:** The 20-period rolling correlation between the three metals must fall below 0.65 (ideal 0.35-0.55), actively declining from above 0.75, not stale. No entries if correlation is above ~0.65.
2.  **Volatility Expansion:** At least two metals must show an ATR(14) ratio exceeding 1.5x their 20-period average, confirming an overreaction. For Platinum sells or any short leg, require ATR >1.8x due to its higher loss rate.
3.  **Meaningful Dislocation:** The Z-score spread (calculated as [Current Price - 20-period SMA] / 20-period Standard Deviation) between the identified leader (highest Z) and laggard (lowest Z) must exceed 2.5, with the leader above +2.0 and the laggard below -1.5.
4.  **Peak Divergence:** The spread's velocity must be below 0.3 per period, confirming the divergence has peaked and is not still accelerating.
5.  **Optimal Timing:** Execute only during defined liquidity windows. **Tier 1 (Highest Priority):** 10:00-11:00 SAST (London Open), 03:00-05:00 SAST (Asian volatility), 08:00 SAST (pre-London). **Tier 2 (Secondary):** 15:00 SAST (London-NY overlap), 19:00 SAST (NY afternoon). Over 80% of profits came from these specific windows. Avoid Mondays pre-10:00 SAST, Fridays after 15:00 SAST, and days with major news (e.g., NFP at 16:30 SAST).

**Execution & Position Management:**
*   **Direction:** Simultaneously SELL the metal with the highest Z-score (overbought leader) and BUY the metal with the lowest Z-score (oversold laggard). Both market orders must execute within 60 seconds; if one leg fails, immediately close the other.
*   **Sizing:** Risk 2-3% of total capital per basket. Split risk evenly between legs, adjusting for tick value differences to equalize dollar risk, not pip risk. Scale to 3% risk if ATR >2.0x (high volatility regime).
*   **Symbol-Specific Insights:** Silver (XAGUSD) is the strongest performer (96.6% win rate). Prefer setups where Silver or Gold is the laggard to BUY, as BUY trades have a 93% win rate versus SELL trades' 80%. Be exceptionally selective with shorts, especially on Platinum.

**Exit & Risk Management Rules:**
*   **Profit-Taking (Tiered):**
    1.  Take first partial profit (50% of both legs) at a basket profit of $20,000-$25,000 (the median win level).
    2.  Exit the remaining position when either: (a) the Z-score spread compresses by 35% from its entry value, or (b) the average correlation recovers above 0.75.
    *Symbol-specific final profit targets*: Gold ~$25,000, Silver ~$70,000 (can hold longer, avg. 10 hrs), Platinum ~$30,000 (exit aggressively).
*   **Stop-Losses (Mandatory, Basket-Level):**
    1.  Hard stop at a basket loss of $3,000 or 3% account risk.
    2.  Time Stop: Exit if basket is negative after 4 hours (trades rarely recover).
    3.  Correlation Stop: Immediate exit if average correlation rises above 0.75.
    4.  Volatility Stop: Exit if both metals' ATR ratios fall below 1.0x.
    5.  Maximum Hold: Close all positions by 12 hours (median hold is 3.9 hrs).

**Critical Prohibitions & Filters:**
*   **Never trade** non-precious-metal symbols (US30, FX majors, indices, oil). Losses occurred here.
*   **Never trade** outside Tier 1/Tier 2 windows, even if all other conditions are perfect.
*   **Never enter** if correlation is above 0.65, if fewer than two metals show ATR spikes, or if the spread velocity is above 0.3 (still widening).
*   **Never hold** positions over the weekend; close by 18:00 SAST Friday.
*   **Advanced Filter:** Require the metal with the highest absolute Z-score to show above-average tick volume, confirming institutional flow.

**Manual Workflow & Tools (Free-to-Execute):**
Due to TradingView Free plan limits (2 indicators/chart), the manual workflow is essential:
1.  Use MT4/MT5 for charts and execution.
2.  Use a spreadsheet (Excel/Sheets) to manually calculate the 20-period correlation (CORREL function), ATR ratios, and Z-scores, updated every 15-30 mins during trading windows.
3.  On each chart, display only ATR(14) and Standard Deviation(20) indicators, plus a 20-period SMA (does not count against limit).
4.  Follow a strict pre-trade checklist matching all five entry conditions.

**Strategy Thesis & Rationale:**
The edge comes from capturing snap-backs in the metals' historical relationship after short-term institutional flows cause temporary dislocations during specific liquidity windows. The high win rate derives from strict multi-filter confluences (correlation, volatility, dislocation, timing), not from large risk-reward ratios. Automation (EA) was explored but deemed inferior for this strategy, as contextual judgment on correlation regimes and volatility balance is crucial. Success is dependent on disciplined adherence to the rule hierarchy, rigorous trade journaling, and weekly review of win rates and checklist compliance. Expected realistic performance targets for disciplined manual trading are a 65-70% win rate, 10-20 trades monthly, and sustainable compounding growth.