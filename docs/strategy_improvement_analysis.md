# Strategy Improvement Analysis

## Date: 2026-05-11

## 1. FreqTrade Backtest Data Analysis

### Raw Results Summary

| Version | Timerange | Leverage | Return | Trade Count | Final Balance |
|---------|-----------|----------|--------|-------------|---------------|
| V5 | Jan-May 2024 | 1x | -3.17% | 1,464 | $968.29 |
| V6 | Jan-Mar 2024 | 1x | +22.02% | 1,092 | $1,220.16 |
| V6 | Jan-Mar 2024 | 3x | +56.0% (est) | 1,092 | ~$1,560 |
| V6 | Jan-Mar 2024 | 5x | +82.6% (est) | 1,092 | ~$1,826 |
| V7 | Jan-Mar 2024 | 1x | +22.02% | 1,092 | $1,220.16 |
| V7 | Jan-Mar 2024 | 5x | +82.59% | 1,092 | $1,825.91 |

### Critical Issues Identified

1. **Overtrading**: 1,092 trades in 90 days = 12+ trades/day. The strategy is trading nearly every hourly candle rather than selecting high-probability setups.

2. **V5 Lost Money Over 4 Months**: The -3.17% return over Jan-May 2024 (a bull market for BTC) indicates the strategy catches too many false signals.

3. **V6/V7 Identical Results**: These versions produced identical trade counts and returns, suggesting V7 changes were cosmetic rather than substantive.

4. **No Time Filter**: Trades occurring at all hours including 00:00-04:00 UTC when BTC/USDT liquidity is lower and spreads wider.

5. **Win Rate Issue**: Individual trade PnL analysis shows roughly 48-52% win rate with small average wins/losses (0.2-0.5% per trade), meaning the edge is extremely thin and fragile.

### V8 Strategy Improvements Applied

- **Time-of-day filter**: Block trading during UTC 0-4 and 22-23 (low liquidity)
- **Raised entry thresholds**: ADX 25+ (was 20), volume 1.5x avg (was 1.0x)
- **Added Stochastic RSI**: Secondary confirmation prevents premature entries
- **Added ROC momentum**: Prevents entering against short-term momentum
- **Cooldown period**: Minimum 3 hours between trades (reduces from 12/day to max 5-6/day)
- **Directional filter (+DI/-DI)**: Confirms trend direction before entry
- **Tighter stoploss (-3.5%)**: Improved from -5%, better R:R ratio
- **Extended max hold (6h)**: Data shows winning trades need more time to develop
- **Day-of-week sizing**: Reduced exposure Wed/Thu (historically weaker days)
- **Dynamic leverage (2-3x)**: Adaptive based on market conditions

### Expected Impact

- Trade frequency: ~1,092 -> estimated 200-350 trades (higher quality)
- Win rate: ~50% -> target 55-60% with stronger filters
- Average R:R: ~1.0 -> target 1.5-2.0 with tighter stops and wider targets
- Drawdown: Should reduce 40-60% due to fewer trades and tighter risk

---

## 2. EA Trade Data Analysis (MasterMetalsEA)

### Dataset: Feb 2-13, 2026 | ~370 trades across XAUUSD, XAGUSD, XPTUSD, US30, NDX100

### Performance by Symbol

| Symbol | Profitable Trades | Losing Trades | Net Performance |
|--------|-------------------|---------------|-----------------|
| XAGUSD | High (many $50K+ winners) | Moderate | Strongly positive |
| XAUUSD | Moderate | High frequency small losses | Mixed |
| XPTUSD | Good on buys | Poor on sells | Positive on buys |
| US30 | Mixed | Significant losses ($10K+) | Negative |
| NDX100 | Mixed | Large loss events | Negative |

### Key Findings from Trade Data

#### Profitable Patterns
- **Large winners** cluster in hours 1-3, 6, 8-9, 13, 15-17 UTC
- **XAGUSD Buy** in hours 1-3 and 8-9: Enormous wins ($70K-$202K per trade)
- **XAGUSD Sell** in hours 2-6 and 13: Very profitable ($50K-$172K)
- **Synchronized basket trades** (XAU+XAG together) have highest success
- **Longer hold times** (4-24h) produce the biggest winners
- **Monday and early-week** trades outperform significantly

#### Loss Patterns
- **Hours 4-5, 7, 10-12**: High frequency of small losses ($500-$3000)
- **XAUUSD Sell** during strong uptrends (Feb 3-4): Large losses ($8K-$17K)
- **Short hold times** (< 5 min): Mostly losers due to spread costs
- **Wednesday/Thursday**: Higher loss frequency
- **Hour 22-23**: Poor performance (end of session, thin liquidity)
- **Over-leveraged positions** (9 lots): Higher loss magnitude
- **US30 and NDX100**: Net losers - should be excluded or heavily filtered

#### Win Rate by Direction
- **Buy signals**: ~63% win rate (aligns with GoldBasket_v4 data)
- **Sell signals**: ~53% win rate
- Sell signals require higher conviction to justify entry

### V56 EA Improvements Applied

#### Risk Management
- BasketRiskPct: 2.5% -> 2.0% (smaller bets)
- MaxConsecutiveLosses: 5 -> 3 (faster defense mode)
- Added MaxDailyLoss cap ($15K)
- Added XAU-XAG correlation filter (> 0.50 required)
- Added spread filter (max 35 points)

#### Entry Timing
- AvoidHours expanded: "5,6,8,23" -> "4,5,7,10,11,12,22,23"
- HotHours updated based on actual profit data: "1,2,3,6,8,9,13,15,16,17"
- ATRSpike_Event: 1.12 -> 1.15 (higher threshold for fewer, better signals)
- EventWindowMinutes: 60 -> 45 (tighter window)
- Added Friday 18:00+ block (weekend gap risk)
- Added news lockout (first 5 min of each hour)
- MinScoreToTrade: 3.5 -> 4.0

#### Exit Logic
- Partial_RR: 1.20 -> 1.40 (let winners breathe)
- TrailStart_RR: 1.60 -> 1.50 (lock gains slightly earlier)
- WinnerFloor_RR: 0.80 -> 0.90 (higher floor)
- TP2_RR_Normal: 2.0 -> 2.5 (bigger targets)
- Added TP2_RR_HotHour: 3.0 (extended targets in proven windows)
- ScratchMinutes: 30 -> 20 (exit dead trades faster)
- ScratchLoss_R: -0.50 -> -0.35 (tighter scratch threshold)
- MaxHoldMinutes: 240 -> 300 (data shows big winners need 5h+)
- Added breakeven at 1.0R (capital protection)

#### Day-of-Week Multipliers
- Monday: 1.10 -> 1.15 (data confirms strong day)
- Wednesday: 0.70 -> 0.55 (significantly weaker)
- Thursday: 0.80 -> 0.75

#### New Features
- Multi-timeframe RSI confirmation
- XAU-XAG correlation gate
- Daily PnL tracking with hard stop
- Breakeven management at 1.0R
- Hot hour detection for extended targets
- Position size halving in defense mode

### Expected Impact (EA)
- Trade frequency: Reduced ~30% (higher quality entries)
- Win rate: Target 60%+ (from ~57.9%)
- Average winner: Should increase with larger TP targets
- Max drawdown: Should decrease 40-50% with tighter scratches and daily cap
- Profit factor: Target 10+ (from 8.96)

---

## 3. Summary of Changes Made

### Files Modified
- `agents/trading-agent/freqtrade_strategy_testnet.py` - V8 strategy with optimized parameters

### Files Created
- `agents/trading-agent/mq5/MasterMetalsEA_v56.mq5` - Enhanced EA with data-driven optimizations

### Next Steps
1. Run V8 backtest over same periods to validate improvements
2. Paper trade both strategies for 1-2 weeks before live deployment
3. Monitor correlation filter impact on trade frequency
4. Consider removing US30/NDX100 from EA basket entirely
5. Integrate swarm ML signals for score enhancement
