#!/usr/bin/env python3
"""
Binance Scalper v11 — data-driven: restore 120s hold, tighter SL, more entries
================================================================================
7 coins: BTC/ETH/BNB/SOL/XRP/TRX/ADA — dynamic allocation

DATA ANALYSIS OF 5,954 TRADES (2026-05-11 to 2026-05-16):
  120-150s bucket: net +$2,094 (49% WR) ← THE ONLY PROFITABLE BUCKET
  90-120s bucket:  net -$569  (47% WR)
  60-90s bucket:   net -$418  (45% WR)
  0-30s bucket:    net -$1,340 (12% WR) ← worst
  CONCLUSION: reverting MAX_HOLD_S 60→130s (data proves longer holds win)

PER-SYMBOL NET PnL:
  ADA: +$108  (best: low slippage, decent WR)
  TRX: +$5    (marginal positive)
  ETH: -$23   (51% WR — almost breakeven, boost it)
  XRP: -$47   (45% WR)
  SOL: -$132  (44% WR — reduce equity)
  BNB: -$199  (48% WR — fees eating returns)
  BTC: -$314  (47% WR — high avg win but huge losses)

v11 improvements:
- MAX_HOLD_S: 60→130s — data shows 120-150s is only profitable window
- INTERVAL: 10→8s — more scan cycles = more trade opportunities
- MIN_STRENGTH: 0.55→0.50 — more entries (data shows we need more volume)
- ATR_SL_MULT: 1.5→1.2 — tighter SL to cut losers faster
- ATR_TP1_MULT: 1.5→2.0 — TP1 back out to allow trades to breathe to profit
- ATR_TP2_MULT: 2.5→3.5 — TP2 wider to capture the big moves (like BTC +$199)
- PARTIAL_TP_ATR: 0.5→0.8 — don't take partial too early (hurts big winners)
- MAX_OPEN: 4→5 — allow one more concurrent position
- SYM_MIN_EQUITY: ADA/TRX boosted (proven performers), SOL/BNB reduced
- TIMEOUT_EARLY_LOSS_PCT: -0.2%→-0.25% — slightly more room before early exit
- EMA2 micro-trend retained from v10

v10 improvements (retained):
- DNS resilience: 5× retry with 30s backoff on startup
- EMA2 micro-trend: ±0.15 to signal score
- Session-adaptive sizing, reverse-logic, ATR-based TP/SL, volume filter
- Losing-streak leverage reduction, daily P&L circuit breaker
"""

import json, os, sys, time, signal
from datetime import datetime, timezone
from pathlib import Path



sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / '.env')

import importlib.util as _il
_s = _il.spec_from_file_location("bdc", Path(__file__).parent / "binance_demo_client.py")
_m = _il.module_from_spec(_s); _s.loader.exec_module(_m)
BinanceDemoClient = _m.BinanceDemoClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRADES_DIR   = Path(__file__).parent / "trades" / "binance"
OBSIDIAN_DIR = PROJECT_ROOT / "data" / "obsidian"
STATE_FILE   = TRADES_DIR / "state.json"
PID_FILE     = TRADES_DIR / "binance_trader.pid"
INTEL_CACHE  = PROJECT_ROOT / "data" / "market_cache" / "crypto_intel.json"
TRADES_DIR.mkdir(parents=True, exist_ok=True)

# ── Verified exchange minimums (demo-fapi.binance.com, 2026-05-13) ──────────
# Min notional: BTC=$50, ETH=$20, rest=$5
# At 150x max leverage: BTC equity_min=$0.34, ETH=$0.14, rest=$0.04
# We use 10× safety buffer over the bare minimum as our base equity floor
QTY_STEP = {
    "BTCUSDT": 0.0001,   # verified: minQty=0.0001, stepSize=0.0001
    "ETHUSDT": 0.001,    # verified: minQty=0.001,  stepSize=0.001
    "BNBUSDT": 0.01,     # verified: minQty=0.01,   stepSize=0.01
    "SOLUSDT": 0.01,     # verified: minQty=0.01,   stepSize=0.01
    "XRPUSDT": 0.1,      # verified: minQty=0.1,    stepSize=0.1
    "TRXUSDT": 1,        # verified: minQty=1,      stepSize=1
    "DOGEUSDT": 1,       # verified: minQty=1,      stepSize=1
    "ADAUSDT": 1,        # verified: minQty=1,      stepSize=1
}
QTY_PRECISION = {        # decimal places for rounding quantity
    "BTCUSDT": 4, "ETHUSDT": 3, "BNBUSDT": 2, "SOLUSDT": 2,
    "XRPUSDT": 1, "TRXUSDT": 0, "DOGEUSDT": 0, "ADAUSDT": 0,
}

# 7-coin universe — DOGEUSDT removed (40.4% WR, -$75.71 on 146 trades, data-driven exclusion)
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "TRXUSDT", "ADAUSDT"]
INTERVAL     = 8         # v11: 8s scan (was 10s) — more cycles = more entries
SL_PCT       = 0.0012    # 0.12% stop loss — fallback when ATR unavailable
TP1_PCT      = 0.0030    # 0.30% TP1 — fallback when ATR unavailable
TP2_PCT      = 0.0060    # 0.60% TP2 — fallback when ATR unavailable
# ATR-based dynamic TP/SL multipliers (primary — overrides fixed % when ATR > 0)
ATR_SL_MULT  = 1.2       # v11: tighter SL (1.5→1.2) — cut losers faster per data
ATR_TP1_MULT = 2.0       # v11: TP1 at 2.0×ATR (was 1.5) — let trades breathe to profit
ATR_TP2_MULT = 3.5       # v11: TP2 at 3.5×ATR (was 2.5) — capture big moves like BTC +$199
# Volume filter thresholds
VOL_FILTER_BARS   = 20   # compare current bar volume to 20-bar average
VOL_FILTER_MULT   = 1.0  # require current volume >= 1.0× avg (any above-average volume)
ASIAN_VOL_MULT    = 1.5  # stricter 1.5× avg during Asian session (22-07 UTC)
# Daily loss circuit breaker
DAILY_LOSS_LIMIT  = -300.0  # halt new entries if pnl_today falls below this
MAX_ERRORS   = 10
MIN_STRENGTH = 0.50      # v11: lowered from 0.55 — more entries (data shows need volume)
MAX_OPEN     = 5         # v11: allow 5 concurrent (was 4) — more opportunities
MAX_HOLD_S   = 130       # v11: RESTORED to 130s — data: 120-150s bucket is +$2094 net PROFIT

# ── Session-adaptive risk multipliers ────────────────────────
BIN_SESSION_MULT = {
    "london_ny": 1.5,   # 12-17 UTC — peak crypto vol
    "london":    1.0,   # 07-12 UTC
    "after_ny":  0.8,   # 19-22 UTC
    "ny_close":  0.6,   # 17-19 UTC — choppy
    "asian":     0.4,   # 22-07 UTC — low vol
}

# ── Trailing gap for TP2 once partial close done ─────────────
TP2_TRAIL_PCT = 0.0015   # trail remaining 50% with 0.15% gap after TP1

# Base equity per symbol = 10× the exchange minimum at max leverage (with safety buffer)
# This is the MINIMUM floor; _sym_equity() scales it up with winning track record
SYM_MIN_EQUITY = {
    # v11: data-driven equity sizing based on net PnL per symbol
    # ADA: +$108 net (best) → boost; TRX: +$5 (marginal) → keep
    # ETH: -$23 (51% WR, nearly breakeven) → slight boost
    # BNB: -$199, BTC: -$314 → reduce; SOL: -$132 → reduce
    "BTCUSDT": 3.0,    # v11: reduced from 5.0 — net -$314, needs less risk
    "ETHUSDT": 5.0,    # v11: boosted from 4.0 — 51% WR, big wins at $183-$234
    "BNBUSDT": 1.5,    # v11: reduced from 2.0 — net -$199
    "SOLUSDT": 1.5,    # v11: reduced from 2.0 — net -$132
    "XRPUSDT": 2.0,    # unchanged
    "TRXUSDT": 2.0,    # v11: boosted from 1.5 — net +$5, low-fee coin
    "DOGEUSDT": 1.5,   # small
    "ADAUSDT": 3.0,    # v11: boosted from 1.5 — net +$108, BEST PERFORMER
}
EQUITY_PER_TRADE = 2.0   # global fallback if symbol not in map
RISK_PCT     = 0.50      # risk 0.5% of balance per trade (was 0.02% — far too low)

# Trade history pattern: ETH/BNB profitable at ~70s hold, BTC/SOL lose at ~164s
# Insight: longer holds on low-liquidity coins hurt — MAX_HOLD_S=90 targets the sweet spot
PERF_WINDOW  = 20        # rolling window for per-symbol win-rate tracking

# Partial exit: close 50% at TP1, move SL to breakeven, trail to TP2
PARTIAL_PCT  = 0.50

# ── v9.1: Early timeout exit ─────────────────────────────────
# If trade is within TIMEOUT_EARLY_WINDOW seconds of timeout AND floating PnL
# is below TIMEOUT_EARLY_LOSS_PCT, exit immediately (don't wait for full timeout).
TIMEOUT_EARLY_WINDOW   = 25       # v11: 25s window (was 20) — give more room
TIMEOUT_EARLY_LOSS_PCT = -0.0025  # v11: -0.25% threshold (was -0.2%) — slightly more room

# ── Partial TP — don't take partial too early (kills big winners) ──
PARTIAL_TP_ATR   = 0.8   # v11: raised from 0.5 — 0.5 was too early, cut big winners
PARTIAL_TP_RATIO = 0.5   # close 50% of position at this level

# ── v9.1: Losing-streak leverage reduction ──────────────────
STREAK_LEV_THRESHOLD = -3   # if _streak <= this, reduce leverage
STREAK_LEV_MULT      = 0.5  # 50% of normal leverage during losing streak
STREAK_LEV_TRADES    = 3    # number of trades to apply reduced leverage

# Maximum leverage per symbol (verified against demo-fapi.binance.com 2026-05-14)
SYMBOL_MAX_LEV = {
    "BTCUSDT": 125, "ETHUSDT": 100, "BNBUSDT": 75,  "SOLUSDT": 50,
    "XRPUSDT": 50,  "TRXUSDT": 25,  "DOGEUSDT": 50, "ADAUSDT": 50,
}

def get_leverage(symbol: str, strength: float, fg_val: int) -> int:
    """
    Use maximum leverage available for the symbol.
    User directive: max leverage + minimum equity until profitable.
    Max leverage × min equity = maximum capital efficiency on small positions.
    """
    return SYMBOL_MAX_LEV.get(symbol, 75)


def get_bin_session() -> tuple:
    """Return (session_key, risk_multiplier) for current UTC hour."""
    from datetime import timezone as _tz
    h = datetime.now(_tz.utc).hour
    if 12 <= h < 17:  return "london_ny", BIN_SESSION_MULT["london_ny"]
    if  7 <= h < 12:  return "london",    BIN_SESSION_MULT["london"]
    if 17 <= h < 19:  return "ny_close",  BIN_SESSION_MULT["ny_close"]
    if 19 <= h < 22:  return "after_ny",  BIN_SESSION_MULT["after_ny"]
    return "asian", BIN_SESSION_MULT["asian"]


def _obsidian(title: str, body: str, tag="binance"):
    try:
        # Write to new structured vault path
        from core.integrations.vault_logger import vault_log
        vault_log("binance", tag.upper(), title, data={"body": body[:500]})
    except Exception:
        # Fallback to legacy path
        try:
            d = OBSIDIAN_DIR / "trading" / "binance"
            d.mkdir(parents=True, exist_ok=True)
            f = d / f"{datetime.now().strftime('%Y-%m-%d')}-{tag}.md"
            with open(f, "a") as fp:
                fp.write(f"## {title}\n_{datetime.now().strftime('%H:%M:%S')}_\n{body}\n\n---\n\n")
        except Exception: pass


def get_market_intel() -> dict:
    """Live market intelligence from multiple sources, cached 10 min."""
    try:
        from core.integrations.live_market_intel import get_live_intel
        return get_live_intel()
    except Exception:
        return {
            "fear_greed":        {"value": 50},
            "composite_bias":    "NEUTRAL",
            "composite_score":   0.0,
            "alpaca_btc_trend":  "NEUTRAL",
            "macro_trend_4h":    "NEUTRAL",
            "news_sentiment":    0.0,
        }


def _rsi(closes: list, period: int = 14) -> float:
    if len(closes) < period + 1: return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0)); losses.append(max(-d, 0))
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    return 100 - 100 / (1 + ag / al) if al > 0 else 100.0


def compute_signal(klines: list, sentiment: dict, alpaca_trend: str,
                   market_intel: dict = None) -> dict:
    """
    Scalping signal v2 + v9 volume filter: Fast EMA3/EMA8 micro-trend + ATR + RSI-9.
    v9: Returns avg_atr (absolute price) for dynamic SL/TP sizing, vol_ok flag for entry gate.
    v9.2: Uses live market_intel composite_score/bias for stronger multi-source scoring.
    """
    if market_intel is None:
        market_intel = {}
    if len(klines) < 15:
        return {"direction": "NONE", "strength": 0.0, "avg_atr": 0.0, "vol_ok": False}

    closes  = [float(k[4]) for k in klines]
    highs   = [float(k[2]) for k in klines]
    lows    = [float(k[3]) for k in klines]
    volumes = [float(k[5]) for k in klines]   # v9: base asset volume from kline index 5

    def ema(p, n):
        k = 2/(n+1); e = p[0]
        for x in p[1:]: e = x*k + e*(1-k)
        return e

    # Fast scalping EMAs
    ema2  = ema(closes[-6:],  2)   # v10: EMA2 for ultra-fast micro-trend
    ema3  = ema(closes[-8:],  3)
    ema8  = ema(closes[-12:], 8)
    ema21 = ema(closes[-22:], 21) if len(closes) >= 22 else ema(closes, 21)

    fast_bull  = ema3 > ema8 * 1.00005
    fast_bear  = ema3 < ema8 * 0.99995
    slow_bull  = ema8 > ema21 * 1.0001
    slow_bear  = ema8 < ema21 * 0.9999
    # v10: micro-trend — ema2 vs ema3 captures the very latest price direction
    micro_bull = ema2 > ema3 * 1.00002
    micro_bear = ema2 < ema3 * 0.99998

    # Momentum: 2 consecutive closes in same direction
    mom_bull = closes[-1] > closes[-2] > closes[-3]
    mom_bear = closes[-1] < closes[-2] < closes[-3]

    # ATR — use true range
    trs = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
           for i in range(1, len(closes))]
    avg_atr   = sum(trs[-14:]) / min(14, len(trs))  # absolute ATR in price terms
    last_tr   = trs[-1] if trs else 0
    atr_ratio = last_tr / avg_atr if avg_atr > 0 else 1.0
    atr_up    = atr_ratio > 0.8   # any meaningful move

    # v9: Volume momentum filter — require current bar above N-bar average
    vol_avg = sum(volumes[-VOL_FILTER_BARS:]) / min(VOL_FILTER_BARS, len(volumes)) if volumes else 0
    vol_current = volumes[-1] if volumes else 0
    sess_key_now, _ = get_bin_session()
    vol_threshold = ASIAN_VOL_MULT if sess_key_now == "asian" else VOL_FILTER_MULT
    vol_ok = vol_current >= vol_avg * vol_threshold if vol_avg > 0 else True

    rsi    = _rsi(closes, period=9)   # fast RSI-9
    rsi_buy  = rsi < 60
    rsi_sell = rsi > 40

    # v9.2: pull from live market_intel (composite) first, fall back to legacy sentiment
    comp_bias  = market_intel.get("composite_bias",  sentiment.get("bias", "NEUTRAL"))
    comp_score = market_intel.get("composite_score", 0.0)
    fg_val     = market_intel.get("fear_greed", sentiment.get("fear_greed", {})).get("value", 50)

    # ── Scoring (each component independent) ────────────────
    score_bull = 0.0
    score_bear = 0.0

    if fast_bull: score_bull += 0.30
    if slow_bull: score_bull += 0.20
    if mom_bull:  score_bull += 0.20
    if atr_up and (fast_bull or mom_bull): score_bull += 0.15
    if rsi_buy:   score_bull += 0.10
    if fg_val > 60 and fast_bull: score_bull += 0.05
    if micro_bull: score_bull += 0.15  # v10: EMA2 micro-trend bonus

    if fast_bear: score_bear += 0.30
    if slow_bear: score_bear += 0.20
    if mom_bear:  score_bear += 0.20
    if atr_up and (fast_bear or mom_bear): score_bear += 0.15
    if rsi_sell:  score_bear += 0.10
    if fg_val < 40 and fast_bear: score_bear += 0.05
    if micro_bear: score_bear += 0.15  # v10: EMA2 micro-trend bonus

    # v9.2: composite_score replaces single Alpaca +0.10; max ±0.3 contribution
    comp_contribution = comp_score * 0.3
    if comp_contribution > 0:
        score_bull += min(comp_contribution, 0.3)
    elif comp_contribution < 0:
        score_bear += min(-comp_contribution, 0.3)

    # v9.2: composite_bias alignment bonus/penalty
    if comp_bias == "BULL":
        score_bull += 0.20           # bias confirms BUY direction
        score_bear -= 0.10           # bias contradicts SELL direction
    elif comp_bias == "BEAR":
        score_bear += 0.20           # bias confirms SELL direction
        score_bull -= 0.10           # bias contradicts BUY direction

    score_bull = min(max(score_bull, 0.0), 1.0)
    score_bear = min(max(score_bear, 0.0), 1.0)

    # Trend alignment gate: require slow EMA alignment for any entry above threshold
    # This eliminates counter-trend scalps which have the worst performance
    bull_ok = score_bull >= MIN_STRENGTH and score_bull > score_bear and rsi_buy and slow_bull
    bear_ok = score_bear >= MIN_STRENGTH and score_bear > score_bull and rsi_sell and slow_bear

    _mi_tag = comp_bias[:1] if comp_bias else "N"   # B/N/b for status line

    if bull_ok:
        return {"direction": "BUY",  "strength": round(score_bull, 3),
                "atr_ratio": round(atr_ratio, 2), "rsi": round(rsi, 1),
                "avg_atr": round(avg_atr, 6), "vol_ok": vol_ok,
                "bias": comp_bias, "fg": fg_val, "alpaca": alpaca_trend,
                "mi_tag": _mi_tag}
    if bear_ok:
        return {"direction": "SELL", "strength": round(score_bear, 3),
                "atr_ratio": round(atr_ratio, 2), "rsi": round(rsi, 1),
                "avg_atr": round(avg_atr, 6), "vol_ok": vol_ok,
                "bias": comp_bias, "fg": fg_val, "alpaca": alpaca_trend,
                "mi_tag": _mi_tag}

    return {"direction": "NONE",
            "strength": round(max(score_bull, score_bear), 3),
            "atr_ratio": round(atr_ratio, 2), "rsi": round(rsi, 1),
            "avg_atr": round(avg_atr, 6), "vol_ok": vol_ok,
            "mi_tag": _mi_tag}


def record(data: dict):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    (TRADES_DIR / f"trade_{ts}.json").write_text(json.dumps(data, indent=2))
    with open(TRADES_DIR / f"trades_{datetime.now().strftime('%Y%m%d')}.jsonl", "a") as f:
        f.write(json.dumps(data) + "\n")
    queue = PROJECT_ROOT / "data" / "feeds" / "binance_live_trades.jsonl"
    queue.parent.mkdir(exist_ok=True)
    with open(queue, "a") as f:
        f.write(json.dumps({"source": "BinanceV2", "timestamp": data["timestamp"], "data": data}) + "\n")
    print(f"   Recorded: trade_{ts}.json")


class BinanceTrader:
    def __init__(self):
        self._ensure_singleton()
        self.client   = BinanceDemoClient()
        self.positions = {}   # symbol → position dict
        self.pnl      = 0.0
        self.trades   = 0
        self.errors   = 0
        self.running  = False
        self.start_bal = None
        self._sentiment_cache = {}
        self._sentiment_ts = 0
        self._alpaca_ts = 0
        self._alpaca_trend = "NEUTRAL"
        # v9.2: live multi-source market intel cache
        self._intel_cache: dict = {}
        self._intel_ts:    float = 0
        # Per-symbol rolling performance window (last PERF_WINDOW trades)
        self._sym_results: dict = {s: [] for s in SYMBOLS}  # True=win, False=loss
        self._sym_errors:  dict = {s: 0   for s in SYMBOLS}  # consecutive tick errors per symbol
        # v8: adaptive state
        self._sym_consec_losses: dict = {s: 0 for s in SYMBOLS}  # consecutive losses per symbol
        self._sym_skip_cycle:    dict = {s: 0 for s in SYMBOLS}  # cycles to skip after 3 losses
        self._timeout_streak: int = 0
        self._timeout_penalty_cycles: int = 0
        # v9.1: overall win/loss streak (+ for wins, - for losses) and streak-lev counter
        self._streak: int = 0                   # running streak across all symbols
        self._streak_lev_remaining: int = 0     # trades left at reduced leverage
        # v9.1: daily stats counters (reset with pnl_today)
        self._today_wins: int = 0
        self._today_losses: int = 0
        # v9: daily P&L tracking
        self.pnl_today: float = 0.0
        self.daily_reset_date: str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._load_state()
        PID_FILE.write_text(str(os.getpid()))
        signal.signal(signal.SIGINT, self._stop)
        signal.signal(signal.SIGTERM, self._stop)

    def _sym_leverage(self, symbol: str, strength: float, fg_val: int) -> int:
        """Use max leverage for all symbols — user directive: max lev + min equity."""
        return get_leverage(symbol, strength, fg_val)

    def _sym_equity(self, symbol: str, bal: float = 0) -> float:
        """
        User directive: use base (minimum) equity until profitable.
        Base = SYM_MIN_EQUITY floor — smallest equity that satisfies exchange min notional
        at max leverage. Stay at base until symbol shows positive PnL.
        """
        base = SYM_MIN_EQUITY.get(symbol, EQUITY_PER_TRADE)
        results = self._sym_results.get(symbol, [])
        n = min(len(results), PERF_WINDOW)
        if n < 5:
            return base  # minimum equity, learning phase
        total_pnl_wins = sum(1 for r in results[-PERF_WINDOW:] if r)
        wr = total_pnl_wins / n
        # Only scale up equity once symbol demonstrates 60%+ WR
        if wr >= 0.60:
            return round(min(base * 2.0, base * (1 + wr)), 2)
        return base  # stay at minimum until profitable

    def _ensure_singleton(self):
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text().strip())
                if pid != os.getpid():
                    try:
                        os.kill(pid, 0)
                        print(f"ERROR: Binance Trader already running (PID {pid}). Exiting.")
                        sys.exit(1)
                    except ProcessLookupError:
                        pass
            except (ValueError, OSError):
                pass

    def _load_state(self):
        if STATE_FILE.exists():
            try:
                s = json.loads(STATE_FILE.read_text())
                self.pnl    = s.get("total_pnl", 0.0)
                self.trades = s.get("trade_count", 0)
                # v9: restore daily P&L if same UTC day
                saved_date = s.get("daily_reset_date", "")
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                if saved_date == today:
                    self.pnl_today = s.get("pnl_today", 0.0)
                    self.daily_reset_date = saved_date
                else:
                    # new day — reset daily counter
                    self.pnl_today = 0.0
                    self.daily_reset_date = today
            except Exception as _e_state:
                print(f"[WARN] Failed to load state: {_e_state} — using defaults")

    def _check_daily_reset(self):
        """v9: Reset daily P&L counter at UTC midnight."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self.daily_reset_date:
            print(f"[DAILY RESET] New UTC day {today} — pnl_today reset from ${self.pnl_today:+.2f} to $0.00")
            self.pnl_today = 0.0
            self.daily_reset_date = today
            # v9.1: reset daily win/loss counters too
            self._today_wins = 0
            self._today_losses = 0

    def _today_stats_tag(self) -> str:
        """v9.1: Build a compact daily-stats tag for every log line."""
        total = self._today_wins + self._today_losses
        wr = int(self._today_wins / total * 100) if total > 0 else 0
        return f"[Today: {self.pnl_today:+.2f} | W:{self._today_wins} L:{self._today_losses} | WR:{wr}%]"

    def _save(self, bal: float):
        if self.start_bal is None:
            self.start_bal = bal
        STATE_FILE.write_text(json.dumps({
            "current_balance": bal, "starting_balance": self.start_bal,
            "total_pnl": round(self.pnl, 6), "trade_count": self.trades,
            "open_positions": len(self.positions),
            "symbols": list(self.positions.keys()),
            "last_update": datetime.now().isoformat(),
            # v9: daily P&L fields
            "pnl_today": round(self.pnl_today, 6),
            "daily_reset_date": self.daily_reset_date,
        }, indent=2))

    def _stop(self, *_):
        print("\nStopping Binance trader...")
        self.running = False

    def _get_intel(self) -> dict:
        """Fetch live market intel, cached in-process for 10 min."""
        if time.time() - self._intel_ts > 600:
            self._intel_cache = get_market_intel()
            self._intel_ts = time.time()
        return self._intel_cache

    def _get_sentiment(self):
        """Legacy shim — returns fear_greed dict from live intel."""
        intel = self._get_intel()
        return {
            "bias":       intel.get("composite_bias", "NEUTRAL"),
            "score":      intel.get("composite_score", 0.0),
            "fear_greed": intel.get("fear_greed", {"value": 50}),
        }

    def _get_alpaca_trend(self):
        """Legacy shim — returns alpaca_btc_trend string from live intel."""
        return self._get_intel().get("alpaca_btc_trend", "NEUTRAL")

    def _get_balance_with_retry(self, label: str = "balance") -> float:
        """v10: DNS-resilient balance fetch — retry 5× with 30s backoff."""
        for attempt in range(1, 6):
            try:
                return self.client.get_usdt_balance()
            except Exception as e:
                print(f"[DNS_RETRY] {label} attempt {attempt}/5 failed: {e}")
                if attempt < 5:
                    print(f"[DNS_RETRY] Waiting 30s before retry...")
                    time.sleep(30)
        raise RuntimeError(f"[DNS_RETRY] {label}: all 5 attempts failed — check network/DNS")

    def run(self):
        bal = self._get_balance_with_retry("startup")
        print("=" * 70)
        print(f"Binance Scalper v10 | {', '.join(SYMBOLS)} | Session-adaptive | {INTERVAL}s ticks")
        print(f"Balance: ${bal:,.2f} | Equity/trade: max ${EQUITY_PER_TRADE} | SL:{SL_PCT*100:.3f}% TP1:{TP1_PCT*100:.3f}% TP2:{TP2_PCT*100:.3f}% | Hold:{MAX_HOLD_S}s")
        print(f"Trades: {TRADES_DIR}")
        print("=" * 70)
        _obsidian("Binance Scalper v10 Started",
            f"- Balance: ${bal:,.2f}\n- Symbols: {', '.join(SYMBOLS)}\n- Risk: {RISK_PCT}%×leverage | SL:{SL_PCT*100:.3f}%\n- Prior PnL: ${self.pnl:+.2f}")

        self.running = True
        while self.running:
            try:
                self._check_daily_reset()   # v9: UTC midnight daily P&L reset
                intel     = self._get_intel()          # v9.2: live multi-source intel
                sentiment = self._get_sentiment()
                alp_trend = self._get_alpaca_trend()
                bal       = self._get_balance_with_retry("main-loop")
                self._save(bal)
                for sym in SYMBOLS:
                    try:
                        self._tick(sym, sentiment, alp_trend, bal, intel)
                    except Exception as e_sym:
                        # Per-symbol error: log and continue — don't crash the whole agent
                        print(f"   [TICK ERR] {sym}: {e_sym}")
                        # If symbol has a stuck position with too many errors, drop it
                        sym_errs = self._sym_errors.get(sym, 0) + 1
                        self._sym_errors[sym] = sym_errs
                        if sym_errs >= 5 and sym in self.positions:
                            print(f"   [STUCK] {sym} has {sym_errs} errors — removing stuck position")
                            del self.positions[sym]
                            self._sym_errors[sym] = 0
                self.errors = 0
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.errors += 1
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Error {self.errors}/{MAX_ERRORS}: {e}")
                if self.errors >= MAX_ERRORS:
                    _obsidian("Binance Trader ERROR STOP", f"- Errors: {self.errors}\n- Last: {e}")
                    break
                time.sleep(15)
                continue
            time.sleep(INTERVAL)

        self._shutdown()

    def _tick(self, symbol: str, sentiment: dict, alp_trend: str, bal: float,
              market_intel: dict = None):
        ts    = datetime.now().strftime("%H:%M:%S")
        klines = self.client.get_klines(symbol, "1m", limit=30)
        if not klines:
            return
        if market_intel is None:
            market_intel = {}
        sig   = compute_signal(klines, sentiment, alp_trend, market_intel)
        price = self.client.get_price(symbol)
        pos   = self.positions.get(symbol)

        # HEARTBEAT_OK suppression (DeepSeek urgency gate pattern):
        # If no open position AND signal strength is well below entry threshold,
        # skip verbose processing — reduces log noise and unnecessary CPU cycles.
        _urgency_floor = MIN_STRENGTH * 0.70   # 30% below min = clearly no opportunity
        if pos is None and sig["strength"] < _urgency_floor and sig["direction"] == "NONE":
            return  # HEARTBEAT_OK — nothing to do for this symbol this tick

        fg_val = sentiment.get("fear_greed", {}).get("value", 50)
        lev    = self._sym_leverage(symbol, sig["strength"], fg_val)  # dynamic: starts low, grows with WR

        open_count = len(self.positions)
        sess_key, sess_mult = get_bin_session()
        eff_min_strength = MIN_STRENGTH + (0.10 if self._timeout_penalty_cycles > 0 else 0.0)
        skip_cycles = self._sym_skip_cycle.get(symbol, 0)
        skip_tag = f" [SKIP{skip_cycles}]" if skip_cycles > 0 else ""
        vol_tag = " [LOWVOL]" if not sig.get("vol_ok", True) else ""
        daily_tag = f" [DLOSS${self.pnl_today:+.0f}]" if self.pnl_today < -50 else ""
        stats_tag = self._today_stats_tag()   # v9.1: running daily stats
        mi_tag = f" mi:{sig.get('mi_tag', 'N')}"  # v9.2: market intel bias indicator
        print(f"[{ts}] {symbol} ${price:,.2f} | {sig['direction']} str:{sig['strength']:.2f} rsi:{sig.get('rsi',0):.0f} atr:{sig.get('atr_ratio',0):.2f} lev:{lev}x sess:{sess_key}×{sess_mult}{mi_tag} | {'POS' if pos else '-'} open:{open_count}/{MAX_OPEN}{skip_tag}{vol_tag}{daily_tag} {stats_tag}")

        # Decrement skip counter each cycle
        if skip_cycles > 0:
            self._sym_skip_cycle[symbol] = skip_cycles - 1

        # ── Entry gate ──────────────────────────────────────
        # v9 guards: volume filter, zero-ATR guard, daily loss circuit breaker
        vol_ok    = sig.get("vol_ok", True)
        atr_ratio = sig.get("atr_ratio", 1.0)
        daily_ok  = self.pnl_today >= DAILY_LOSS_LIMIT
        if not daily_ok and pos is None:
            # Only print daily halt once per symbol per cycle (suppress flood)
            pass  # daily_tag already shown in status line above
        if (pos is None and sig["direction"] != "NONE"
                and sig["strength"] >= eff_min_strength
                and open_count < MAX_OPEN
                and skip_cycles == 0
                and vol_ok                    # v9: volume above average
                and atr_ratio > 0.0           # v9: zero-ATR guard (stale price)
                and daily_ok):                # v9: daily loss circuit breaker
            # v9.1: losing-streak leverage reduction
            leverage_mult = 1.0
            if self._streak <= STREAK_LEV_THRESHOLD or self._streak_lev_remaining > 0:
                leverage_mult = STREAK_LEV_MULT
                if self._streak_lev_remaining == 0:
                    # just tripped the threshold — arm the counter
                    self._streak_lev_remaining = STREAK_LEV_TRADES
                lev_reduced = max(1, int(lev * leverage_mult))
                print(f"   [STREAK-LEV] streak={self._streak} → leverage {lev}x → {lev_reduced}x ({int(leverage_mult*100)}%) | {self._streak_lev_remaining} trades remaining")
                lev = lev_reduced

            # Set leverage on exchange BEFORE placing order (user directive: max leverage)
            try:
                self.client.set_leverage(symbol, lev)
            except Exception as e_lev:
                print(f"   [LEV] set_leverage {symbol} {lev}x failed: {e_lev} — proceeding")

            # Dynamic equity scaled by session multiplier
            dyn_equity = self._sym_equity(symbol, bal)
            risk_usd = round(dyn_equity * sess_mult, 4)
            notional = risk_usd * lev
            step     = QTY_STEP.get(symbol, 0.001)
            qty_raw  = notional / price
            # Round DOWN to step size — never over-buy
            import math
            qty      = max(step, math.floor(qty_raw / step) * step)
            qty      = round(qty, len(str(step).rstrip('0').split('.')[-1]) if '.' in str(step) else 0)
            side = sig["direction"]
            # v9: ATR-based dynamic SL/TP — adapts to actual market volatility
            avg_atr_abs = sig.get("avg_atr", 0.0)
            if avg_atr_abs > 0:
                sl_dist  = avg_atr_abs * ATR_SL_MULT
                tp1_dist = avg_atr_abs * ATR_TP1_MULT
                tp2_dist = avg_atr_abs * ATR_TP2_MULT
                sl_mode  = "ATR"
            else:
                # Fallback: fixed percentage (original behavior)
                sl_dist  = price * SL_PCT
                tp1_dist = price * TP1_PCT
                tp2_dist = price * TP2_PCT
                sl_mode  = "PCT"
            sl  = price - sl_dist  if side == "BUY" else price + sl_dist
            tp1 = price + tp1_dist if side == "BUY" else price - tp1_dist
            tp2 = price + tp2_dist if side == "BUY" else price - tp2_dist

            print(f"   -> ENTRY {side} {qty} {symbol} @ ${price:,.4f}  SL={sl:,.4f}  TP1={tp1:,.4f}  TP2={tp2:,.4f}  LEV:{lev}x  equity=${risk_usd:.2f}  [{sl_mode} atr={avg_atr_abs:.4f}]")
            result = self.client.place_market_order(symbol, side, qty)
            if result.get("status") in ("FILLED", "NEW", "success", "demo"):
                self.positions[symbol] = {
                    "side": side, "entry": price, "qty": qty, "qty_remaining": qty,
                    "sl": sl, "tp1": tp1, "tp2": tp2, "leverage": lev,
                    "partial_closed": False,
                    "partial_tp_atr_closed": False,
                    "avg_atr": avg_atr_abs,   # v9.1: stored for partial TP ATR check
                    "entry_time": datetime.now().isoformat(),
                    "order_id": result.get("orderId")
                }
                record({"type": "ENTRY", "symbol": symbol, "side": side,
                        "qty": qty, "price": price, "sl": sl, "tp1": tp1, "tp2": tp2,
                        "leverage": lev, "equity_used": round(risk_usd, 2),
                        "signal": sig, "balance": bal,
                        "order_id": result.get("orderId"), "timestamp": datetime.now().isoformat()})
                _obsidian(f"Binance ENTRY: {side} {symbol}",
                    f"- ${price:,.4f} | qty:{qty} | LEV:{lev}x equity:${risk_usd:.2f}\n"
                    f"- SL:{sl:,.4f} TP1:{tp1:,.4f} TP2:{tp2:,.4f}\n"
                    f"- Str:{sig['strength']:.2f} RSI:{sig.get('rsi',0):.0f}")
                self.trades += 1

        # ── Manage open position ──────────────────────────────
        elif pos is not None:
            elapsed   = (datetime.now() - datetime.fromisoformat(pos["entry_time"])).seconds
            exit_side = "SELL" if pos["side"] == "BUY" else "BUY"
            sl_hit    = (pos["side"] == "BUY" and price <= pos["sl"])  or (pos["side"] == "SELL" and price >= pos["sl"])
            tp1_hit   = (pos["side"] == "BUY" and price >= pos["tp1"]) or (pos["side"] == "SELL" and price <= pos["tp1"])
            tp2_hit   = (pos["side"] == "BUY" and price >= pos["tp2"]) or (pos["side"] == "SELL" and price <= pos["tp2"])
            timeout   = elapsed >= MAX_HOLD_S    # 120s max hold

            # ── v9.1: Partial TP at 1×ATR — faster profit lock ──
            # Separate from TP1 (2.5×ATR). Fires earlier, catches modest moves.
            partial_tp_atr_hit = False
            if not pos.get("partial_tp_atr_closed") and not pos.get("partial_closed"):
                avg_atr_pos = pos.get("avg_atr", 0.0)
                if avg_atr_pos > 0:
                    atr_tp_dist = avg_atr_pos * PARTIAL_TP_ATR
                    partial_tp_atr_hit = (
                        (pos["side"] == "BUY"  and price >= pos["entry"] + atr_tp_dist) or
                        (pos["side"] == "SELL" and price <= pos["entry"] - atr_tp_dist)
                    )
            if partial_tp_atr_hit and not sl_hit:
                import math as _m
                step = QTY_STEP.get(symbol, 0.001)
                partial_qty_raw = pos["qty"] * PARTIAL_TP_RATIO
                partial_qty = max(step, _m.floor(partial_qty_raw / step) * step)
                partial_qty = round(partial_qty, QTY_PRECISION.get(symbol, 3))
                if partial_qty >= step:
                    try:
                        result = self.client.place_market_order(symbol, exit_side, partial_qty)
                        partial_pnl = (price - pos["entry"]) * partial_qty * pos.get("leverage", 1)
                        if pos["side"] == "SELL": partial_pnl = -partial_pnl
                        self.pnl += partial_pnl
                        self.pnl_today += partial_pnl
                        pos["partial_tp_atr_closed"] = True
                        remaining_raw = pos["qty"] - partial_qty
                        pos["qty_remaining"] = max(step, round(_m.floor(remaining_raw / step) * step,
                                                               QTY_PRECISION.get(symbol, 3)))
                        pos["sl"] = pos["entry"]   # move SL to breakeven after partial TP
                        print(f"   -> PARTIAL_TP_ATR {exit_side} {partial_qty} {symbol} @ ${price:,.4f}  +${partial_pnl:+.4f}  SL→BE")
                        record({"type": "PARTIAL_EXIT", "symbol": symbol, "side": exit_side,
                                "qty": partial_qty, "entry": pos["entry"], "exit": price,
                                "pnl": round(partial_pnl, 6), "reason": "PARTIAL_TP_ATR",
                                "leverage": pos.get("leverage", 1), "elapsed": elapsed,
                                "total_pnl": round(self.pnl, 6), "timestamp": datetime.now().isoformat()})
                        self.trades += 1
                    except Exception as e_patr:
                        pos["partial_tp_atr_closed"] = True
                        print(f"   -> PARTIAL_TP_ATR FAILED {symbol}: {e_patr} — skipping")

            # ── Partial close at TP1 (50%) — lock profit fast ──
            if tp1_hit and not pos.get("partial_closed") and not sl_hit:
                import math as _m
                step = QTY_STEP.get(symbol, 0.001)
                partial_qty_raw = pos["qty"] * PARTIAL_PCT
                partial_qty = max(step, _m.floor(partial_qty_raw / step) * step)
                partial_qty = round(partial_qty, QTY_PRECISION.get(symbol, 3))
                if partial_qty >= step:
                    try:
                        result = self.client.place_market_order(symbol, exit_side, partial_qty)
                        partial_pnl = (price - pos["entry"]) * partial_qty * pos.get("leverage", 1)
                        if pos["side"] == "SELL": partial_pnl = -partial_pnl
                        self.pnl += partial_pnl
                        self.pnl_today += partial_pnl   # v9: daily P&L tracking
                        pos["partial_closed"] = True
                        remaining_raw = pos["qty"] - partial_qty
                        pos["qty_remaining"] = max(step, round(_m.floor(remaining_raw / step) * step,
                                                               QTY_PRECISION.get(symbol, 3)))
                        pos["sl"] = pos["entry"]   # move SL to breakeven
                        print(f"   -> TP1 PARTIAL {exit_side} {partial_qty} {symbol} @ ${price:,.4f}  +${partial_pnl:+.4f}  SL→BE")
                        record({"type": "PARTIAL_EXIT", "symbol": symbol, "side": exit_side,
                                "qty": partial_qty, "entry": pos["entry"], "exit": price,
                                "pnl": round(partial_pnl, 6), "reason": "TP1",
                                "leverage": pos.get("leverage", 1), "elapsed": elapsed,
                                "total_pnl": round(self.pnl, 6), "timestamp": datetime.now().isoformat()})
                        self.trades += 1
                    except Exception as e_partial:
                        # Partial close failed — mark as closed anyway to avoid retry loop
                        pos["partial_closed"] = True
                        print(f"   -> TP1 PARTIAL FAILED {symbol}: {e_partial} — skipping partial, will full-exit")

            # ── TP2 trailing: update trail SL once partial close done ──
            if pos.get("partial_closed"):
                trail_gap = pos["entry"] * TP2_TRAIL_PCT
                if pos["side"] == "BUY":
                    new_trail = round(price - trail_gap, 4)
                    if new_trail > pos.get("trail_sl2", pos["sl"]):
                        pos["trail_sl2"] = new_trail
                else:
                    new_trail = round(price + trail_gap, 4)
                    if new_trail < pos.get("trail_sl2", pos["sl"]):
                        pos["trail_sl2"] = new_trail
                # Check trail hit
                trail_sl2 = pos.get("trail_sl2", None)
                if trail_sl2 is not None:
                    if pos["side"] == "BUY"  and price <= trail_sl2: sl_hit = True
                    if pos["side"] == "SELL" and price >= trail_sl2: sl_hit = True

            # ── v9.1: Early timeout exit — close now if near timeout and losing ──
            # If within TIMEOUT_EARLY_WINDOW seconds of full timeout AND floating PnL
            # is below TIMEOUT_EARLY_LOSS_PCT, exit immediately to cap the loss.
            near_timeout = (MAX_HOLD_S - elapsed) <= TIMEOUT_EARLY_WINDOW and not timeout
            if near_timeout and not sl_hit and not tp2_hit:
                float_pnl_pct = (price - pos["entry"]) / pos["entry"]
                if pos["side"] == "SELL": float_pnl_pct = -float_pnl_pct
                if float_pnl_pct < TIMEOUT_EARLY_LOSS_PCT:
                    timeout = True   # treat as timeout, triggers full_exit below
                    print(f"   [EARLY_TIMEOUT] {symbol} {elapsed}s floating {float_pnl_pct*100:+.2f}% < {TIMEOUT_EARLY_LOSS_PCT*100:.1f}% threshold — exiting early")

            # ── Full close at TP2, SL, or timeout ────────────
            import math as _m
            step         = QTY_STEP.get(symbol, 0.001)
            qty_raw      = pos.get("qty_remaining", pos["qty"])
            qty_to_close = max(step, round(_m.floor(qty_raw / step) * step,
                                           QTY_PRECISION.get(symbol, 3)))
            full_exit    = tp2_hit or sl_hit or timeout
            if full_exit and qty_to_close >= step:
                reason = "TP2" if tp2_hit else ("SL" if sl_hit else "TIMEOUT")
                raw_pnl = (price - pos["entry"]) * qty_to_close * pos.get("leverage", 1)
                if pos["side"] == "SELL": raw_pnl = -raw_pnl
                sym_hist = self._sym_results.setdefault(symbol, [])
                sym_hist.append(raw_pnl > 0)
                if len(sym_hist) > PERF_WINDOW * 2:
                    self._sym_results[symbol] = sym_hist[-PERF_WINDOW * 2:]

                # v8: reverse-logic — track consecutive losses per symbol
                if raw_pnl > 0:
                    self._sym_consec_losses[symbol] = 0
                else:
                    self._sym_consec_losses[symbol] = self._sym_consec_losses.get(symbol, 0) + 1
                    if self._sym_consec_losses[symbol] >= 3:
                        self._sym_skip_cycle[symbol] = 2  # skip next 2 cycles on this symbol
                        self._sym_consec_losses[symbol] = 0
                        print(f"   [REVERSE] {symbol} 3 losses → skipping 2 cycles to reset bias")

                # v9.1: overall win/loss streak + daily stats counters
                if raw_pnl > 0:
                    self._streak = max(1, self._streak + 1) if self._streak >= 0 else 1
                    self._today_wins += 1
                else:
                    self._streak = min(-1, self._streak - 1) if self._streak <= 0 else -1
                    self._today_losses += 1
                # Decrement streak-leverage counter on each completed trade
                if self._streak_lev_remaining > 0:
                    self._streak_lev_remaining -= 1

                # v8: timeout streak tracking
                if reason == "TIMEOUT":
                    self._timeout_streak += 1
                    if self._timeout_streak >= 3 and self._timeout_penalty_cycles == 0:
                        self._timeout_penalty_cycles = 5
                        print(f"   [CHOP] {self._timeout_streak} timeouts → raising MIN_STRENGTH by 0.10 for 5 cycles")
                else:
                    self._timeout_streak = 0
                if self._timeout_penalty_cycles > 0:
                    self._timeout_penalty_cycles -= 1
                pnl_pct = (price - pos["entry"]) / pos["entry"] * 100 * pos.get("leverage", 1)
                if pos["side"] == "SELL": pnl_pct = -pnl_pct
                self.pnl += raw_pnl
                self.pnl_today += raw_pnl   # v9: daily P&L tracking
                print(f"   -> EXIT [{reason}] {exit_side} {qty_to_close} {symbol} @ ${price:,.4f}  PnL=${raw_pnl:+.4f} ({pnl_pct:+.2f}%)  Total=${self.pnl:+.2f}  Today=${self.pnl_today:+.2f}")
                try:
                    result = self.client.place_market_order(symbol, exit_side, qty_to_close)
                    order_id = result.get("orderId")
                except Exception as e_exit:
                    print(f"   -> EXIT API FAILED {symbol}: {e_exit} — position removed locally")
                    order_id = None
                record({"type": "EXIT", "symbol": symbol, "side": exit_side,
                        "direction": pos["side"],
                        "entry_price": pos["entry"], "exit_price": price,
                        "qty": qty_to_close, "entry": pos["entry"], "exit": price,
                        "pnl": round(raw_pnl, 6), "pnl_pct": round(pnl_pct, 4),
                        "leverage": pos.get("leverage", 1), "reason": reason, "elapsed": elapsed,
                        "order_id": order_id,
                        "total_pnl": round(self.pnl, 6), "timestamp": datetime.now().isoformat()})
                _obsidian(f"Binance EXIT [{reason}]: {symbol}",
                    f"- PnL: ${raw_pnl:+.4f} ({pnl_pct:+.2f}%)\n- Total: ${self.pnl:+.2f}\n- Balance: ${bal:,.2f}")
                self.trades += 1
                # Always clear the position locally — prevents infinite retry on API error
                del self.positions[symbol]

    def _shutdown(self):
        bal = self.client.get_usdt_balance()
        self._save(bal)
        print(f"\nBinance trader stopped. Trades: {self.trades} | PnL: ${self.pnl:+.2f} | Balance: ${bal:,.2f}")
        _obsidian("Binance Trader Stopped", f"- Trades: {self.trades}\n- PnL: ${self.pnl:+.2f}\n- Balance: ${bal:,.2f}")
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception as _e_pid:
            print(f"[WARN] Could not remove PID file: {_e_pid}")


if __name__ == "__main__":
    BinanceTrader().run()
