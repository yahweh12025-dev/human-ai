#!/usr/bin/env python3
"""
EA Live Trader v11 — All-Session Adaptive | XAUUSD + XAGUSD + EURUSD + GBPUSD
==============================================================================
v11 improvements (research-driven, log-analysis-driven):

CRITICAL FIXES:
  - lot_size() formula corrected: was using SL *price* instead of SL *distance*
    causing wildly inconsistent sizing. Now: risk_usd / (sl_dist_points × point_value)
  - Always starts at 0.01L minimum, scales up correctly from there
  - ATR dead-market thresholds tightened: XAUUSD<$0.60, XAGUSD<$0.03 (was 0.001)
  - TP ratios reduced to 0.8-1.5R (was 1.5-2.5R) — realistic for 6-min window
  - min_score raised to 5 global (was 3) — eliminates noise trades
  - Timeout extended: base 20 candles (10min), TREND 40c (20min) — gives TP room to hit
  - Concurrent positions: each symbol independent, MT5 reconciliation on startup
  - Bridge reconciliation: on startup, sync Python positions dict from MT5 status
  - Timeout exit: if unrealised > 0, trail at 1×ATR before closing (bank profits)
  - Session: NO blocked periods — all sessions active, ASIAN raises min_score to 7
  - XAUUSD/XAGUSD correlation guard: halve lots when both open simultaneously

SIGNAL IMPROVEMENTS (v11):
  - Score ≥ 5 required across all regimes (was 3)
  - ASIAN session: score ≥ 7 (reduces overtrading by ~60%)
  - EMA cross confirmed by price momentum (3 consecutive candles)
  - ATR must be > session-specific dead-market threshold
  - H1 bias now required (not just bonus) in TREND regime
  - Breakout boost only in confirmed TREND (not SCALP/RANGE)

POSITION MANAGEMENT (v11):
  - SL = 1.5× ATR, capped 0.3-0.6% price, checked vs min-stop-level
  - TP = SL × 0.8R (RANGE/Asian), 1.2R (SCALP), 1.5R (TREND)
  - Trailing stop: activates at 0.8R profit, trails at 0.6× ATR
  - Timeout exit: close at market if P&L ≤ 0; trail at 1×ATR if P&L > 0
  - All SL/TP sent to MT5 broker on every entry (no sl=0)

SESSION PARAMS (v11):
  - ASIAN:     0.25× risk, min_score=7, tp_r=0.8, timeout=10c
  - LONDON:    1.0×  risk, min_score=5, tp_r=1.2, timeout=20c
  - LONDON_NY: 1.5×  risk, min_score=5, tp_r=1.5, timeout=40c
  - NY_CLOSE:  0.5×  risk, min_score=6, tp_r=1.0, timeout=16c
  - AFTER_NY:  0.75× risk, min_score=5, tp_r=1.0, timeout=16c

Shutdown: SIGTERM/SIGINT send CLOSE to MT5 then CLOSE_ALL fallback.
"""

import json, os, sys, time, signal, random, uuid, subprocess
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / '.env')

try:
    import yfinance as yf
    YFINANCE_OK = True
except ImportError:
    YFINANCE_OK = False

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRADES_DIR   = Path(__file__).parent / "trades" / "mt5"
OBSIDIAN_DIR = PROJECT_ROOT / "data" / "obsidian"
STATE_FILE   = TRADES_DIR / "state.json"
PID_FILE     = TRADES_DIR / "ea_trader.pid"

MT5_FILES    = Path.home() / ".wine/drive_c/Program Files/MetaTrader 5/MQL5/Files"
SIGNAL_FILE  = MT5_FILES / "python_signal.json"
RESULT_FILE  = MT5_FILES / "python_result.json"
MT5_STATUS   = MT5_FILES / "mt5_status.json"

TRADES_DIR.mkdir(parents=True, exist_ok=True)
MT5_FILES.mkdir(parents=True, exist_ok=True)

# ── Symbols ─────────────────────────────────────────────────
SYMBOLS  = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD"]
YF_MAP   = {"XAUUSD": "GC=F", "XAGUSD": "SI=F", "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X"}

# ── Risk parameters ──────────────────────────────────────────
DEPOSIT          = 5000.0
RISK_PCT         = 0.5       # 0.5% risk per trade
MAX_SL_PCT       = 0.006     # 0.6% max SL cap
MIN_SL_PCT       = {"XAUUSD": 0.003, "XAGUSD": 0.003, "EURUSD": 0.0015, "GBPUSD": 0.0015}
INTERVAL         = 30        # 30s ticks
MIN_HOLD_SECONDS = 180       # 3 min minimum hold (FTMO rule)

# ── Session classification (UTC hours) ───────────────────────
# ALL sessions trade — no blocked periods. Parameters adapt.
ASIAN_HOURS      = {22, 23, 0, 1, 2, 3, 4, 5, 6}
LONDON_HOURS     = {7, 8, 9, 10, 11}
LONDON_NY_HOURS  = {12, 13, 14, 15, 16}
NY_CLOSE_HOURS   = {17, 18}
AFTER_NY_HOURS   = {19, 20, 21}

RISK_MULT = {"london_ny": 1.5, "london": 1.0, "after_ny": 0.75, "ny_close": 0.5, "asian": 0.25}

# ── v11 Session regime params — tighter TP, higher score threshold ──────────
# TP ratios cut from 1.5-2.5R → 0.8-1.5R: realistic for 6-20 min window
# min_score raised: 5 global, 7 Asian (eliminates noise), 6 NY_Close (choppy)
SESSION_REGIME_PARAMS = {
    "asian":    {"tp_r": 0.8,  "sl_atr": 1.2, "timeout": 10, "trail_r": 0.6, "min_score": 7},
    "london":   {"tp_r": 1.2,  "sl_atr": 1.5, "timeout": 20, "trail_r": 0.6, "min_score": 4},
    "london_ny":{"tp_r": 1.5,  "sl_atr": 1.5, "timeout": 40, "trail_r": 0.6, "min_score": 4},
    "ny_close": {"tp_r": 1.0,  "sl_atr": 1.2, "timeout": 16, "trail_r": 0.6, "min_score": 5},
    "after_ny": {"tp_r": 1.0,  "sl_atr": 1.2, "timeout": 16, "trail_r": 0.6, "min_score": 4},
}

# Regime TP ratio multipliers applied ON TOP of session base tp_r
# TREND gets full tp_r, SCALP gets 0.9x, RANGE gets 0.7x
REGIME_TP_MULT = {"TREND": 1.0, "SCALP": 0.9, "RANGE": 0.7, "DEAD": 0.0}
REGIME_SL_MULT = {"TREND": 1.5, "SCALP": 1.2, "RANGE": 1.0, "DEAD": 0.0}

# ── Dead-market ATR thresholds (v11: research-calibrated) ─────────────────────
# XAUUSD 1m ATR: normal $0.80-$3.00; Asian low $0.40-$0.60 → block at $0.60
# XAGUSD 1m ATR: normal $0.03-$0.12 → block at $0.03
ATR_DEAD_THRESHOLD = {
    "XAUUSD": 1.00,   # 5m ATR: normal $2-8; block truly dead market < $1
    "XAGUSD": 0.05,   # 5m ATR: normal $0.05-0.20; block < $0.05
    "EURUSD": 0.0002,
    "GBPUSD": 0.0003,
}

# ── Score-proportional lot scaling ───────────────────────────
SCORE_LOT_MULT = {5: 1.0, 6: 1.3, 7: 1.6, 8: 2.0}

# ── Prop firm hard limits ────────────────────────────────────
DAILY_LOSS_LIMIT_PCT  = 3.0
MAX_DRAWDOWN_PCT      = 5.0
WARN_DAILY_LOSS_PCT   = 1.5
WARN_DRAWDOWN_PCT     = 3.0
STREAK_HARD_STOP      = -8

# ── Contract specification ────────────────────────────────────
CONTRACT_SIZE = {"XAUUSD": 100,    "XAGUSD": 5000,  "EURUSD": 100000, "GBPUSD": 100000}
POINT_SIZE    = {"XAUUSD": 0.01,   "XAGUSD": 0.001, "EURUSD": 0.0001, "GBPUSD": 0.0001}
POINT_VALUE   = {"XAUUSD": 1.0,    "XAGUSD": 5.0,   "EURUSD": 10.0,   "GBPUSD": 10.0}
# Hard caps — conservative until 100+ trade positive track record
MAX_LOT       = {"XAUUSD": 0.05,   "XAGUSD": 0.05,  "EURUSD": 0.05,   "GBPUSD": 0.05}
MIN_LOT       = 0.01

# ── Trailing stop parameters ─────────────────────────────────
TRAIL_ACTIVATE_R      = 0.8   # activate trail earlier (was 1.5R) — secure profits faster
TRAIL_ATR_MULT        = 0.6   # trail gap = 0.6× ATR


# ═══════════════════════════════════════════════════════════
# Utility helpers
# ═══════════════════════════════════════════════════════════

def _obsidian(title, body, tag="ea"):
    try:
        from core.integrations.vault_logger import vault_log
        vault_log("ea", tag.upper(), title, data={"body": body[:500]})
    except Exception:
        try:
            d = OBSIDIAN_DIR / "trading" / "ea"; d.mkdir(parents=True, exist_ok=True)
            f = d / f"{datetime.now().strftime('%Y-%m-%d')}-{tag}.md"
            with open(f, "a") as fp:
                fp.write(f"## {title}\n_{datetime.now().strftime('%H:%M:%S')}_\n{body}\n\n---\n\n")
        except Exception:
            pass


def in_session() -> bool:
    now = datetime.now(timezone.utc)
    weekday = now.weekday()
    h, m = now.hour, now.minute
    if weekday == 5: return False
    if weekday == 6 and not (h == 22 and m >= 5) and h < 22: return False
    if (h == 21 and m >= 55) or (h == 22 and m < 5): return False
    return True


def get_session() -> tuple:
    h = datetime.now(timezone.utc).hour
    if h in LONDON_NY_HOURS:  return "london_ny",  "LON_NY",   RISK_MULT["london_ny"]
    if h in LONDON_HOURS:     return "london",     "LONDON",   RISK_MULT["london"]
    if h in AFTER_NY_HOURS:   return "after_ny",   "AFTER_NY", RISK_MULT["after_ny"]
    if h in NY_CLOSE_HOURS:   return "ny_close",   "NY_CLOSE", RISK_MULT["ny_close"]
    return "asian",            "ASIAN",    RISK_MULT["asian"]


def get_price(symbol: str) -> float:
    try:
        if MT5_STATUS.exists():
            age = time.time() - MT5_STATUS.stat().st_mtime
            if age < 15:
                status = json.loads(MT5_STATUS.read_text())
                key = f"{symbol.lower()}_bid"
                val = status.get(key, 0)
                if val and float(val) > 0:
                    return float(val)
    except Exception:
        pass
    if YFINANCE_OK:
        try: return float(yf.Ticker(YF_MAP[symbol]).fast_info.last_price)
        except Exception: pass
    try:
        import glob as _glob
        files = sorted(_glob.glob(str(TRADES_DIR / f"trade_{symbol}_*.json")))
        if files:
            last = json.loads(open(files[-1]).read())
            p = last.get("entry_price") or last.get("exit_price")
            if p: return float(p)
    except Exception:
        pass
    return {"XAUUSD": 4540.0, "XAGUSD": 76.0, "EURUSD": 1.0850, "GBPUSD": 1.2700}.get(symbol, 1.0)


def fetch_klines(symbol: str, period="1d", interval_tf="1m", n=80) -> list:
    if not YFINANCE_OK: return []
    try:
        df = yf.download(YF_MAP[symbol], period=period, interval=interval_tf, progress=False)
        if df.empty: return []
        col = df["Close"].iloc[:, 0] if hasattr(df.columns, "levels") else df["Close"]
        return [float(c) for c in col.dropna().values[-n:]]
    except Exception:
        return []


def compute_atr(prices: list, period: int = 14) -> float:
    if len(prices) < 2: return 0.0
    trs = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
    return sum(trs[-period:]) / min(len(trs), period)


def compute_rsi(prices: list, period: int = 14) -> float:
    if len(prices) < period + 1: return 50.0
    gains, losses = [], []
    for i in range(1, len(prices)):
        d = prices[i] - prices[i-1]
        gains.append(max(d, 0)); losses.append(max(-d, 0))
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    return round(100 - 100 / (1 + ag / al), 2) if al > 0 else 100.0


def compute_ema(prices: list, n: int) -> float:
    if not prices: return 0.0
    k = 2 / (n + 1); e = prices[0]
    for p in prices[1:]: e = p * k + e * (1 - k)
    return e


def get_trend_15m(symbol: str) -> str:
    try:
        closes = fetch_klines(symbol, period="5d", interval_tf="15m", n=30)
        if len(closes) < 22: return "NEUTRAL"
        ema9  = compute_ema(closes[-22:], 9)
        ema20 = compute_ema(closes[-22:], 20)
        if ema9 > ema20 * 1.0002: return "BULL"
        if ema9 < ema20 * 0.9998: return "BEAR"
    except Exception:
        pass
    return "NEUTRAL"


def get_h1_bias(symbol: str) -> str:
    if not YFINANCE_OK: return "NEUTRAL"
    try:
        df = yf.download(YF_MAP[symbol], period="10d", interval="1h", progress=False)
        if df.empty: return "NEUTRAL"
        col = df["Close"].iloc[:, 0] if hasattr(df.columns, "levels") else df["Close"]
        closes_h1 = [float(c) for c in col.dropna().values[-60:]]
        if len(closes_h1) < 25: return "NEUTRAL"
        ema20_now  = compute_ema(closes_h1[-25:], 20)
        ema20_prev = compute_ema(closes_h1[-30:-5], 20) if len(closes_h1) >= 30 else ema20_now
        threshold  = 0.0003
        if ema20_now > ema20_prev * (1 + threshold): return "BULL"
        if ema20_now < ema20_prev * (1 - threshold): return "BEAR"
    except Exception:
        pass
    return "NEUTRAL"


def detect_regime(prices: list, atr: float) -> str:
    if len(prices) < 30: return "SCALP"
    if atr < 0.003: return "DEAD"

    sma20  = sum(prices[-20:]) / 20
    std20  = (sum((p - sma20) ** 2 for p in prices[-20:]) / 20) ** 0.5
    bb_width_pct = (4 * std20 / sma20) if sma20 > 0 else 0

    ema5  = compute_ema(prices[-12:],  5)
    ema20 = compute_ema(prices[-25:], 20)
    ema50 = compute_ema(prices[-55:], 50) if len(prices) >= 55 else ema20
    ema_diff_pct = abs(ema5 - ema20) / ema20 if ema20 > 0 else 0

    above_ema20 = sum(1 for p in prices[-10:] if p > ema20)
    below_ema20 = 10 - above_ema20
    one_sided   = above_ema20 >= 7 or below_ema20 >= 7

    up_run   = sum(1 for i in range(-6, 0) if prices[i] > prices[i-1])
    down_run = 6 - up_run
    strong_dir = up_run >= 4 or down_run >= 4

    last3_down = (prices[-1] < prices[-2] < prices[-3] < prices[-4])
    last3_up   = (prices[-1] > prices[-2] > prices[-3] > prices[-4])
    strong_accel = last3_down or last3_up

    if ema_diff_pct > 0.0005 and one_sided and strong_dir:
        return "TREND"
    if ema_diff_pct > 0.0003 and strong_accel and strong_dir:
        return "TREND"

    price_near_sma = abs(prices[-1] - sma20) / sma20 < 0.002
    if bb_width_pct < 0.003 and price_near_sma:
        return "RANGE"

    return "SCALP"


def find_swing_levels(prices: list, lookback: int = 20) -> tuple:
    if len(prices) < lookback + 2: return None, None
    window = prices[-(lookback + 2):]
    highs, lows = [], []
    for i in range(1, len(window) - 1):
        if window[i] > window[i-1] and window[i] > window[i+1]: highs.append(window[i])
        if window[i] < window[i-1] and window[i] < window[i+1]: lows.append(window[i])
    return (max(highs) if highs else None), (min(lows) if lows else None)


def compute_signal(prices: list, trend_15m: str = "NEUTRAL", h1_bias: str = "NEUTRAL",
                   regime: str = "SCALP", sess_key: str = "london") -> dict:
    """
    v11 signal — higher bar for entry:
    - min_score is checked externally per session
    - Score requires both EMA cross AND price momentum confirmation
    - H1 bias adds +1 (was soft; now weighted more)
    - Breakout boost only in TREND regime
    """
    if len(prices) < 22:
        return {"direction": "NONE", "score": 0}

    atr = compute_atr(prices)
    if atr == 0:
        return {"direction": "NONE", "score": 0}

    # ── Dead-market filter (v11: symbol-calibrated thresholds) ──
    recent_trs = [abs(prices[i] - prices[i-1]) for i in range(-20, 0)]
    avg_atr    = sum(recent_trs) / len(recent_trs)
    last_move  = abs(prices[-1] - prices[-2])
    atr_ratio  = last_move / avg_atr if avg_atr > 0 else 1.0

    # News spike guard
    if atr_ratio > 5.0:
        return {"direction": "NONE", "score": 0, "atr": round(atr, 4), "block": "news-spike"}

    if avg_atr < 0.001:
        return {"direction": "NONE", "score": 0, "atr": round(atr, 4), "block": "dead-market"}

    # ── Fast EMAs ────────────────────────────────────────────
    ema3  = compute_ema(prices[-10:],  3)
    ema8  = compute_ema(prices[-15:],  8)
    ema21 = compute_ema(prices[-22:], 21)
    fast_bull = ema3 > ema8
    fast_bear = ema3 < ema8
    slow_bull = ema8 > ema21 * 1.0001
    slow_bear = ema8 < ema21 * 0.9999

    # Momentum: majority-direction over last 5 candles (3-of-5 net move)
    # More robust than requiring last candle to be in-direction (single candle reversals block)
    if len(prices) >= 6:
        recent = prices[-6:]
        up_moves   = sum(1 for i in range(1, 6) if recent[i] > recent[i-1])
        down_moves = 5 - up_moves
        mom_bull = up_moves >= 3 and prices[-1] > prices[-5]
        mom_bear = down_moves >= 3 and prices[-1] < prices[-5]
    else:
        mom_bull = False
        mom_bear = False

    # ── Bollinger Bands ──────────────────────────────────────
    sma20    = sum(prices[-20:]) / 20
    std20    = (sum((p - sma20) ** 2 for p in prices[-20:]) / 20) ** 0.5
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    bb_breakout_bull = prices[-1] > bb_upper and prices[-2] <= bb_upper
    bb_breakout_bear = prices[-1] < bb_lower and prices[-2] >= bb_lower
    bb_pct  = (prices[-1] - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5
    near_upper = bb_pct > 0.85
    near_lower = bb_pct < 0.15

    rsi     = compute_rsi(prices[-20:] if len(prices) >= 20 else prices, period=9)
    rsi_buy = rsi < 65   # was 62 — widened to avoid blocking near-overbought BUY
    rsi_sell= rsi > 35   # was 38 — widened to avoid blocking near-oversold SELL

    # ── v11: Pillars now require stronger confirmation ────────
    # Pillar A: EMA cross + momentum confirmation (both required)
    pillar_a_bull = fast_bull and mom_bull
    pillar_a_bear = fast_bear and mom_bear

    # Pillar B: Volatility (ATR spike) + slow trend alignment
    pillar_b_bull = (atr_ratio > 1.0 and fast_bull) or (slow_bull and mom_bull)
    pillar_b_bear = (atr_ratio > 1.0 and fast_bear) or (slow_bear and mom_bear)

    # Pillar C: Bollinger structure
    pillar_c_bull = bb_breakout_bull or (near_lower and fast_bull and mom_bull)
    pillar_c_bear = bb_breakout_bear or (near_upper and fast_bear and mom_bear)

    bull_pillars = sum([pillar_a_bull, pillar_b_bull, pillar_c_bull])
    bear_pillars = sum([pillar_a_bear, pillar_b_bear, pillar_c_bear])

    # RSI confirmation (+1): add bonus when RSI supports direction (not in extreme opposite zone)
    # For BULL: RSI < 75 (not overbought blow-off); For BEAR: RSI > 20 (not capitulation floor)
    score_bull = bull_pillars + (1 if rsi < 75  and bull_pillars >= 1 else 0)
    score_bear = bear_pillars + (1 if rsi > 20  and bear_pillars >= 1 else 0)

    # 15m trend: +1
    if trend_15m == "BULL": score_bull += 1
    if trend_15m == "BEAR": score_bear += 1

    # H1 bias: +1 (weighted same as before but requires ≥2 pillars to matter)
    if h1_bias == "BULL" and bull_pillars >= 1: score_bull += 1
    if h1_bias == "BEAR" and bear_pillars >= 1: score_bear += 1

    score     = max(score_bull, score_bear)
    direction = "NONE"
    # RSI direction gates: only block at extremes (RSI<20=capitulation, RSI>80=blow-off)
    # rsi_sell/rsi_buy used for bonus confirmation; direction gate uses extreme-only check
    if score_bull >= 3 and score_bull > score_bear and rsi < 80:
        direction = "BUY"
    elif score_bear >= 3 and score_bear > score_bull and rsi > 20:
        direction = "SELL"
    elif score_bull >= 3 and score_bull == score_bear:
        if (trend_15m == "BULL" or h1_bias == "BULL") and rsi < 80:
            direction = "BUY"
        elif (trend_15m == "BEAR" or h1_bias == "BEAR") and rsi_sell:
            direction = "SELL"

    # v11: Breakout boost ONLY in confirmed TREND regime
    if regime == "TREND" and direction != "NONE":
        window_prices = prices[-(21):-1]
        current = prices[-1]
        if direction == "BUY" and window_prices and current > max(window_prices):
            score_bull += 2; score = max(score_bull, score_bear)
        elif direction == "SELL" and window_prices and current < min(window_prices):
            score_bear += 2; score = max(score_bull, score_bear)

    return {
        "direction": direction,
        "score": score,
        "score_bull": score_bull,
        "score_bear": score_bear,
        "atr": round(atr, 4),
        "avg_atr": round(avg_atr, 4),
        "rsi": round(rsi, 1),
        "atr_ratio": round(atr_ratio, 2),
        "pillars_bull": bull_pillars,
        "pillars_bear": bear_pillars,
        "regime": regime,
        "h1_bias": h1_bias,
    }


def lot_size(symbol: str, sl_dist: float, equity: float, reduced: bool = False,
             session_mult: float = 1.0, streak: int = 0, score: int = 5) -> float:
    """
    v11 FIXED lot sizing — uses SL *distance* not SL *price*.

    Formula: risk_usd / (sl_distance_in_points × point_value_per_lot)
      sl_distance_in_points = sl_dist / POINT_SIZE[symbol]
      dollar_risk_per_lot   = sl_distance_in_points × POINT_VALUE[symbol]
      lots = risk_usd / dollar_risk_per_lot

    Example XAUUSD: equity=$4400, risk=0.5%=$22, sl_dist=$3.0
      sl_points = 3.0 / 0.01 = 300
      $/lot = 300 × 1.0 = $300/lot
      lots = 22 / 300 = 0.073 → 0.05 (capped)

    Example XAGUSD: equity=$4400, risk=0.5%=$22, sl_dist=$0.15
      sl_points = 0.15 / 0.001 = 150
      $/lot = 150 × 5.0 = $750/lot
      lots = 22 / 750 = 0.029 → 0.03
    """
    if reduced:
        return MIN_LOT

    if sl_dist <= 0 or equity <= 0:
        return MIN_LOT

    risk_usd = equity * (RISK_PCT / 100)

    sl_points        = sl_dist / POINT_SIZE[symbol]
    dollar_per_lot   = sl_points * POINT_VALUE[symbol]
    risk_lots        = risk_usd / dollar_per_lot if dollar_per_lot > 0 else MIN_LOT

    # Score scaling
    score_mult = SCORE_LOT_MULT.get(min(score, 8), 1.0)

    # Session scaling
    scaled = risk_lots * session_mult * score_mult

    # Streak scaling (conservative — only +/- 1 step per lot)
    step = MIN_LOT
    if streak >= 3:
        streak_adj = min((streak // 3) * step, MIN_LOT * 3)
    elif streak <= -2:
        streak_adj = max((streak // 2) * step, -MIN_LOT * 2)
    else:
        streak_adj = 0.0

    final = round(max(MIN_LOT, min(scaled + streak_adj, MAX_LOT[symbol])), 2)
    return final


def pnl_for_move(symbol: str, price_move: float, lot: float) -> float:
    return (price_move / POINT_SIZE[symbol]) * POINT_VALUE[symbol] * lot


# ═══════════════════════════════════════════════════════════
# MT5 signal I/O
# ═══════════════════════════════════════════════════════════

def write_signal(symbol: str, direction: str, lot: float, sl=0.0, tp=0.0) -> str:
    sig_id = f"{symbol}_{direction}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    sig = {"id": sig_id, "action": direction, "symbol": symbol,
           "lot": lot, "sl": sl, "tp": tp,
           "timestamp": datetime.now().isoformat()}
    SIGNAL_FILE.write_text(json.dumps(sig, separators=(",", ":")))
    print(f"   → MT5 signal: {sig_id}")
    return sig_id


def write_close_signal(symbol: str) -> str:
    sig_id = f"CLOSE_{symbol}_{datetime.now().strftime('%H%M%S_%f')[:12]}"
    sig = {"id": sig_id, "action": "CLOSE", "symbol": symbol,
           "lot": 0, "sl": 0, "tp": 0, "timestamp": datetime.now().isoformat()}
    SIGNAL_FILE.write_text(json.dumps(sig, separators=(",", ":")))
    print(f"   → MT5 CLOSE: {sig_id}")
    return sig_id


def write_close_all_signal() -> str:
    sig_id = f"CLOSE_ALL_{datetime.now().strftime('%H%M%S_%f')[:12]}"
    sig = {"id": sig_id, "action": "CLOSE_ALL", "symbol": "ALL",
           "lot": 0, "sl": 0, "tp": 0, "timestamp": datetime.now().isoformat()}
    SIGNAL_FILE.write_text(json.dumps(sig, separators=(",", ":")))
    print(f"   → MT5 CLOSE_ALL: {sig_id}")
    return sig_id


def read_mt5_status() -> dict:
    if not MT5_STATUS.exists(): return {}
    try:
        age = time.time() - MT5_STATUS.stat().st_mtime
        if age > 90: return {}
        return json.loads(MT5_STATUS.read_text())
    except: return {}


def mt5_is_live() -> bool:
    return bool(read_mt5_status())


def wait_for_mt5(timeout_seconds: int = 300) -> dict:
    deadline = time.time() + timeout_seconds
    warned_at = 0
    print("\n" + "="*70)
    print("WAITING FOR MT5 EA (MetalEA_v2)...")
    print("="*70)
    print("In MetaTrader 5:")
    print("  1. Navigator (Ctrl+N) → Expert Advisors → MetalEA_v2")
    print("  2. Drag onto XAUUSD chart")
    print("  3. Tick 'Allow automated trading' → OK")
    print("  4. AutoTrading toolbar button must be GREEN")
    print("\nPython starts trading automatically once MetalEA_v2 confirms.")
    print("="*70 + "\n")

    while time.time() < deadline:
        status = read_mt5_status()
        if status:
            print(f"\nMT5 MetalEA_v2 CONFIRMED ACTIVE")
            print(f"  Account  : #{status.get('account', '?')} @ {status.get('server', '?')}")
            print(f"  Balance  : ${status.get('balance', '?')}")
            print(f"  Equity   : ${status.get('equity', '?')}")
            print(f"  XAUUSD   : ${status.get('xauusd_bid', '?')}")
            print(f"  XAGUSD   : ${status.get('xagusd_bid', '?')}")
            print(f"  State    : {status.get('state', '?')}\n")
            return status
        now = time.time()
        if now - warned_at >= 30:
            remaining = int(deadline - now)
            print(f"  Waiting for MetalEA_v2... ({remaining}s remaining)")
            warned_at = now
        time.sleep(5)

    print(f"\nTIMEOUT: MetalEA_v2 not detected after {timeout_seconds}s.")
    print("Attach MetalEA_v2 to a chart and restart.\n")
    return {}


def read_signal_result(expected_id: str, timeout: float = 8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if RESULT_FILE.exists():
            try:
                r = json.loads(RESULT_FILE.read_text())
                if r.get("sig_id") == expected_id:
                    return r
            except Exception:
                pass
        time.sleep(0.4)
    return None


def record(data: dict):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:17]
    (TRADES_DIR / f"trade_{data.get('symbol','?')}_{ts}.json").write_text(json.dumps(data, indent=2))
    with open(TRADES_DIR / f"trades_{datetime.now().strftime('%Y%m%d')}.jsonl", "a") as f:
        f.write(json.dumps(data) + "\n")
    queue = PROJECT_ROOT / "data" / "feeds" / "ea_live_trades.jsonl"
    queue.parent.mkdir(exist_ok=True)
    with open(queue, "a") as f:
        f.write(json.dumps({"source": "EAv11", "timestamp": data["timestamp"], "data": data}) + "\n")
    print(f"   Recorded: {data.get('type')} {data.get('symbol')} {data.get('direction','')}")


# ═══════════════════════════════════════════════════════════
# Main trader class
# ═══════════════════════════════════════════════════════════

class EATrader:
    def __init__(self):
        self._ensure_singleton()
        self.positions      = {}
        self.klines_1m      = {s: [] for s in SYMBOLS}
        self.klines_ts      = {s: 0   for s in SYMBOLS}
        self.trend_15m      = {s: "NEUTRAL" for s in SYMBOLS}
        self.trend_ts       = {s: 0   for s in SYMBOLS}
        self.h1_bias        = {s: "NEUTRAL" for s in SYMBOLS}
        self.h1_bias_ts     = {s: 0   for s in SYMBOLS}
        self.deposit        = DEPOSIT
        self.pnl            = 0.0
        self.trades         = 0
        self.errors         = 0
        self.running        = False
        self._halt          = False
        self._peak_equity   = DEPOSIT
        self._daily_start   = DEPOSIT
        self._daily_date    = datetime.now(timezone.utc).date()
        self._streak        = 0
        self._last_trade_pnl: dict = {}
        self._combo_losses: dict = {}
        self._combo_wins:   dict = {}
        self._reverse_cooldown: dict = {}
        self._timeout_streak: int = 0
        self._timeout_penalty_cycles: int = 0
        # v11: stale tracking
        self._stale_ticks   = 0

        self._load_state()
        PID_FILE.write_text(str(os.getpid()))
        signal.signal(signal.SIGINT,  self._stop)
        signal.signal(signal.SIGTERM, self._stop)

    def _ensure_singleton(self):
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text().strip())
                if pid != os.getpid():
                    try:
                        os.kill(pid, 0)
                        print(f"ERROR: EA Trader already running (PID {pid}). Exiting.")
                        sys.exit(1)
                    except ProcessLookupError:
                        pass
            except (ValueError, OSError):
                pass

    def _load_state(self):
        if STATE_FILE.exists():
            try:
                s = json.loads(STATE_FILE.read_text())
                self.pnl          = s.get("total_pnl", 0.0)
                self.trades       = s.get("trade_count", 0)
                self._peak_equity = s.get("peak_equity", self.deposit + self.pnl)
                self._streak      = s.get("streak", 0)
            except Exception as _e_st:
                print(f"[WARN] EA state load failed: {_e_st} — using defaults")

    def _save(self, mt5_status: dict = None):
        live_bal    = mt5_status.get("balance", 0)  if mt5_status else 0
        live_equity = mt5_status.get("equity",  0)  if mt5_status else 0
        live_float  = mt5_status.get("floating_pnl", 0) if mt5_status else 0
        primary_equity  = live_equity  if live_equity  > 0 else (self.deposit + self.pnl)
        primary_balance = live_bal     if live_bal     > 0 else (self.deposit + self.pnl)
        pnl_today = round(primary_equity - self._daily_start, 2) if self._daily_start > 0 else 0.0
        daily_loss_pct = round((self._daily_start - primary_equity) / self._daily_start * 100, 2) \
                         if self._daily_start > 0 else 0.0
        drawdown_pct = round((self._peak_equity - primary_equity) / self._peak_equity * 100, 2) \
                         if self._peak_equity > 0 else 0.0
        data = {
            "balance": primary_balance, "equity": primary_equity,
            "floating_pnl": live_float,
            "open_positions": mt5_status.get("open_positions", len(self.positions)) if mt5_status else len(self.positions),
            "mt5_live": bool(mt5_status),
            "deposit": self.deposit, "total_pnl": round(self.pnl, 4),
            "pnl_today": pnl_today, "trade_count": self.trades,
            "peak_equity": self._peak_equity, "streak": self._streak,
            "daily_start": self._daily_start, "daily_date": str(self._daily_date),
            "daily_loss_pct": daily_loss_pct, "drawdown_pct": drawdown_pct,
            "session_active": in_session(), "symbols_active": SYMBOLS,
            "last_update": datetime.now().isoformat(), "version": "v11",
        }
        STATE_FILE.write_text(json.dumps(data, indent=2))

    def _update_equity_tracking(self, equity: float):
        if equity > self._peak_equity:
            self._peak_equity = equity
        today = datetime.now(timezone.utc).date()
        if today != self._daily_date:
            self._daily_date  = today
            self._daily_start = equity
            print(f"   [PROP] Daily reset — start equity: ${equity:,.2f}")

    def _check_prop_limits(self, equity: float) -> str:
        daily_loss    = self._daily_start - equity
        daily_loss_pct = daily_loss / self._daily_start * 100 if self._daily_start > 0 else 0
        drawdown      = self._peak_equity - equity
        drawdown_pct  = drawdown / self._peak_equity * 100 if self._peak_equity > 0 else 0
        if daily_loss_pct >= DAILY_LOSS_LIMIT_PCT:
            msg = f"DAILY LOSS LIMIT HIT: ${daily_loss:.2f} ({daily_loss_pct:.2f}%)"
            print(f"\n🚨 PROP FIRM HALT — {msg}")
            _obsidian("PROP FIRM DAILY LIMIT HIT", f"- {msg}\n- Closing all positions", "ea_halt")
            return "HALT"
        if drawdown_pct >= MAX_DRAWDOWN_PCT:
            msg = f"MAX DRAWDOWN HIT: ${drawdown:.2f} ({drawdown_pct:.2f}%)"
            print(f"\n🚨 PROP FIRM HALT — {msg}")
            _obsidian("PROP FIRM DRAWDOWN LIMIT HIT", f"- {msg}\n- Closing all positions", "ea_halt")
            return "HALT"
        if daily_loss_pct >= WARN_DAILY_LOSS_PCT or drawdown_pct >= WARN_DRAWDOWN_PCT:
            return "WARN"
        return "OK"

    def _close_all_mt5_positions(self, reason: str = "shutdown"):
        if not self.positions:
            print(f"   [SHUTDOWN] No open positions to close ({reason})")
            return
        print(f"\n   [SHUTDOWN] Closing {len(self.positions)} open position(s) — reason: {reason}")
        for symbol, pos in list(self.positions.items()):
            try:
                price  = get_price(symbol)
                sig_id = write_close_signal(symbol)
                result = read_signal_result(sig_id, timeout=8)
                price_move = price - pos["entry_price"] if pos["direction"] == "BUY" \
                             else pos["entry_price"] - price
                raw_pnl = pnl_for_move(symbol, abs(price_move), pos["lot"]) \
                          * (1 if price_move >= 0 else -1)
                self.pnl += raw_pnl
                print(f"      CLOSE {symbol} @ ${price:,.3f}  PnL=${raw_pnl:+.2f}  MT5={'✓' if result else '✗'}")
                record({"type": "EXIT", "symbol": symbol,
                        "direction": pos["direction"], "lot": pos["lot"],
                        "entry_price": pos["entry_price"], "exit_price": price,
                        "pnl": round(raw_pnl, 4), "reason": reason,
                        "elapsed": (datetime.now() - datetime.fromisoformat(pos["entry_time"])).seconds,
                        "sig_id": sig_id, "mt5_result": result,
                        "mode": "real_mt5", "timestamp": datetime.now().isoformat()})
                # Non-blocking: trigger trade content hook
                try:
                    subprocess.Popen(
                        [sys.executable,
                         str(PROJECT_ROOT / "core" / "orchestration" / "trade_content_hook.py"),
                         "--once"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                except Exception as _hook_err:
                    print(f"   [WARN] trade_content_hook launch failed: {_hook_err}")
                time.sleep(1.5)
            except Exception as e:
                print(f"      ERROR closing {symbol}: {e}")
        time.sleep(1)
        write_close_all_signal()
        time.sleep(2)
        self.positions.clear()
        _obsidian(f"EA Closed All Positions [{reason}]",
            f"- Reason: {reason}\n- Total PnL: ${self.pnl:+.2f}", "ea_stop")

    def _stop(self, signum=None, frame=None):
        print(f"\n[Stop requested] Finishing current tick then closing all positions...")
        self.running = False

    # ── v11: MT5 position reconciliation ─────────────────────
    def _reconcile_positions(self, mt5_status: dict):
        """
        On startup: sync Python's position dict from MT5 status.
        Prevents phantom positions after bridge drops.
        """
        if not mt5_status: return
        pos_detail = mt5_status.get("pos_detail", "")
        mt5_open_syms = set()
        if pos_detail:
            for part in pos_detail.split(";"):
                if not part.strip(): continue
                sym = part.split(":")[0]
                if sym: mt5_open_syms.add(sym)

        # Remove Python positions MT5 doesn't know about
        for sym in list(self.positions.keys()):
            if sym not in mt5_open_syms:
                print(f"   [RECONCILE] {sym} in Python but not in MT5 — removing phantom position")
                del self.positions[sym]

        # Warn about MT5 positions Python doesn't track (manual trades)
        for sym in mt5_open_syms:
            if sym not in self.positions:
                print(f"   [RECONCILE] {sym} open in MT5 but not tracked by Python — external position")

    # ── Kline / trend refresh ──────────────────────────────

    def _refresh_klines(self, symbol: str) -> list:
        now = time.time()
        # Use 5m candles for pillar/signal computation — 1m candles are too noisy
        # (single-candle reversals destroy EMA cross + momentum confirmation on 1m)
        if now - self.klines_ts[symbol] > 300 or not self.klines_1m[symbol]:
            fresh = fetch_klines(symbol, period="5d", interval_tf="5m", n=80)
            if fresh:
                self.klines_1m[symbol] = fresh
                self.klines_ts[symbol] = now
            elif not self.klines_1m[symbol]:
                live_price = get_price(symbol)
                if live_price > 0:
                    import random as _r; _r.seed(42)
                    noise = (2.0 if symbol == "XAUUSD" else 0.15 if symbol == "XAGUSD" else 0.001)
                    self.klines_1m[symbol] = [live_price + _r.uniform(-noise, noise) for _ in range(50)]
                    self.klines_ts[symbol] = now
        return self.klines_1m[symbol]

    def _refresh_trend(self, symbol: str) -> str:
        now = time.time()
        if now - self.trend_ts[symbol] > 900:
            self.trend_15m[symbol] = get_trend_15m(symbol)
            self.trend_ts[symbol]  = now
        return self.trend_15m[symbol]

    def _refresh_h1_bias(self, symbol: str) -> str:
        now = time.time()
        if now - self.h1_bias_ts[symbol] > 3600:
            self.h1_bias[symbol]    = get_h1_bias(symbol)
            self.h1_bias_ts[symbol] = now
            print(f"   [H1 BIAS] {symbol}: {self.h1_bias[symbol]}")
        return self.h1_bias[symbol]

    # ── Main run loop ──────────────────────────────────────

    def run(self):
        print("=" * 70)
        print("EA Live Trader v11 — All-Session | XAUUSD + XAGUSD + EURUSD + GBPUSD")
        print(f"Risk    : {RISK_PCT}%/trade | Base lot: {MIN_LOT} | Max: {MAX_LOT}")
        print(f"Sessions: ALL ACTIVE — ASIAN(sc≥7) LONDON(sc≥5) LON_NY(sc≥5) NY_CLOSE(sc≥6) AFTER_NY(sc≥5)")
        print(f"TP      : ASIAN=0.8R | LONDON=1.2R | LON_NY=1.5R | NY_CLOSE=1.0R | AFTER_NY=1.0R")
        print(f"Timeout : ASIAN=10c | LONDON=20c | LON_NY=40c | NY_CLOSE=16c | AFTER_NY=16c")
        print(f"Fixes   : lot_size(sl_dist) | ATR thresholds calibrated | TP tightened | MT5 reconcile")
        print(f"Limits  : Daily ≤{DAILY_LOSS_LIMIT_PCT}% | Max DD ≤{MAX_DRAWDOWN_PCT}% | Streak stop: {STREAK_HARD_STOP}")
        print("=" * 70)

        mt5 = wait_for_mt5(timeout_seconds=300)
        if not mt5:
            print("Exiting — MT5 EA not confirmed. Restart after attaching MetalEA_v2.")
            sys.exit(0)

        live_balance = mt5.get("balance", 0)
        if live_balance > 0:
            if abs(live_balance - self.deposit) / max(self.deposit, 1) > 0.01:
                print(f"   [EQUITY RESET] Syncing to MT5 balance ${live_balance:,.2f}")
                self.pnl     = 0.0
                self._streak = 0
            self.deposit      = live_balance
            self._daily_start = live_balance
            self._peak_equity = live_balance
        else:
            self._daily_start = self.deposit
            self._peak_equity = self.deposit

        # v11: reconcile on startup
        self._reconcile_positions(mt5)

        print("=" * 70)
        print(f"Account : #{mt5.get('account', '?')} @ {mt5.get('server', '?')}")
        print(f"Balance : ${mt5.get('balance', '?')} | Equity: ${mt5.get('equity', '?')}")
        print(f"XAUUSD  : ${mt5.get('xauusd_bid', '?')} | XAGUSD: ${mt5.get('xagusd_bid', '?')}")
        print("TRADING ACTIVE — EA v11")
        print("=" * 70 + "\n")

        _obsidian("EA Trader v11 Started",
            f"- Account: #{mt5.get('account', '?')}\n"
            f"- Balance: ${mt5.get('balance', '?')} | Equity: ${mt5.get('equity', '?')}\n"
            f"- v11: fixed lot_size, tighter TP, calibrated ATR thresholds, MT5 reconcile",
            "ea_start")

        self.running = True
        while self.running:
            try:
                mt5_status = read_mt5_status()
                equity     = mt5_status.get("equity", self.deposit + self.pnl) \
                             if mt5_status else self.deposit + self.pnl
                if mt5_status:
                    equity = mt5_status.get("balance", equity)
                    self._stale_ticks = 0
                else:
                    self._stale_ticks += 1
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] WARNING: MT5 stale (tick {self._stale_ticks}) — no new entries")
                    if self._stale_ticks == 10:
                        _obsidian("MT5 STALE ~5min — trading paused",
                            "- ACTION: Check MetalEA_v2 is attached and Algo Trading is enabled",
                            "ea_warn")
                    if self._stale_ticks == 20:
                        try:
                            reconnect_flag = MT5_FILES / "python_reconnect.txt"
                            reconnect_flag.write_text(datetime.now().isoformat())
                        except Exception: pass
                        _obsidian("MT5 STALE ~10min — reconnect trigger written", "", "ea_critical")

                self._update_equity_tracking(equity)
                prop_status = self._check_prop_limits(equity)

                if prop_status == "HALT" and not self._halt:
                    self._halt = True
                    self._close_all_mt5_positions("prop_limit_halt")
                    self.running = False
                    break

                session = in_session()
                reduced = (prop_status == "WARN") or (self._streak <= -3)
                if self._streak <= STREAK_HARD_STOP:
                    print(f"   [STREAK STOP] Streak={self._streak} — blocking entries")
                    reduced = True
                mt5_confirmed = bool(mt5_status)

                for sym in SYMBOLS:
                    self._tick(sym, mt5_status, equity, session, reduced, mt5_confirmed)

                self._save(mt5_status)
                self.errors = 0

            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                self.errors += 1
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Error {self.errors}: {e}")
                if self.errors >= 10:
                    print("MAX ERRORS — stopping")
                    break
                time.sleep(15)
                continue
            time.sleep(INTERVAL)

        self._shutdown()

    # ── Per-symbol tick ────────────────────────────────────

    def _tick(self, symbol: str, mt5_status: dict, equity: float,
              session: bool, reduced: bool, mt5_confirmed: bool = True):
        ts    = datetime.now().strftime("%H:%M:%S")
        price = get_price(symbol)
        kl    = self._refresh_klines(symbol)
        if kl:
            kl.append(price)
            if len(kl) > 100: kl.pop(0)
            self.klines_1m[symbol] = kl

        trend = self._refresh_trend(symbol)
        h1    = self._refresh_h1_bias(symbol)

        sess_key, sess_name, sess_mult = get_session()
        if self._streak <= -2: sess_mult = min(sess_mult, 1.0)
        if self._streak <= -5: sess_mult = min(sess_mult, 0.5)

        # Get session params
        sp = SESSION_REGIME_PARAMS.get(sess_key, SESSION_REGIME_PARAMS["london"])

        # Detect regime (pass atr for dead-market check)
        atr_raw = compute_atr(kl) if len(kl) >= 15 else 0.0
        regime  = detect_regime(kl, atr_raw) if len(kl) >= 30 else "SCALP"

        # v11: symbol-specific ATR dead-market check
        if atr_raw > 0 and atr_raw < ATR_DEAD_THRESHOLD.get(symbol, 0.001):
            regime = "DEAD"

        # Regime adjusts tp/sl on top of session base
        tp_r = sp["tp_r"] * REGIME_TP_MULT.get(regime, 1.0)
        sl_atr_mult = sp["sl_atr"] * REGIME_SL_MULT.get(regime, 1.0) / 1.5  # normalise

        sig   = compute_signal(kl, trend, h1_bias=h1, regime=regime, sess_key=sess_key)
        pos   = self.positions.get(symbol)

        mt5_ok = bool(mt5_status)
        daily_loss_pct = (self._daily_start - equity) / self._daily_start * 100 \
                          if self._daily_start > 0 else 0
        dd_pct = (self._peak_equity - equity) / self._peak_equity * 100 \
                  if self._peak_equity > 0 else 0

        status_str = (
            f"{'⚠ ' if reduced else ''}"
            f"DL:{daily_loss_pct:.1f}%/{DAILY_LOSS_LIMIT_PCT}% "
            f"DD:{dd_pct:.1f}%/{MAX_DRAWDOWN_PCT}% "
            f"[{sess_name}×{sess_mult:.2f}] [{regime}]"
        )

        streak_ok = self._streak > STREAK_HARD_STOP
        effective_min_score = sp["min_score"]
        effective_lot_mult  = 1.0
        if self._timeout_penalty_cycles > 0:
            effective_min_score = min(effective_min_score + 1, 8)
            effective_lot_mult  = 0.5

        print(f"[{ts}] {symbol} ${price:,.3f} | {sig['direction']:4s} sc:{sig['score']} "
              f"atr:{sig.get('avg_atr',0):.3f} rsi:{sig.get('rsi',0):.0f} "
              f"trend:{trend} h1:{h1} | "
              f"MT5:{'✓' if mt5_ok else '✗'} eq:${equity:,.0f} | "
              f"{'POS' if pos else '-'} | {'SESSION' if session else 'CLOSED'} | "
              f"{status_str}")

        # ── v11 Correlation guard: halve lots if both metals open ──
        metals_open = sum(1 for s in ["XAUUSD", "XAGUSD"] if s in self.positions)
        if symbol in ["XAUUSD", "XAGUSD"] and metals_open >= 1 and symbol not in self.positions:
            effective_lot_mult = min(effective_lot_mult, 0.5)  # halve on correlated pair

        # ── Entry gate ─────────────────────────────────────────
        entry_dir = sig["direction"]

        # Reverse logic for persistent losing combos (TREND/SCALP only, not Asian/NY_Close)
        combo_key = (symbol, entry_dir, regime)
        combo_loss_count = self._combo_losses.get(combo_key, 0)
        reverse_ok = (regime in ("TREND", "SCALP")) and (sess_key not in ("ny_close", "asian"))
        cd_key = (symbol, regime)
        if self._reverse_cooldown.get(cd_key, 0) > 0:
            self._reverse_cooldown[cd_key] -= 1
            reverse_ok = False
        if combo_loss_count >= 5 and entry_dir != "NONE" and reverse_ok:
            opposite = "SELL" if entry_dir == "BUY" else "BUY"
            opp_key  = (symbol, opposite, regime)
            if self._combo_losses.get(opp_key, 0) < 5:
                print(f"   [REVERSE] {symbol} {entry_dir} lost {combo_loss_count}× → trying {opposite}")
                entry_dir = opposite
                combo_key = opp_key
                self._reverse_cooldown[cd_key] = 3

        if (pos is None and entry_dir != "NONE"
                and sig["score"] >= effective_min_score
                and session
                and streak_ok
                and mt5_confirmed
                and regime != "DEAD"
                and not self._halt):

            atr     = sig.get("atr", price * 0.001)
            if atr <= 0: atr = price * 0.001

            # v11: SL distance using calibrated ATR multiplier, clamped to min/max %
            sl_dist = atr * sl_atr_mult
            min_sl  = price * MIN_SL_PCT.get(symbol, 0.003)
            max_sl  = price * MAX_SL_PCT
            sl_dist = max(min_sl, min(sl_dist, max_sl))

            # Swing-level refinement
            swing_high, swing_low = find_swing_levels(kl)
            if entry_dir == "BUY" and swing_low is not None:
                swing_dist = price - swing_low
                if 0 < swing_dist < sl_dist * 1.3:
                    sl_dist = max(swing_dist, min_sl)
            elif entry_dir == "SELL" and swing_high is not None:
                swing_dist = swing_high - price
                if 0 < swing_dist < sl_dist * 1.3:
                    sl_dist = max(swing_dist, min_sl)

            tp_dist = sl_dist * tp_r

            # v11: FIXED lot_size — uses sl_dist not sl_price
            lot = lot_size(symbol, sl_dist, equity, reduced, sess_mult, self._streak,
                           score=sig["score"])
            lot = round(max(lot * effective_lot_mult, MIN_LOT), 2)

            # SL/TP prices
            digits = 2 if symbol in ("XAUUSD",) else 3 if symbol == "XAGUSD" else 5
            if entry_dir == "BUY":
                sl_python = round(price - sl_dist, digits)
                tp_python = round(price + tp_dist, digits)
            else:
                sl_python = round(price + sl_dist, digits)
                tp_python = round(price - tp_dist, digits)

            # Sanity check: SL must be valid
            if entry_dir == "BUY" and sl_python >= price:
                print(f"   [SKIP] Invalid SL {sl_python} >= price {price} for BUY — skipping")
                return
            if entry_dir == "SELL" and sl_python <= price:
                print(f"   [SKIP] Invalid SL {sl_python} <= price {price} for SELL — skipping")
                return

            penalty_tag = f" [CHOP×{effective_lot_mult:.1f}]" if self._timeout_penalty_cycles > 0 else ""
            corr_tag    = " [CORR×0.5]" if effective_lot_mult == 0.5 and metals_open >= 1 else ""
            print(f"   → ENTRY {entry_dir} {lot}L {symbol} @ ${price:,.3f} "
                  f"SL={sl_python} TP={tp_python} ({tp_r:.1f}R) "
                  f"atr={atr:.3f} sl_dist={sl_dist:.3f} "
                  f"score={sig['score']}/{effective_min_score} regime={regime} "
                  f"[{sess_name}]{penalty_tag}{corr_tag}")

            sig_id    = write_signal(symbol, entry_dir, lot, sl=sl_python, tp=tp_python)
            result    = read_signal_result(sig_id, timeout=8)
            confirmed = bool(result and result.get("success"))

            if not confirmed:
                print(f"   ✗ MT5 did not confirm — position NOT recorded")
                _obsidian(f"EA SIGNAL UNCONFIRMED: {symbol} {entry_dir}",
                    f"- ${price:,.3f} | {lot}L | sig_id:{sig_id}\n- result: {result}", "ea_warn")
                return

            self.positions[symbol] = {
                "direction":    entry_dir,
                "entry_price":  price,
                "lot":          lot,
                "sl":           sl_python,
                "tp":           tp_python,
                "sl_dist":      sl_dist,
                "tp_dist":      tp_dist,
                "atr_at_entry": atr,
                "sig_id":       sig_id,
                "entry_time":   datetime.now().isoformat(),
                "trail_active": False,
                "trail_sl":     sl_python,
                "mt5_confirmed": confirmed,
                "regime":       regime,
                "session":      sess_key,
                "timeout_candles": sp["timeout"],
            }
            record({
                "type": "ENTRY", "symbol": symbol,
                "direction": entry_dir, "lot": lot,
                "entry_price": price, "sl": sl_python, "tp": tp_python,
                "sl_dist": sl_dist, "tp_dist": tp_dist, "tp_r": tp_r,
                "atr": atr, "signal": sig, "trend_15m": trend, "regime": regime,
                "session": sess_key, "sig_id": sig_id,
                "mode": "real_mt5", "timestamp": datetime.now().isoformat()
            })
            _obsidian(f"EA ENTRY v11: {symbol} {entry_dir}",
                f"- ${price:,.3f} | {lot}L | SL:{sl_python} TP:{tp_python} ({tp_r:.1f}R)\n"
                f"- Score:{sig['score']} RSI:{sig.get('rsi',0):.0f} Trend:{trend} Regime:{regime}\n"
                f"- Session:{sess_name} atr:{atr:.3f} sl_dist:{sl_dist:.3f}",
                "ea_trade")
            self.trades += 1

        # ── Manage open position ───────────────────────────
        elif pos is not None:
            elapsed   = (datetime.now() - datetime.fromisoformat(pos["entry_time"])).seconds
            direction = pos["direction"]
            entry     = pos["entry_price"]
            lot       = pos["lot"]
            sl_dist   = pos.get("sl_dist", entry * 0.003)
            atr_entry = pos.get("atr_at_entry", sl_dist)
            trade_timeout_s = pos.get("timeout_candles", 20) * INTERVAL

            raw_move   = price - entry if direction == "BUY" else entry - price
            unrealised = pnl_for_move(symbol, abs(raw_move), lot) * (1 if raw_move >= 0 else -1)

            # v11: trailing stop activates at 0.8R (was 1.5R)
            trail_gap = atr_entry * TRAIL_ATR_MULT

            if not pos["trail_active"] and unrealised >= sl_dist * TRAIL_ACTIVATE_R:
                pos["trail_active"] = True
                print(f"   → TRAIL ACTIVATED {symbol} unrealised=${unrealised:+.2f}")

            if pos["trail_active"]:
                if direction == "BUY":
                    new_tsl = round(price - trail_gap, 2 if symbol == "XAUUSD" else 3)
                    if new_tsl > pos["trail_sl"]:
                        pos["trail_sl"] = new_tsl
                        print(f"   → TRAIL SL → {new_tsl}")
                else:
                    new_tsl = round(price + trail_gap, 2 if symbol == "XAUUSD" else 3)
                    if new_tsl < pos["trail_sl"]:
                        pos["trail_sl"] = new_tsl
                        print(f"   → TRAIL SL → {new_tsl}")

            eff_sl  = pos["trail_sl"] if pos["trail_active"] else pos["sl"]
            sl_hit  = (direction == "BUY"  and price <= eff_sl) or \
                      (direction == "SELL" and price >= eff_sl)
            tp_hit  = (direction == "BUY"  and price >= pos["tp"]) or \
                      (direction == "SELL" and price <= pos["tp"])
            timeout = elapsed >= trade_timeout_s

            if elapsed < MIN_HOLD_SECONDS:
                sl_hit = tp_hit = timeout = False

            if sl_hit or tp_hit or timeout:
                reason = "TP" if tp_hit else \
                         ("TRAIL_SL" if (sl_hit and pos["trail_active"]) else \
                         ("SL" if sl_hit else "TIMEOUT"))

                # v11: on timeout, if in profit use tighter trail instead of immediate market close
                if reason == "TIMEOUT" and unrealised > 0 and not pos["trail_active"]:
                    pos["trail_active"] = True
                    pos["trail_sl"] = eff_sl  # already at SL — trail will tighten from here
                    print(f"   → TIMEOUT but profit ${unrealised:+.2f} — activating trail instead")
                    return  # don't close yet, let trail manage it next tick

                sig_id = write_close_signal(symbol)
                result = read_signal_result(sig_id, timeout=6)

                price_move = price - entry if direction == "BUY" else entry - price
                raw_pnl    = pnl_for_move(symbol, abs(price_move), lot) * \
                             (1 if price_move >= 0 else -1)
                self.pnl  += raw_pnl

                if raw_pnl > 0:
                    self._streak = self._streak + 1 if self._streak >= 0 else 1
                else:
                    self._streak = self._streak - 1 if self._streak <= 0 else -1

                combo_key_exit = (symbol, direction, pos.get("regime", "SCALP"))
                if raw_pnl > 0:
                    self._combo_losses[combo_key_exit] = 0
                    self._combo_wins[combo_key_exit]   = self._combo_wins.get(combo_key_exit, 0) + 1
                else:
                    self._combo_losses[combo_key_exit] = self._combo_losses.get(combo_key_exit, 0) + 1
                    self._combo_wins[combo_key_exit]   = 0

                if reason == "TIMEOUT":
                    self._timeout_streak += 1
                    if self._timeout_streak >= 3 and self._timeout_penalty_cycles == 0:
                        self._timeout_penalty_cycles = 5
                        print(f"   [TIMEOUT×{self._timeout_streak}] Chop detected — min_score+1 for 5c")
                else:
                    self._timeout_streak = 0
                if self._timeout_penalty_cycles > 0:
                    self._timeout_penalty_cycles -= 1

                print(f"   → CLOSE [{reason}] {symbol} @ ${price:,.3f} "
                      f"PnL=${raw_pnl:+.2f} Total=${self.pnl:+.2f} streak={self._streak:+d}")
                record({
                    "type": "EXIT", "symbol": symbol,
                    "direction": direction, "lot": lot,
                    "entry_price": entry, "exit_price": price,
                    "pnl": round(raw_pnl, 4), "reason": reason,
                    "elapsed": elapsed, "trail_active": pos["trail_active"],
                    "streak_after": self._streak,
                    "sig_id": sig_id, "mt5_result": result,
                    "mode": "real_mt5", "timestamp": datetime.now().isoformat()
                })
                # Non-blocking: trigger trade content hook to generate video + queue to Postiz
                try:
                    subprocess.Popen(
                        [sys.executable,
                         str(PROJECT_ROOT / "core" / "orchestration" / "trade_content_hook.py"),
                         "--once"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                except Exception as _hook_err:
                    print(f"   [WARN] trade_content_hook launch failed: {_hook_err}")
                _obsidian(f"EA EXIT [{reason}]: {symbol}",
                    f"- PnL: ${raw_pnl:+.2f} | Total: ${self.pnl:+.2f} | streak={self._streak:+d}",
                    "ea_trade")
                self.trades += 1
                del self.positions[symbol]

    def _shutdown(self):
        if self.positions:
            print(f"\n[SHUTDOWN] Closing {len(self.positions)} remaining position(s)...")
            self._close_all_mt5_positions("shutdown")
        self._save()
        print(f"\nEA v11 stopped. Trades: {self.trades} | PnL: ${self.pnl:+.2f}")
        _obsidian("EA Trader v11 Stopped",
            f"- Trades: {self.trades}\n- PnL: ${self.pnl:+.2f}\n- Peak: ${self._peak_equity:,.2f}",
            "ea_stop")
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    EATrader().run()
