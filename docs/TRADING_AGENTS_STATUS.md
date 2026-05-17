# Trading Agents Status

**Last updated: 2026-05-15**

---

## EA Trader v10.1 (XAUUSD / XAGUSD / EURUSD / GBPUSD)

- **File**: `agents/trading-agent/live_trading_ea.py`
- **Start**: `python3 liveea.py` (root launcher)
- **Stop**: `python3 stopea.py`
- **Status**: RUNNING in nohup
- **Account**: ICMarketsSC-Demo #52878487 | Balance: $4,430.86 | trades=757 | streak=+5
- **Version**: v10.1

### Signal Architecture
- 3-pillar signal: trend (EMA stack) + RSI divergence + Bollinger structure
- **H1 EMA bias filter**: Longs only above H1 EMA, shorts only below
- **Breakout score boost**: +2 added to breakout detection (entry requires score≥6)
- Session-aware regimes: ASIAN (22-07 UTC), LONDON (07-12), NY (13-21)

### Risk Management
- Prop-firm safe: 3% daily limit, 5% max drawdown
- XAUUSD: 0.05L hard cap | XAGUSD: 0.01L always | EURUSD/GBPUSD: 0.01L default
- LONDON_NY overlap: trailing stop tightened to 10 pips
- NY_CLOSE: TREND regime now active (unblocked in v10)

### Regime Behavior
- **RANGE regime**: mean-reversion mode, score≥4 required, REVERSE disabled
- **NY_CLOSE regime**: REVERSE mode disabled
- **REVERSE mode**: threshold 3→5 (v10.1), 3-cycle cooldown post-exit, disabled in RANGE/NY_CLOSE
- **NEUTRAL noise filter**: score≥4 required in RANGE and NEUTRAL regimes

### GoldBasket_v4.1
- Added **Window_7to9am**: London open window (07:00–09:00 UTC)
- Existing windows: London (07-12), NY (13-21), Asian (22-07), combined baskets

---

## Binance Scalper v9.1 (BTC / ETH / BNB / SOL / XRP / ADA / DOGE)

- **File**: `agents/trading-agent/live_trading_binance.py`
- **Start**: `python3 startbinance.py` (root launcher)
- **Stop**: `python3 stopbinance.py`
- **Status**: RUNNING via nohup + PID file
- **Balance**: $4,502.09 | trades=5,533 | pnl_today=+$16.93
- **Version**: v9.1 — 7 symbols, ATR-based risk, market intelligence

### Signal Architecture
- 10-second tick rate, 60-second max hold
- MIN_STRENGTH: 0.55, MAX_OPEN: 4
- Volume momentum filter: trade blocked when volume < 20-bar MA
- **Live market intelligence**: composite BEAR/BULL/NEUTRAL bias (±0.3 score impact)
  - Fear/Greed: alternative.me | BTC dominance: CoinGecko
  - Alpaca H1 trend | Binance 4H macro | CryptoCompare news sentiment
  - Log tag: `mi:B/N/b` on every tick line
  - **Current bias (2026-05-15)**: BEAR | Fear/Greed=43

### Risk Management (v9 + v9.1)
- **ATR-based SL/TP**: dynamic levels derived from live ATR (not fixed pips)
- **Zero-ATR guard**: division-by-zero protection during flash crashes
- **Daily -$300 circuit breaker**: pauses 1 hour when daily loss exceeds $300
- **Daily P&L reset**: resets at 00:00 UTC
- **Early timeout exit**: closes position at -0.3% when ≤30s before timeout
- **Partial TP at 1×ATR**: closes 50% at first target, moves SL to breakeven
- **Leverage halved on -3 streak**: reduced for next 3 trades after 3 consecutive losses

### Position Sizing
- BTC: $5 equity | ETH: $3 equity | BNB: $2 equity | Others: $1.50 equity
- Max leverage: 75x (reduced from 150x)
- Dynamic leverage: starts at 50% max, scales with win-rate track record

---

## Automode v5

- **File**: `automode.py` (root) — delegates to `core/orchestration/automode.py`
- **Fixes (2026-05-15)**: GSD `--project-dir` → `--add-dir` flag fixed; PAI `is_pai_installed()` false-negative fixed (resolved 555 silent failures)
- **Queues**: `task_queue.pending`, `task_queue.completed`, `task_queue.failed`
- **Task stats (2026-05-15)**: 19 pending, 1 in_progress, 30+ completed, 4 failed (GSD gsd-progress tasks)
- **Agents**: hermes, opencode, pi.dev, openclaw, researcher, social, pai, gsd,
              hermes_trade, opencode_trade, pidev_monitor
- **LLM routing**: All agents now use NVIDIA NIM direct (no OpenRouter)

---

## Launcher Reference

| Command | Action |
|---------|--------|
| `python3 liveea.py` | Start EA Trader v10.1 |
| `python3 stopea.py` | Stop EA + close all MT5 positions |
| `python3 startbinance.py` | Start Binance Scalper v9.1 |
| `python3 stopbinance.py` | Stop Binance Scalper |
| `python3 automode.py` | Start autonomous swarm |
