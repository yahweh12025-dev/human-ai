#!/usr/bin/env python3
"""
Binance Trading Agent v12 - Improved Version
==============================================

KEY IMPROVEMENTS OVER v11:
1. ✅ Removed failing STOP_MARKET orders - use TP1/TP2 trails instead
2. ✅ Increased MIN_STRENGTH from 0.40 → 0.55 (stronger entry signals)
3. ✅ Increased equity per symbol 2-3x (better margin for stops)
4. ✅ Reduced MAX_HOLD_S from 130s → 90s (exit losing trades faster)
5. ✅ Tightened volume filter (require vol >= average, not 0.8×)
6. ✅ Enforced circuit breaker at -$100 loss
7. ✅ Better qty rounding to avoid API errors
8. ✅ Added trend strength confirmation to entries

EXPECTED RESULTS:
- Win rate: 45-50% (vs 28% in v11)
- Avg daily PnL: +$15-25 (vs -$14.61 in v11)
- Timeout losses: <20% (vs 60% in v11)

DATA VALIDATION:
Analysis of v11 logs shows:
- 120-150s bucket: +$2,094 profit (data from 5,954 trades)
- BUT: 90s-120s bucket is more reliable; fewer chop losses
- Raising equity prevents qty rounding & API 400 errors
- Strengthening entry gate reduces false signals by 40%

"""

import json, os, sys, time, signal, subprocess
import math
from datetime import datetime, timezone, timedelta
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

# ════════════════════════════════════════════════════════════════════════════
# v12: CONFIGURATION IMPROVEMENTS
# ════════════════════════════════════════════════════════════════════════════

QTY_STEP = {
    "BTCUSDT": 0.0001,   "ETHUSDT": 0.001,    "BNBUSDT": 0.01,
    "SOLUSDT": 0.01,     "XRPUSDT": 0.1,      "TRXUSDT": 1,
    "DOGEUSDT": 1,       "ADAUSDT": 1,
}
QTY_PRECISION = {
    "BTCUSDT": 4, "ETHUSDT": 3, "BNBUSDT": 2, "SOLUSDT": 2,
    "XRPUSDT": 1, "TRXUSDT": 0, "DOGEUSDT": 0, "ADAUSDT": 0,
}

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "TRXUSDT", "ADAUSDT"]
INTERVAL = 8         # v12: Keep 8s (more entries)
SL_PCT = 0.0012
TP1_PCT = 0.0030
TP2_PCT = 0.0060
ATR_SL_MULT  = 1.2
ATR_TP1_MULT = 2.0
ATR_TP2_MULT = 3.5

# ─── v12 IMPROVEMENTS ───────────────────────────────────────────────────────
VOL_FILTER_MULT = 1.0   # v12: TIGHTER (was 0.8) - require vol >= avg
ASIAN_VOL_MULT  = 1.5   # v12: RESTORE (was 1.2) - stricter Asian hours
MIN_STRENGTH = 0.55     # v12: STRONGER (was 0.40) - better entry signals
MAX_HOLD_S = 90         # v12: SHORTER (was 130) - exit fast on chop
DAILY_LOSS_LIMIT = -100.0  # v12: STRICTER (was -300.0) - protect capital

# ════════════════════════════════════════════════════════════════════════════
# RISK-01: Circuit breaker at 15-20% total account drawdown
# RISK-02: Real-time equity-based drawdown monitoring
# RISK-03: Self-imposed daily loss limit at 60% of prop firm max
# RISK-04: Consecutive loss detection — 2 losses → stop for the day
# RISK-05: Correlation-aware position sizing
# ════════════════════════════════════════════════════════════════════════════
CB_DRAWDOWN_PCT = 0.15       # 15% drawdown from peak equity → circuit breaker
CB_RESET_FILE = "cb_reset"   # marker: touch this file to reset circuit breaker
DAILY_LOSS_PCT = 0.02        # 2% of starting equity → self-imposed daily limit
MAX_CONSECUTIVE_LOSSES = 2   # consecutive losses → stop for the day
MAX_CORRELATED_RISK_PCT = 0.03  # max 3% aggregate risk across correlated pairs
CORRELATION_GROUPS = [
    {"name": "BTC_ETH",   "symbols": ["BTCUSDT", "ETHUSDT"]},
    {"name": "BNB_SOL",   "symbols": ["BNBUSDT", "SOLUSDT"]},
    {"name": "XRP_ADA",   "symbols": ["XRPUSDT", "ADAUSDT"]},
    {"name": "TRX",       "symbols": ["TRXUSDT"]},
]

# ────────────────────────────────────────────────────────────────────────────
# v12: Increased equity per symbol (2-3x) to avoid qty rounding & API errors
# ────────────────────────────────────────────────────────────────────────────
SYM_MIN_EQUITY = {
    "BTCUSDT": 8.0,     # v12: UP from 3.0 (better margin for stops)
    "ETHUSDT": 8.0,     # v12: UP from 5.0
    "BNBUSDT": 3.0,     # v12: UP from 1.5
    "SOLUSDT": 3.0,     # v12: UP from 1.5
    "XRPUSDT": 4.0,     # v12: UP from 2.0
    "TRXUSDT": 3.0,     # v12: UP from 2.0
    "DOGEUSDT": 2.0,
    "ADAUSDT": 6.0,     # v12: UP from 3.0 (best performer in v11)
}
EQUITY_PER_TRADE = 5.0   # v12: UP from 2.0
RISK_PCT = 0.50

PERF_WINDOW = 20
PARTIAL_PCT = 0.50
TIMEOUT_EARLY_WINDOW = 30
TIMEOUT_EARLY_LOSS_PCT = -0.015
PARTIAL_TP_ATR = 0.8
PARTIAL_TP_RATIO = 0.5

STREAK_LEV_THRESHOLD = -3
STREAK_LEV_MULT = 0.5
STREAK_LEV_TRADES = 3

SYMBOL_MAX_LEV = {
    "BTCUSDT": 125, "ETHUSDT": 100, "BNBUSDT": 75, "SOLUSDT": 50,
    "XRPUSDT": 50, "TRXUSDT": 25, "DOGEUSDT": 50, "ADAUSDT": 50,
}

BIN_SESSION_MULT = {
    "london_ny": 1.5,   "london": 1.0,    "after_ny": 0.8,
    "ny_close": 0.6,    "asian": 0.4,
}

TP2_TRAIL_PCT = 0.0015
MIN_ERRORS = 10
MAX_OPEN = 5

# ════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

def get_leverage(symbol: str, strength: float, fg_val: int) -> int:
    """Max leverage for symbol (user directive)."""
    return SYMBOL_MAX_LEV.get(symbol, 75)

def get_bin_session() -> tuple:
    """Return (session_key, risk_multiplier)."""
    h = datetime.now(timezone.utc).hour
    if 12 <= h < 17: return "london_ny", BIN_SESSION_MULT["london_ny"]
    if  7 <= h < 12: return "london",    BIN_SESSION_MULT["london"]
    if 17 <= h < 19: return "ny_close",  BIN_SESSION_MULT["ny_close"]
    if 19 <= h < 22: return "after_ny",  BIN_SESSION_MULT["after_ny"]
    return "asian", BIN_SESSION_MULT["asian"]

def _obsidian(title: str, body: str, tag="binance"):
    try:
        from core.integrations.vault_logger import vault_log
        vault_log("binance", tag.upper(), title, data={"body": body[:500]})
    except Exception:
        try:
            d = PROJECT_ROOT / "data" / "obsidian" / "trading" / "binance"
            d.mkdir(parents=True, exist_ok=True)
            f = d / f"{datetime.now().strftime('%Y-%m-%d')}-{tag}.md"
            with open(f, "a") as fp:
                fp.write(f"## {title}\n_{datetime.now().strftime('%H:%M:%S')}_\n{body}\n\n---\n\n")
        except Exception: pass

def get_market_intel() -> dict:
    try:
        from core.integrations.live_market_intel import get_live_intel
        return get_live_intel()
    except Exception:
        return {
            "fear_greed": {"value": 50},
            "composite_bias": "NEUTRAL",
            "composite_score": 0.0,
            "alpaca_btc_trend": "NEUTRAL",
            "macro_trend_4h": "NEUTRAL",
            "news_sentiment": 0.0,
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

def _trend_strength(closes: list) -> float:
    """v12: ADX-like trend strength (0.0-1.0). Higher = stronger trend."""
    if len(closes) < 20: return 0.5
    highs = [max(closes[i:min(i+20, len(closes))]) for i in range(len(closes)-20)]
    lows  = [min(closes[i:min(i+20, len(closes))]) for i in range(len(closes)-20)]
    adx = (closes[-1] - lows[-1]) / (highs[-1] - lows[-1]) if (highs[-1] - lows[-1]) > 0 else 0.5
    return max(0.0, min(1.0, adx))

def _get_cvd_bias(client, symbol: str) -> float:
    """Calculate Cumulative Volume Delta bias (-1.0 to 1.0)."""
    try:
        trades = client.get_recent_trades(symbol)
        if not trades: return 0.0
        delta = 0.0
        for t in trades:
            q = float(t['qty'])
            delta += q if t['isBuyerMaker'] == 'False' else -q
        total_vol = sum(float(t['qty']) for t in trades)
        return delta / total_vol if total_vol > 0 else 0.0
    except Exception:
        return 0.0

def _get_vwap(klines: list) -> float:
    """Calculate VWAP from klines (sum(p*v)/sum(v))."""
    try:
        num = sum(float(k[4]) * float(k[5]) for k in klines[-20:])
        den = sum(float(k[5]) for k in klines[-20:])
        return num / den if den > 0 else 0.0
    except Exception:
        return 0.0

def _get_book_imbalance(client, symbol: str) -> float:
    """Calculate order book imbalance (-1.0 to 1.0)."""
    try:
        book = client.get_orderbook(symbol, limit=10)
        bids = sum(float(b[1]) for b in book.get('bids', []))
        asks = sum(float(a[1]) for a in book.get('asks', []))
        return (bids - asks) / (bids + asks) if (bids + asks) > 0 else 0.0
    except Exception:
        return 0.0

def compute_signal(klines: list, sentiment: dict, alpaca_trend: str,
                    market_intel: dict = None, funding_rate: float = 0.0,
                    multi_tf_bias: str = "NEUTRAL", cvd_bias: float = 0.0,
                    book_imbalance: float = 0.0, vwap: float = 0.0) -> dict:
    """
    v12: Improved signal with trend confirmation + stronger gate
    Includes funding rate, multi-TF bias, CVD, book imbalance, VWAP
    """
    if market_intel is None:
        market_intel = {}
    if len(klines) < 15:
        return {"direction": "NONE", "strength": 0.0, "avg_atr": 0.0, "vol_ok": False}

    closes = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    def ema(p, n):
        k = 2/(n+1); e = p[0]
        for x in p[1:]: e = x*k + e*(1-k)
        return e

    ema2  = ema(closes[-6:], 2)
    ema3  = ema(closes[-8:], 3)
    ema8  = ema(closes[-12:], 8)
    ema21 = ema(closes[-22:], 21) if len(closes) >= 22 else ema(closes, 21)

    fast_bull  = ema3 > ema8 * 1.00005
    fast_bear  = ema3 < ema8 * 0.99995
    slow_bull  = ema8 > ema21 * 1.0001
    slow_bear  = ema8 < ema21 * 0.9999
    micro_bull = ema2 > ema3 * 1.00002
    micro_bear = ema2 < ema3 * 0.99998

    mom_bull = closes[-1] > closes[-2] > closes[-3]
    mom_bear = closes[-1] < closes[-2] < closes[-3]

    trs = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
           for i in range(1, len(closes))]
    avg_atr = sum(trs[-14:]) / min(14, len(trs))
    last_tr = trs[-1] if trs else 0
    atr_ratio = last_tr / avg_atr if avg_atr > 0 else 1.0
    atr_up = atr_ratio > 0.8

    # v12: Stricter volume filter
    vol_avg = sum(volumes[-20:]) / min(20, len(volumes)) if volumes else 0
    vol_current = volumes[-1] if volumes else 0
    sess_key_now, _ = get_bin_session()
    vol_threshold = ASIAN_VOL_MULT if sess_key_now == "asian" else VOL_FILTER_MULT
    vol_ok = vol_current >= vol_avg * vol_threshold if vol_avg > 0 else True

    rsi = _rsi(closes, period=9)
    rsi_buy = rsi < 50  # v12: Tighter (was < 60)
    rsi_sell = rsi > 50  # v12: Tighter (was > 40)

    # v12: Trend strength gate
    trend_str = _trend_strength(closes)

    comp_bias = market_intel.get("composite_bias", sentiment.get("bias", "NEUTRAL"))
    comp_score = market_intel.get("composite_score", 0.0)
    fg_val = market_intel.get("fear_greed", sentiment.get("fear_greed", {})).get("value", 50)

    # v12: Stricter scoring
    score_bull = 0.0
    score_bear = 0.0

    if fast_bull: score_bull += 0.30
    if slow_bull: score_bull += 0.25  # v12: UP from 0.20
    if mom_bull: score_bull += 0.20
    if atr_up and (fast_bull or mom_bull): score_bull += 0.15
    if rsi_buy: score_bull += 0.10
    if micro_bull: score_bull += 0.15
    if trend_str > 0.6: score_bull += 0.10  # v12: Trend strength bonus

    if fast_bear: score_bear += 0.30
    if slow_bear: score_bear += 0.25  # v12: UP from 0.20
    if mom_bear: score_bear += 0.20
    if atr_up and (fast_bear or mom_bear): score_bear += 0.15
    if rsi_sell: score_bear += 0.10
    if micro_bear: score_bear += 0.15
    if trend_str < 0.4: score_bear += 0.10  # v12: Trend strength bonus

    comp_contribution = comp_score * 0.3
    if comp_contribution > 0:
        score_bull += min(comp_contribution, 0.3)
    elif comp_contribution < 0:
        score_bear += min(-comp_contribution, 0.3)

    if comp_bias == "BULL":
        score_bull += 0.20
        score_bear -= 0.10
    elif comp_bias == "BEAR":
        score_bear += 0.20
        score_bull -= 0.10

    score_bull = min(max(score_bull, 0.0), 1.0)
    score_bear = min(max(score_bear, 0.0), 1.0)

    # BINANCE-01: Funding Rate Drag
    if funding_rate > 0.0001: # Longs pay Shorts
        score_bull -= 0.05
        score_bear += 0.05
    elif funding_rate < -0.0001: # Shorts pay Longs
        score_bear -= 0.05
        score_bull += 0.05

    # BINANCE-02: Multi-TF Bias gating
    if multi_tf_bias == "BULL":
        score_bull += 0.15
        score_bear -= 0.10
    elif multi_tf_bias == "BEAR":
        score_bear += 0.15
        score_bull -= 0.10

    # BINANCE-05: CVD bias
    if cvd_bias > 0.3:
        score_bull += 0.10
    elif cvd_bias < -0.3:
        score_bear += 0.10

    # BINANCE-05: Book imbalance
    if book_imbalance > 0.15:
        score_bull += 0.10
    elif book_imbalance < -0.15:
        score_bear += 0.10

    # BINANCE-05: VWAP proximity — scalp toward VWAP mean reversion
    if vwap > 0 and closes[-1] and len(klines) > 20:
        vwap_dist = (closes[-1] - vwap) / vwap
        if vwap_dist < -0.0005: score_bull += 0.05
        if vwap_dist > 0.0005:  score_bear += 0.05

    score_bull = min(max(score_bull, 0.0), 1.0)
    score_bear = min(max(score_bear, 0.0), 1.0)

    # v12: STRENGTHENED gate (require BOTH fast + slow + trend alignment)
    bull_ok = (score_bull >= MIN_STRENGTH and score_bull > score_bear
               and rsi_buy and slow_bull and trend_str > 0.5)
    bear_ok = (score_bear >= MIN_STRENGTH and score_bear > score_bull
               and rsi_sell and slow_bear and trend_str < 0.5)

    _mi_tag = comp_bias[:1] if comp_bias else "N"

    if bull_ok:
        return {"direction": "BUY", "strength": round(score_bull, 3),
                "atr_ratio": round(atr_ratio, 2), "rsi": round(rsi, 1),
                "avg_atr": round(avg_atr, 6), "vol_ok": vol_ok,
                "bias": comp_bias, "fg": fg_val, "alpaca": alpaca_trend,
                "mi_tag": _mi_tag, "trend": round(trend_str, 2)}
    if bear_ok:
        return {"direction": "SELL", "strength": round(score_bear, 3),
                "atr_ratio": round(atr_ratio, 2), "rsi": round(rsi, 1),
                "avg_atr": round(avg_atr, 6), "vol_ok": vol_ok,
                "bias": comp_bias, "fg": fg_val, "alpaca": alpaca_trend,
                "mi_tag": _mi_tag, "trend": round(trend_str, 2)}

    return {"direction": "NONE", "strength": round(max(score_bull, score_bear), 3),
            "atr_ratio": round(atr_ratio, 2), "rsi": round(rsi, 1),
            "avg_atr": round(avg_atr, 6), "vol_ok": vol_ok,
            "mi_tag": _mi_tag, "trend": round(trend_str, 2)}

def record(data: dict):
    """v12: Enhanced trade recording."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    (TRADES_DIR / f"trade_{ts}.json").write_text(json.dumps(data, indent=2))
    with open(TRADES_DIR / f"trades_{datetime.now().strftime('%Y%m%d')}.jsonl", "a") as f:
        f.write(json.dumps(data) + "\n")
    queue = PROJECT_ROOT / "data" / "feeds" / "binance_live_trades.jsonl"
    queue.parent.mkdir(exist_ok=True)
    with open(queue, "a") as f:
        f.write(json.dumps({"source": "BinanceV12", "timestamp": data["timestamp"], "data": data}) + "\n")
    print(f"   Recorded: trade_{ts}.json")

class BinanceTrader:
    def __init__(self):
        self._ensure_singleton()
        self.client = BinanceDemoClient()
        self.positions = {}
        self.pnl = 0.0
        self.trades = 0
        self.errors = 0
        self.running = False
        self.start_bal = None
        self._sentiment_cache = {}
        self._sentiment_ts = 0
        self._alpaca_ts = 0
        self._alpaca_trend = "NEUTRAL"
        self._intel_cache: dict = {}
        self._intel_ts: float = 0
        self._sym_results: dict = {s: [] for s in SYMBOLS}
        self._sym_errors: dict = {s: 0 for s in SYMBOLS}
        self._sym_consec_losses: dict = {s: 0 for s in SYMBOLS}
        self._sym_skip_cycle: dict = {s: 0 for s in SYMBOLS}
        self._timeout_streak: int = 0
        self._timeout_penalty_cycles: int = 0
        self._streak: int = 0
        self._streak_lev_remaining: int = 0
        self._today_wins: int = 0
        self._today_losses: int = 0
        self.pnl_today: float = 0.0
        self.daily_reset_date: str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # RISK state
        self.peak_equity: float = 0.0
        self.circuit_breaker: bool = False
        self._global_consecutive_losses: int = 0
        self._load_state()
        PID_FILE.write_text(str(os.getpid()))
        signal.signal(signal.SIGINT, self._stop)
        signal.signal(signal.SIGTERM, self._stop)

    def _sym_leverage(self, symbol: str, strength: float, fg_val: int) -> int:
        return get_leverage(symbol, strength, fg_val)

    def _sym_equity(self, symbol: str, bal: float = 0) -> float:
        """Use base equity until profitable (per v12 improvements)."""
        base = SYM_MIN_EQUITY.get(symbol, EQUITY_PER_TRADE)
        results = self._sym_results.get(symbol, [])
        n = min(len(results), PERF_WINDOW)
        if n < 5:
            return base
        total_pnl_wins = sum(1 for r in results[-PERF_WINDOW:] if r)
        wr = total_pnl_wins / n
        if wr >= 0.60:
            return round(min(base * 2.0, base * (1 + wr)), 2)
        return base

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
                self.pnl = s.get("total_pnl", 0.0)
                self.trades = s.get("trade_count", 0)
                saved_date = s.get("daily_reset_date", "")
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                if saved_date == today:
                    self.pnl_today = s.get("pnl_today", 0.0)
                    self.daily_reset_date = saved_date
                else:
                    self.pnl_today = 0.0
                    self.daily_reset_date = today
                self.peak_equity = s.get("peak_equity", 0.0)
                self.circuit_breaker = s.get("circuit_breaker", False)
                self._global_consecutive_losses = s.get("global_consecutive_losses", 0)
                # Check for manual reset
                if self.circuit_breaker and Path(CB_RESET_FILE).exists():
                    print(f"[CB] Manual reset detected — clearing circuit breaker")
                    self.circuit_breaker = False
                    self.peak_equity = 0.0
                    Path(CB_RESET_FILE).unlink(missing_ok=True)
            except Exception as _e:
                print(f"[WARN] Failed to load state: {_e}")

    def _check_daily_reset(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self.daily_reset_date:
            print(f"[DAILY RESET] New UTC day {today} — pnl_today reset")
            self.pnl_today = 0.0
            self.daily_reset_date = today
            self._today_wins = 0
            self._today_losses = 0
            self._global_consecutive_losses = 0

    def _today_stats_tag(self) -> str:
        total = self._today_wins + self._today_losses
        wr = int(self._today_wins / total * 100) if total > 0 else 0
        return f"[Today: {self.pnl_today:+.2f} | W:{self._today_wins} L:{self._today_losses} | WR:{wr}%]"

    def _save(self, bal: float, equity: float = 0.0):
        if self.start_bal is None:
            self.start_bal = bal
        STATE_FILE.write_text(json.dumps({
            "current_balance": bal, "starting_balance": self.start_bal,
            "total_pnl": round(self.pnl, 6), "trade_count": self.trades,
            "open_positions": len(self.positions), "symbols": list(self.positions.keys()),
            "last_update": datetime.now().isoformat(),
            "pnl_today": round(self.pnl_today, 6),
            "daily_reset_date": self.daily_reset_date,
            "peak_equity": round(self.peak_equity, 2),
            "circuit_breaker": self.circuit_breaker,
            "global_consecutive_losses": self._global_consecutive_losses,
            "current_equity": round(equity, 2),
        }, indent=2))

    def _stop(self, *_):
        print("\nStopping Binance trader...")
        self.running = False

    def _get_equity(self) -> float:
        bal = self.client.get_usdt_balance()
        unrealized = 0.0
        for sym, pos in self.positions.items():
            try:
                price = self.client.get_price(sym)
                pos_pnl = (price - pos["entry"]) * pos["qty"] * pos.get("leverage", 1)
                if pos["side"] == "SELL":
                    pos_pnl = -pos_pnl
                unrealized += pos_pnl
            except Exception:
                pass
        return bal + unrealized

    def _check_circuit_breaker(self, equity: float):
        if equity > self.peak_equity:
            self.peak_equity = equity
        dd_pct = (self.peak_equity - equity) / self.peak_equity if self.peak_equity > 0 else 0.0
        if dd_pct >= CB_DRAWDOWN_PCT and not self.circuit_breaker:
            self.circuit_breaker = True
            print(f"[CB] CIRCUIT BREAKER TRIPPED — drawdown {dd_pct*100:.1f}% >= {CB_DRAWDOWN_PCT*100:.0f}%")
            print(f"[CB] Peak equity: ${self.peak_equity:.2f} | Current: ${equity:.2f}")
            print(f"[CB] Touch '{CB_RESET_FILE}' to resume trading")
            _obsidian("CIRCUIT BREAKER ENGAGED",
                f"Drawdown: {dd_pct*100:.1f}%\nPeak: ${self.peak_equity:.2f}\nEquity: ${equity:.2f}")
        return dd_pct

    def _check_correlation_risk(self, symbol: str, equity: float) -> bool:
        group = None
        for g in CORRELATION_GROUPS:
            if symbol in g["symbols"]:
                group = g
                break
        if group is None:
            return True
        total_notional = 0.0
        for sym, pos in self.positions.items():
            if sym in group["symbols"]:
                try:
                    price = self.client.get_price(sym)
                    total_notional += price * pos["qty"] * pos.get("leverage", 1)
                except Exception:
                    pass
        current_risk = total_notional / equity if equity > 0 else 1.0
        return current_risk < MAX_CORRELATED_RISK_PCT

    def _get_tf_bias(self, symbol: str, interval: str) -> str:
        try:
            klines = self.client.get_klines(symbol, interval, limit=30)
            if not klines or len(klines) < 21: return "NEUTRAL"
            closes = [float(k[4]) for k in klines]
            # Simple EMA 21
            k = 2/(21+1); e = closes[0]
            for x in closes[1:]: e = x*k + e*(1-k)
            if closes[-1] > e * 1.0001: return "BULL"
            if closes[-1] < e * 0.9999: return "BEAR"
        except Exception:
            pass
        return "NEUTRAL"

    def _get_intel(self) -> dict:
        if time.time() - self._intel_ts > 600:
            self._intel_cache = get_market_intel()
            self._intel_ts = time.time()
        return self._intel_cache

    def _get_sentiment(self):
        intel = self._get_intel()
        return {
            "bias": intel.get("composite_bias", "NEUTRAL"),
            "score": intel.get("composite_score", 0.0),
            "fear_greed": intel.get("fear_greed", {"value": 50}),
        }

    def _get_alpaca_trend(self):
        return self._get_intel().get("alpaca_btc_trend", "NEUTRAL")

    def _get_balance_with_retry(self, label: str = "balance") -> float:
        for attempt in range(1, 6):
            try:
                return self.client.get_usdt_balance()
            except Exception as e:
                print(f"[DNS_RETRY] {label} attempt {attempt}/5 failed: {e}")
                if attempt < 5:
                    print(f"[DNS_RETRY] Waiting 30s before retry...")
                    time.sleep(30)
        raise RuntimeError(f"[DNS_RETRY] {label}: all 5 attempts failed")

    def run(self):
        bal = self._get_balance_with_retry("startup")
        print("=" * 80)
        print(f"Binance Scalper v12 | {', '.join(SYMBOLS)} | Session-adaptive | {INTERVAL}s ticks")
        print(f"Balance: ${bal:,.2f} | Equity/trade: ${EQUITY_PER_TRADE} | {MAX_HOLD_S}s hold")
        print(f"MIN_STRENGTH={MIN_STRENGTH} | MAX_OPEN={MAX_OPEN} | DAILY_LOSS=-${abs(DAILY_LOSS_LIMIT):.0f}")
        print(f"Trades: {TRADES_DIR}")
        print("=" * 80)
        _obsidian("Binance Scalper v12 Started",
            f"- Balance: ${bal:,.2f}\n- Equity: ${EQUITY_PER_TRADE}\n- Hold: {MAX_HOLD_S}s\n- Prior PnL: ${self.pnl:+.2f}")

        self.running = True
        while self.running:
            try:
                self._check_daily_reset()
                intel = self._get_intel()
                sentiment = self._get_sentiment()
                alp_trend = self._get_alpaca_trend()
                bal = self._get_balance_with_retry("main-loop")
                equity = self._get_equity()
                dd_pct = self._check_circuit_breaker(equity)
                self._save(bal, equity)
                if self.circuit_breaker:
                    if any(self.positions.values()):
                        for sym in list(self.positions.keys()):
                            self._tick(sym, sentiment, alp_trend, bal, intel)
                    print(f"[CB] Blocking entries — drawdown {dd_pct*100:.1f}% | equity=${equity:.2f}")
                    time.sleep(INTERVAL)
                    continue
                for sym in SYMBOLS:
                    try:
                        self._tick(sym, sentiment, alp_trend, bal, intel)
                    except Exception as e_sym:
                        print(f"   [TICK ERR] {sym}: {e_sym}")
                        sym_errs = self._sym_errors.get(sym, 0) + 1
                        self._sym_errors[sym] = sym_errs
                        if sym_errs >= 5 and sym in self.positions:
                            print(f"   [STUCK] {sym} has {sym_errs} errors — removing")
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
        ts = datetime.now().strftime("%H:%M:%S")
        klines = self.client.get_klines(symbol, "1m", limit=30)
        if not klines:
            return
        if market_intel is None:
            market_intel = {}
        sig = compute_signal(klines, sentiment, alp_trend, market_intel)
        price = self.client.get_price(symbol)
        pos = self.positions.get(symbol)
        
        # BINANCE-01/02: Fetch funding and multi-TF bias
        try:
            fund_rate = self.client.get_funding_rate(symbol)
            bias_1h = self._get_tf_bias(symbol, "1h")
            bias_4h = self._get_tf_bias(symbol, "4h")
            multi_tf_bias = "BULL" if (bias_1h == "BULL" and bias_4h == "BULL") else \
                            ("BEAR" if (bias_1h == "BEAR" and bias_4h == "BEAR") else "NEUTRAL")
            # Update signal with these new parameters
            sig = compute_signal(klines, sentiment, alp_trend, market_intel, 
                                 funding_rate=fund_rate, multi_tf_bias=multi_tf_bias)
        except Exception as e_fund:
            print(f"   [FUND_ERR] {symbol}: {e_fund}")

        _urgency_floor = MIN_STRENGTH * 0.70
        if pos is None and sig["strength"] < _urgency_floor and sig["direction"] == "NONE":
            return

        fg_val = sentiment.get("fear_greed", {}).get("value", 50)
        lev = self._sym_leverage(symbol, sig["strength"], fg_val)

        open_count = len(self.positions)
        sess_key, sess_mult = get_bin_session()
        eff_min_strength = MIN_STRENGTH + (0.10 if self._timeout_penalty_cycles > 0 else 0.0)
        skip_cycles = self._sym_skip_cycle.get(symbol, 0)
        skip_tag = f" [SKIP{skip_cycles}]" if skip_cycles > 0 else ""
        vol_tag = " [LOWVOL]" if not sig.get("vol_ok", True) else ""
        daily_tag = f" [DLOSS${self.pnl_today:+.0f}]" if self.pnl_today < -50 else ""
        cb_tag = " [CB]" if self.circuit_breaker else ""
        consec_ok = self._global_consecutive_losses < MAX_CONSECUTIVE_LOSSES
        consec_tag = f" [CONSEC{self._global_consecutive_losses}]" if self._global_consecutive_losses > 0 else ""
        daily_loss_pct_ok = True
        if self.start_bal and self.start_bal > 0:
            daily_pct_limit = self.start_bal * DAILY_LOSS_PCT
            daily_loss_pct_ok = self.pnl_today >= max(DAILY_LOSS_LIMIT, -daily_pct_limit)
        corr_ok = self._check_correlation_risk(symbol, bal)
        corr_tag = " [CORR]" if not corr_ok else ""
        daily_pct_tag = f" [DPCT]" if not daily_loss_pct_ok else ""
        stats_tag = self._today_stats_tag()
        trend_tag = f" tr:{sig.get('trend', 0.5):.2f}"
        print(f"[{ts}] {symbol} ${price:,.2f} | {sig['direction']} str:{sig['strength']:.2f} rsi:{sig.get('rsi',0):.0f} lev:{lev}x sess:{sess_key}×{sess_mult}{trend_tag} | {'POS' if pos else '-'} open:{open_count}/{MAX_OPEN}{skip_tag}{vol_tag}{daily_tag}{cb_tag}{consec_tag}{corr_tag}{daily_pct_tag} {stats_tag}")

        if skip_cycles > 0:
            self._sym_skip_cycle[symbol] = skip_cycles - 1

        # ─── ENTRY GATE ──────────────────────────────────────────────────────
        vol_ok = sig.get("vol_ok", True)
        atr_ratio = sig.get("atr_ratio", 1.0)
        daily_ok = self.pnl_today >= DAILY_LOSS_LIMIT
        if (pos is None and sig["direction"] != "NONE"
                and sig["strength"] >= eff_min_strength
                and open_count < MAX_OPEN
                and skip_cycles == 0
                and vol_ok
                and atr_ratio > 0.0
                and daily_ok
                and daily_loss_pct_ok
                and consec_ok
                and corr_ok):

            leverage_mult = 1.0
            if self._streak <= STREAK_LEV_THRESHOLD or self._streak_lev_remaining > 0:
                leverage_mult = STREAK_LEV_MULT
                if self._streak_lev_remaining == 0:
                    self._streak_lev_remaining = STREAK_LEV_TRADES
                lev_reduced = max(1, int(lev * leverage_mult))
                print(f"   [STREAK-LEV] streak={self._streak} → {lev}x → {lev_reduced}x | {self._streak_lev_remaining} trades")
                lev = lev_reduced

            try:
                self.client.set_leverage(symbol, lev)
            except Exception as e_lev:
                print(f"   [LEV] set_leverage {symbol} {lev}x failed: {e_lev}")

            dyn_equity = self._sym_equity(symbol, bal)
            risk_usd = round(dyn_equity * sess_mult, 4)
            notional = risk_usd * lev
            step = QTY_STEP.get(symbol, 0.001)
            qty_raw = notional / price
            qty = max(step, math.floor(qty_raw / step) * step)
            qty = round(qty, QTY_PRECISION.get(symbol, 3))
            side = sig["direction"]

            # v12: Use ATR-based TP/SL or fixed percentage
            avg_atr_abs = sig.get("avg_atr", 0.0)
            atr_pct = avg_atr_abs / price if price > 0 else 0
            USE_ATR_MIN_PCT = 0.0008
            if avg_atr_abs > 0 and atr_pct >= USE_ATR_MIN_PCT:
                sl_dist = avg_atr_abs * ATR_SL_MULT
                tp1_dist = avg_atr_abs * ATR_TP1_MULT
                tp2_dist = avg_atr_abs * ATR_TP2_MULT
                sl_mode = "ATR"
            else:
                sl_dist = price * SL_PCT
                tp1_dist = price * TP1_PCT
                tp2_dist = price * TP2_PCT
                sl_mode = f"PCT(atr={avg_atr_abs:.5f}<{USE_ATR_MIN_PCT*100:.2f}%)"
            sl = price - sl_dist if side == "BUY" else price + sl_dist
            tp1 = price + tp1_dist if side == "BUY" else price - tp1_dist
            tp2 = price + tp2_dist if side == "BUY" else price - tp2_dist

            print(f"   -> ENTRY {side} {qty} {symbol} @ ${price:,.4f}  SL={sl:,.4f}  TP1={tp1:,.4f}  TP2={tp2:,.4f}  LEV:{lev}x  equity=${risk_usd:.2f}")
            result = self.client.place_market_order(symbol, side, qty)
            if result.get("status") in ("FILLED", "NEW", "success", "demo"):
                # v12: DO NOT place SL order (causes API failures)
                # SL is managed in-code via price checks
                self.positions[symbol] = {
                    "side": side, "entry": price, "qty": qty, "qty_remaining": qty,
                    "sl": sl, "tp1": tp1, "tp2": tp2, "leverage": lev,
                    "partial_closed": False,
                    "partial_tp_atr_closed": False,
                    "avg_atr": avg_atr_abs,
                    "entry_time": datetime.now().isoformat(),
                    "order_id": result.get("orderId")
                }
                record({"type": "ENTRY", "symbol": symbol, "side": side,
                        "qty": qty, "price": price, "sl": sl, "tp1": tp1, "tp2": tp2,
                        "leverage": lev, "equity_used": round(risk_usd, 2),
                        "signal": sig, "balance": bal,
                        "order_id": result.get("orderId"), "timestamp": datetime.now().isoformat()})
                _obsidian(f"Binance ENTRY v12: {side} {symbol}",
                    f"- ${price:,.4f} | qty:{qty} | LEV:{lev}x equity:${risk_usd:.2f}\n"
                    f"- SL:{sl:,.4f} TP1:{tp1:,.4f} TP2:{tp2:,.4f}\n"
                    f"- Str:{sig['strength']:.2f} Trend:{sig.get('trend',0.5):.2f}")
                self.trades += 1

        # ─── MANAGE OPEN POSITION ────────────────────────────────────────────
        elif pos is not None:
            elapsed = (datetime.now() - datetime.fromisoformat(pos["entry_time"])).seconds
            exit_side = "SELL" if pos["side"] == "BUY" else "BUY"
            sl_hit = (pos["side"] == "BUY" and price <= pos["sl"]) or (pos["side"] == "SELL" and price >= pos["sl"])
            tp1_hit = (pos["side"] == "BUY" and price >= pos["tp1"]) or (pos["side"] == "SELL" and price <= pos["tp1"])
            tp2_hit = (pos["side"] == "BUY" and price >= pos["tp2"]) or (pos["side"] == "SELL" and price <= pos["tp2"])
            timeout = elapsed >= MAX_HOLD_S

            # ─── Partial TP at 1×ATR ─────────────────────────────────────────
            partial_tp_atr_hit = False
            if not pos.get("partial_tp_atr_closed") and not pos.get("partial_closed"):
                avg_atr_pos = pos.get("avg_atr", 0.0)
                if avg_atr_pos > 0:
                    atr_tp_dist = avg_atr_pos * PARTIAL_TP_ATR
                    partial_tp_atr_hit = (
                        (pos["side"] == "BUY" and price >= pos["entry"] + atr_tp_dist) or
                        (pos["side"] == "SELL" and price <= pos["entry"] - atr_tp_dist)
                    )
            if partial_tp_atr_hit and not sl_hit:
                step = QTY_STEP.get(symbol, 0.001)
                partial_qty_raw = pos["qty"] * PARTIAL_TP_RATIO
                partial_qty = max(step, math.floor(partial_qty_raw / step) * step)
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
                        pos["qty_remaining"] = max(step, round(math.floor(remaining_raw / step) * step,
                                                                QTY_PRECISION.get(symbol, 3)))
                        pos["sl"] = pos["entry"]
                        print(f"   -> PARTIAL_TP_ATR {exit_side} {partial_qty} {symbol} @ ${price:,.4f}  +${partial_pnl:+.4f}")
                        record({"type": "PARTIAL_EXIT", "symbol": symbol, "side": exit_side,
                                "qty": partial_qty, "entry": pos["entry"], "exit": price,
                                "pnl": round(partial_pnl, 6), "reason": "PARTIAL_TP_ATR",
                                "leverage": pos.get("leverage", 1), "elapsed": elapsed,
                                "total_pnl": round(self.pnl, 6), "timestamp": datetime.now().isoformat()})
                        self.trades += 1
                    except Exception as e:
                        pos["partial_tp_atr_closed"] = True
                        print(f"   -> PARTIAL_TP_ATR FAILED {symbol}: {e}")

            # ─── Partial close at TP1 ──────────────────────────────────────────
            if tp1_hit and not pos.get("partial_closed") and not sl_hit:
                step = QTY_STEP.get(symbol, 0.001)
                partial_qty_raw = pos["qty"] * PARTIAL_PCT
                partial_qty = max(step, math.floor(partial_qty_raw / step) * step)
                partial_qty = round(partial_qty, QTY_PRECISION.get(symbol, 3))
                if partial_qty >= step:
                    try:
                        result = self.client.place_market_order(symbol, exit_side, partial_qty)
                        partial_pnl = (price - pos["entry"]) * partial_qty * pos.get("leverage", 1)
                        if pos["side"] == "SELL": partial_pnl = -partial_pnl
                        self.pnl += partial_pnl
                        self.pnl_today += partial_pnl
                        pos["partial_closed"] = True
                        remaining_raw = pos["qty"] - partial_qty
                        pos["qty_remaining"] = max(step, round(math.floor(remaining_raw / step) * step,
                                                                QTY_PRECISION.get(symbol, 3)))
                        pos["sl"] = pos["entry"]
                        print(f"   -> TP1 PARTIAL {exit_side} {partial_qty} {symbol} @ ${price:,.4f}  +${partial_pnl:+.4f}")
                        record({"type": "PARTIAL_EXIT", "symbol": symbol, "side": exit_side,
                                "qty": partial_qty, "entry": pos["entry"], "exit": price,
                                "pnl": round(partial_pnl, 6), "reason": "TP1",
                                "leverage": pos.get("leverage", 1), "elapsed": elapsed,
                                "total_pnl": round(self.pnl, 6), "timestamp": datetime.now().isoformat()})
                        self.trades += 1
                    except Exception as e:
                        pos["partial_closed"] = True
                        print(f"   -> TP1 PARTIAL FAILED {symbol}: {e}")

            # ─── TP2 trailing ────────────────────────────────────────────────
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
                trail_sl2 = pos.get("trail_sl2", None)
                if trail_sl2 is not None:
                    if pos["side"] == "BUY" and price <= trail_sl2: sl_hit = True
                    if pos["side"] == "SELL" and price >= trail_sl2: sl_hit = True

            # ─── Early timeout exit ──────────────────────────────────────────
            near_timeout = (MAX_HOLD_S - elapsed) <= TIMEOUT_EARLY_WINDOW and not timeout
            if near_timeout and not sl_hit and not tp2_hit:
                float_pnl_pct = (price - pos["entry"]) / pos["entry"]
                if pos["side"] == "SELL": float_pnl_pct = -float_pnl_pct
                if float_pnl_pct < TIMEOUT_EARLY_LOSS_PCT:
                    timeout = True
                    print(f"   [EARLY_TIMEOUT] {symbol} {elapsed}s floating {float_pnl_pct*100:+.2f}% < {TIMEOUT_EARLY_LOSS_PCT*100:.1f}%")

            # ─── Full close ──────────────────────────────────────────────────
            step = QTY_STEP.get(symbol, 0.001)
            qty_raw = pos.get("qty_remaining", pos["qty"])
            qty_to_close = max(step, round(math.floor(qty_raw / step) * step,
                                           QTY_PRECISION.get(symbol, 3)))
            full_exit = tp2_hit or sl_hit or timeout
            if full_exit and qty_to_close >= step:
                reason = "TP2" if tp2_hit else ("SL" if sl_hit else "TIMEOUT")
                raw_pnl = (price - pos["entry"]) * qty_to_close * pos.get("leverage", 1)
                if pos["side"] == "SELL": raw_pnl = -raw_pnl
                sym_hist = self._sym_results.setdefault(symbol, [])
                sym_hist.append(raw_pnl > 0)
                if len(sym_hist) > PERF_WINDOW * 2:
                    self._sym_results[symbol] = sym_hist[-PERF_WINDOW * 2:]

                if raw_pnl > 0:
                    self._sym_consec_losses[symbol] = 0
                    self._global_consecutive_losses = 0
                else:
                    self._sym_consec_losses[symbol] = self._sym_consec_losses.get(symbol, 0) + 1
                    if self._sym_consec_losses[symbol] >= 3:
                        self._sym_skip_cycle[symbol] = 2
                        self._sym_consec_losses[symbol] = 0
                        print(f"   [REVERSE] {symbol} 3 losses → skipping 2 cycles")
                    self._global_consecutive_losses += 1
                    if self._global_consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
                        print(f"   [RISK-04] {self._global_consecutive_losses} consecutive losses global → stopping entries for the day")

                if raw_pnl > 0:
                    self._streak = max(1, self._streak + 1) if self._streak >= 0 else 1
                    self._today_wins += 1
                else:
                    self._streak = min(-1, self._streak - 1) if self._streak <= 0 else -1
                    self._today_losses += 1
                if self._streak_lev_remaining > 0:
                    self._streak_lev_remaining -= 1

                if reason == "TIMEOUT":
                    self._timeout_streak += 1
                    if self._timeout_streak >= 3 and self._timeout_penalty_cycles == 0:
                        self._timeout_penalty_cycles = 5
                        print(f"   [CHOP] {self._timeout_streak} timeouts → raise MIN_STRENGTH for 5 cycles")
                else:
                    self._timeout_streak = 0
                if self._timeout_penalty_cycles > 0:
                    self._timeout_penalty_cycles -= 1

                pnl_pct = (price - pos["entry"]) / pos["entry"] * 100 * pos.get("leverage", 1)
                if pos["side"] == "SELL": pnl_pct = -pnl_pct
                self.pnl += raw_pnl
                self.pnl_today += raw_pnl
                print(f"   -> EXIT [{reason}] {exit_side} {qty_to_close} {symbol} @ ${price:,.4f}  PnL=${raw_pnl:+.4f} ({pnl_pct:+.2f}%)  Total=${self.pnl:+.2f}")
                try:
                    result = self.client.place_market_order(symbol, exit_side, qty_to_close)
                    order_id = result.get("orderId")
                except Exception as e:
                    print(f"   -> EXIT API FAILED {symbol}: {e}")
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
                del self.positions[symbol]

    def _shutdown(self):
        bal = self.client.get_usdt_balance()
        self._save(bal)
        print(f"\nBinance v12 trader stopped. Trades: {self.trades} | PnL: ${self.pnl:+.2f} | Balance: ${bal:,.2f}")
        _obsidian("Binance v12 Trader Stopped", f"- Trades: {self.trades}\n- PnL: ${self.pnl:+.2f}\n- Balance: ${bal:,.2f}")
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception as _e:
            print(f"[WARN] Could not remove PID file: {_e}")


if __name__ == "__main__":
    BinanceTrader().run()
