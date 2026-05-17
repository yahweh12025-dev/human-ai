# Trading Performance Summary
Generated: 2026-05-14

---

## EA Agent (live_trading_ea.py) — XAUUSD + XAGUSD

**State as of 2026-05-14T17:18:**
| Metric | Value |
|--------|-------|
| Account | #52878487 @ ICMarketsSC-Demo |
| Balance | $4,471.82 |
| Equity | $4,472.15 |
| Total Trades | 599 |
| Total PnL | +$4.13 |
| PnL Today | -$8.05 |
| Daily Loss % | 0.18% (limit: 3.0%) |
| Drawdown % | 0.38% (limit: 5.0%) |
| Streak | -1 |
| Peak Equity | $4,489.38 |

**Key Findings from Log Analysis (3-day, 184+ trades):**
- Hour 14:00-16:00 UTC: +$900+ gains, 65% WR — PEAK confirmed
- Hour 13:00 UTC: -$518 in only 8 trades, 12.5% WR — WORST HOUR
- Hour 03:00-04:00 UTC: -$137 to -$96 — already blocked
- Score=4 in RANGE regime outperforms score=3 significantly
- Backtest profit factor: 2.63 at 51% WR when hours filtered correctly

---

## Binance Agent (live_trading_binance.py) — Crypto Futures

**State as of 2026-05-14T17:17:**
| Metric | Value |
|--------|-------|
| Balance | $4,706.12 |
| Starting Balance | $4,715.28 |
| Total PnL | +$904.19 |
| Total Trades | 3,693 |
| Open Positions | 0 |

**Per-Symbol Performance (3-day analysis):**
| Symbol | Win Rate | Net PnL | Trades | Decision |
|--------|----------|---------|--------|----------|
| DOGEUSDT | 40.4% | -$75.71 | 146 | REMOVED |
| ETHUSDT | 54.5% | Best performer | — | BOOSTED equity |
| BTCUSDT | — | +$132 total | — | KEEP |
| Others | — | Mixed | — | KEEP |

---

## Implemented Improvements (2026-05-14)

### EA Agent Changes
1. **Blocked hour 13:00 UTC** — added 13 to `BLOCKED_HOURS_UTC`: was `{22,23,0-6}`, now `{13,22,23,0-6}`
   - Data: -$518 in 8 trades (12.5% WR), worst single hour in dataset
2. **Removed hour 13 from `ACTIVE_HOURS_UTC`** — was `{7-13,19-21}`, now `{7-12,19-21}`
3. **Tightened RSI buy threshold**: `rsi_buy = rsi < 65` → `rsi_buy = rsi < 60`
   - Avoids entering longs at RSI 60-63 in RANGE regime (overbought entries)

### Binance Agent Changes
1. **Removed DOGEUSDT** from `SYMBOLS` list (7 coins now, was 8)
   - Data: 40.4% WR, -$75.71 cumulative on 146 trades — confirmed drag on performance
2. **Boosted ETHUSDT base equity**: `SYM_MIN_EQUITY["ETHUSDT"]` 3.0 → 4.0
   - Data: 54.5% WR, best performer in universe — increase allocation
3. **Tightened SL/TP for better R:R**:
   - `SL_PCT`: 0.0020 → 0.0015 (tighter SL)
   - `TP1_PCT`: 0.0030 (unchanged — now 2R vs old 1.5R due to tighter SL)
   - `TP2_PCT`: 0.0060 → 0.0055 (slightly closer for better hit rate)
   - Net result: R:R improves from 1.5R minimum to 2R minimum at TP1

---

## Files Modified
- `agents/trading-agent/live_trading_ea.py`
- `agents/trading-agent/live_trading_binance.py`
