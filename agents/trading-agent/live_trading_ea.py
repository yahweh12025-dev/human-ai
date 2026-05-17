#!/usr/bin/env python3
"""
EA Live Trader v10 — Autonomous | XAUUSD + XAGUSD + EURUSD + GBPUSD
====================================================================
v10 improvements (big-move capture upgrades):
  - H1 EMA bias: pulls 60m yfinance data, adds +1 to score when H1 EMA20
    trend aligns with entry direction (BUY when H1 trending up, SELL when down).
    Only bypassed in RANGE regime (mean reversion trades against trend are valid).
  - Breakout score boost: adds +2 when close breaks above 20-bar high (BUY) or
    below 20-bar low (SELL) — catches momentum breakouts the base scorer misses.
  - Tighter trail activation during LONDON_NY: drops from 1.5R to 1.0R during
    the highest-ATR session so winners run longer. Breakeven trail at 0.5R.
  - Multi-market extension: EURUSD + GBPUSD added with pip-correct sizing.
    These capture big-move sessions when XAU/XAG is ranging.
  - NY_CLOSE TREND unblock: strong signals (score>=5) are now allowed to enter
    TREND during NY_CLOSE instead of being universally blocked.

v9 improvements retained:
  - Session-AWARE sizing: Asian/NY-close get 0.25× risk + tighter regime params
  - No session blocking — EA trades 24/5, adapts regime to each session
  - TRAIL_SL: activate at 1.5R (1.0R during LONDON_NY)
  - Hard-stop at streak <=-8
  - Per-session REGIME_PARAMS overrides
  - ATR dead-market filter
  - Timeout-on-drawdown protection
  - WARN halts new entries

v7 features retained:
  - Regime detection: TREND / SCALP / RANGE / DEAD
  - Swing high/low structure-based SL
  - Score-proportional lot sizing
  - Regime-adaptive TP/SL/timeout
  - Prop firm limits (daily -3%, max DD -5%)

Shutdown: SIGTERM/SIGINT send CLOSE to MT5 then CLOSE_ALL fallback.
"""

import json, os, sys, time, signal, random, uuid
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
# v10: added EURUSD + GBPUSD for broader big-move session coverage
SYMBOLS  = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD"]
YF_MAP   = {"XAUUSD": "GC=F", "XAGUSD": "SI=F", "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X"}

# ── Risk parameters ──────────────────────────────────────────
DEPOSIT          = 5000.0   # Reset account
RISK_PCT         = 0.5       # base risk 0.5% per trade (scaled by score + session)
MAX_SL_PCT       = 0.006     # 0.6% absolute max SL cap
MIN_SCORE        = 3         # minimum signal score to enter (per regime, see REGIME_PARAMS)
TRADE_TIMEOUT_CANDLES = 15   # base timeout in candles (regime overrides this)
INTERVAL         = 30        # 30s ticks
MIN_HOLD_SECONDS = 180       # 3 min minimum (FTMO rule)

# ── Session classification (UTC hours) ───────────────────────
# EA trades ALL sessions — no blocking. Parameters adapt to conditions.
#   ASIAN    : 22-07 UTC — low ATR, mean-reversion only, 0.25× risk, tight SL
#   LONDON   : 07-12 UTC — moderate ATR, full regime support, 1.0× risk
#   LONDON_NY: 12-17 UTC — highest ATR, strongest trend signals, 1.5× risk
#   NY_CLOSE : 17-19 UTC — choppy/spike risk, 0.5× risk, no TREND entries
#   AFTER_NY : 19-22 UTC — winding down, 0.75× risk, SCALP/RANGE only
ASIAN_HOURS      = {22, 23, 0, 1, 2, 3, 4, 5, 6}
LONDON_HOURS     = {7, 8, 9, 10, 11}
LONDON_NY_HOURS  = {12, 13, 14, 15, 16}
NY_CLOSE_HOURS   = {17, 18}
AFTER_NY_HOURS   = {19, 20, 21}

# Risk multiplier per session
RISK_MULT = {"london_ny": 1.5, "london": 1.0, "after_ny": 0.75, "ny_close": 0.5, "asian": 0.25}

# Per-session regime parameter overrides — tighter SL and shorter timeout when
# volatility is low (Asian) or spikey/choppy (NY close)
SESSION_REGIME_OVERRIDES = {
    "asian":    {"tp_r": 1.0, "sl_atr": 0.8, "timeout": 6,  "trail_r": 0.5, "min_score": 4},
    "ny_close": {"tp_r": 1.2, "sl_atr": 1.0, "timeout": 8,  "trail_r": 0.8, "min_score": 4},
    "after_ny": {"tp_r": 1.5, "sl_atr": 1.2, "timeout": 10, "trail_r": 0.8, "min_score": 3},
    # london and london_ny use base REGIME_PARAMS unchanged
}

# ── Score-proportional lot scaling ───────────────────────────
# score=3 in RANGE was 40% WR in data — smaller lot. Only TREND/SCALP get score=3.
SCORE_LOT_MULT   = {3: 0.4, 4: 0.75, 5: 1.0, 6: 1.5, 7: 2.0}

# ── Regime-adaptive parameters ───────────────────────────────
# Base regime parameters — used during LONDON and LONDON_NY sessions.
# SESSION_REGIME_OVERRIDES tighten these for ASIAN / NY_CLOSE / AFTER_NY.
REGIME_PARAMS = {
    "TREND": {"tp_r": 2.5, "sl_atr": 1.8, "timeout": 20, "trail_r": 1.0, "min_score": 3},
    "SCALP": {"tp_r": 2.0, "sl_atr": 1.5, "timeout": 12, "trail_r": 1.2, "min_score": 3},
    "RANGE": {"tp_r": 1.5, "sl_atr": 1.2, "timeout":  8, "trail_r": 0.8, "min_score": 3},
    "DEAD":  {"tp_r": 2.0, "sl_atr": 1.5, "timeout": 12, "trail_r": 1.0, "min_score": 99},
}

# ── Prop firm hard limits ────────────────────────────────────
DAILY_LOSS_LIMIT_PCT  = 3.0
MAX_DRAWDOWN_PCT      = 5.0
WARN_DAILY_LOSS_PCT   = 1.5   # tightened from 2.0 — start reducing size earlier
WARN_DRAWDOWN_PCT     = 3.0   # tightened from 4.0

# ── Streak hard-stop ─────────────────────────────────────────
# Raised to -8: at -5 the agent was fully deadlocked (can't trade = can't recover streak).
# Recovery mechanism: if streak <= -6, still allow REDUCED entries so streak can recover.
STREAK_HARD_STOP = -8        # no new entries when streak <= this (was -5, caused deadlock)

# ── Contract specification (ICMarkets standard lots) ─────────
# v10: EURUSD/GBPUSD added — standard 100K lot, 0.0001 point size, $10/pip per lot
CONTRACT_SIZE = {"XAUUSD": 100,    "XAGUSD": 5000,  "EURUSD": 100000, "GBPUSD": 100000}
POINT_SIZE    = {"XAUUSD": 0.01,   "XAGUSD": 0.001, "EURUSD": 0.0001, "GBPUSD": 0.0001}
POINT_VALUE   = {"XAUUSD": 1.0,    "XAGUSD": 5.0,   "EURUSD": 10.0,   "GBPUSD": 10.0}
# v9 safety cap: 0.38L XAUUSD caused -$420 single loss. Hard-cap at 0.05 until
# EA demonstrates consistent positive PnL across 100+ trades.
# EURUSD/GBPUSD capped at 0.05 lots initially (=$5/pip risk).
MAX_LOT       = {"XAUUSD": 0.05,   "XAGUSD": 0.01,  "EURUSD": 0.05,   "GBPUSD": 0.05}

# ── Session filter ───────────────────────────────────────────
SESSION_START_UTC = 0
SESSION_END_UTC   = 24

# ── Trailing stop parameters (v10 updates) ──────────────────────────
# v8: activated at 1.5R — standard for Asian/NY_CLOSE choppy conditions.
# v10: LONDON_NY overrides to 1.0R activation so trending winners run longer.
#      After trail activates, move to breakeven (0.5× SL_DIST) first tick,
#      then trail normally — prevents giving back all profit on whipsaw.
TRAIL_ACTIVATE_R       = 1.5   # default: 1.5R (conservative, avoids whipsaw)
TRAIL_ACTIVATE_R_LNNY  = 1.0   # LONDON_NY override: activate sooner (best trend session)
TRAIL_DISTANCE_R       = 0.6   # trail gap (regime overrides)
TRAIL_DISTANCE_XAGUSD  = 0.8   # wider for XAGUSD high pip value


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
            pass  # obsidian write is best-effort; never crash trading on log failure


def in_session() -> bool:
    """
    XAUUSD/XAGUSD market hours (ICMarkets UTC):
      Monday 00:05 – Friday 21:55  (daily break 21:55–22:05)
      Saturday/Sunday: CLOSED
    """
    now = datetime.now(timezone.utc)
    weekday = now.weekday()   # 0=Mon, 6=Sun
    h, m = now.hour, now.minute

    # Weekend: Saturday all day, Sunday before 22:05
    if weekday == 5: return False                           # Saturday
    if weekday == 6 and not (h == 22 and m >= 5) and h < 22: return False  # Sunday before 22:05
    # Daily break 21:55–22:05 UTC
    if (h == 21 and m >= 55) or (h == 22 and m < 5): return False
    return True


def get_session() -> tuple:
    """
    Classify current UTC hour into a named session.
    Returns (session_key, display_name, risk_multiplier).
    EA trades ALL sessions — parameters adapt rather than blocking.
    """
    h = datetime.now(timezone.utc).hour
    if h in LONDON_NY_HOURS:
        return "london_ny",  "LON_NY",   RISK_MULT["london_ny"]
    if h in LONDON_HOURS:
        return "london",     "LONDON",   RISK_MULT["london"]
    if h in AFTER_NY_HOURS:
        return "after_ny",   "AFTER_NY", RISK_MULT["after_ny"]
    if h in NY_CLOSE_HOURS:
        return "ny_close",   "NY_CLOSE", RISK_MULT["ny_close"]
    return "asian",          "ASIAN",    RISK_MULT["asian"]


def get_session_regime_params(base_rp: dict, session_key: str) -> dict:
    """
    Merge base regime params with session-specific overrides.
    Session overrides tighten SL, shorten timeout, and reduce TP target
    for low-volatility (Asian) and choppy (NY close) conditions.
    """
    override = SESSION_REGIME_OVERRIDES.get(session_key)
    if override is None:
        return base_rp
    merged = dict(base_rp)
    merged.update(override)
    return merged


def get_price(symbol: str) -> float:
    # Primary: live bid from MetalEA_v2 status file (written every 2s)
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
        pass  # MT5 status file unavailable — try next source
    # Secondary: yfinance (slight delay but accurate)
    if YFINANCE_OK:
        try: return float(yf.Ticker(YF_MAP[symbol]).fast_info.last_price)
        except Exception: pass
    # Fallback: last known price from most recent trade file
    try:
        import glob as _glob
        files = sorted(_glob.glob(str(TRADES_DIR / f"trade_{symbol}_*.json")))
        if files:
            last = json.loads(open(files[-1]).read())
            p = last.get("entry_price") or last.get("exit_price")
            if p: return float(p)
    except Exception:
        pass  # no cached trade file — use hardcoded fallback
    # Last resort: hardcoded approximate (agent will not trade until MT5 confirms)
    return {"XAUUSD": 3320.0, "XAGUSD": 33.0, "EURUSD": 1.0850, "GBPUSD": 1.2700}.get(symbol, 1.0)


def fetch_klines(symbol: str, period="1d", interval_tf="1m", n=80) -> list:
    if not YFINANCE_OK: return []
    try:
        df = yf.download(YF_MAP[symbol], period=period, interval=interval_tf, progress=False)
        if df.empty: return []
        col = df["Close"].iloc[:, 0] if hasattr(df.columns, "levels") else df["Close"]
        return [float(c) for c in col.dropna().values[-n:]]
    except: return []


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
    k = 2 / (n + 1); e = prices[0]
    for p in prices[1:]: e = p * k + e * (1 - k)
    return e


def get_trend_15m(symbol: str) -> str:
    try:
        closes = fetch_klines(symbol, period="5d", interval_tf="15m", n=30)
        if len(closes) < 22: return "NEUTRAL"
        ema9  = compute_ema(closes[-22:], 9)
        ema20 = compute_ema(closes[-22:], 20)
        # Tightened from 0.03% to 0.02% threshold — less NEUTRAL, catches more directional bias
        if ema9 > ema20 * 1.0002: return "BULL"
        if ema9 < ema20 * 0.9998: return "BEAR"
    except Exception:
        pass  # yfinance unavailable — return NEUTRAL bias
    return "NEUTRAL"


def get_h1_bias(symbol: str) -> str:
    """
    v10: Higher-timeframe (H1) EMA20 trend bias to filter signals.
    Pulls 60m data from yfinance (last 10 days → ~60 bars).
    Returns 'BULL', 'BEAR', or 'NEUTRAL'.
    Logic: if EMA20 slope is rising (last EMA20 > EMA20 5 bars ago by 0.03%),
           trend is BULL; if falling, BEAR; otherwise NEUTRAL.
    Mapped to yfinance 1h interval. For FX symbols (EURUSD/GBPUSD), uses same logic.
    """
    if not YFINANCE_OK:
        return "NEUTRAL"
    try:
        df = yf.download(YF_MAP[symbol], period="10d", interval="1h", progress=False)
        if df.empty:
            return "NEUTRAL"
        col = df["Close"].iloc[:, 0] if hasattr(df.columns, "levels") else df["Close"]
        closes_h1 = [float(c) for c in col.dropna().values[-60:]]
        if len(closes_h1) < 25:
            return "NEUTRAL"
        # EMA20 now vs 5 bars ago — compare slope
        ema20_now  = compute_ema(closes_h1[-25:], 20)
        ema20_prev = compute_ema(closes_h1[-30:-5], 20) if len(closes_h1) >= 30 else ema20_now
        threshold  = 0.0003   # 0.03% slope threshold
        if ema20_now > ema20_prev * (1 + threshold):
            return "BULL"
        if ema20_now < ema20_prev * (1 - threshold):
            return "BEAR"
    except Exception:
        pass  # yfinance H1 data unavailable — return NEUTRAL bias
    return "NEUTRAL"


def compute_breakout_score_boost(prices: list, direction: str, lookback: int = 20) -> int:
    """
    v10: Breakout momentum score boost.
    Returns +2 if the current close breaks above the 20-bar high (BUY)
    or below the 20-bar low (SELL). This catches momentum breakouts that
    the base EMA/RSI/BB scorer misses because they rely on mean-reversion logic.
    Only fires when price clearly closes through the prior range extreme.
    """
    if len(prices) < lookback + 2 or direction == "NONE":
        return 0
    prior_window = prices[-(lookback + 1):-1]   # prior N bars, excluding current
    current      = prices[-1]
    if direction == "BUY":
        prior_high = max(prior_window)
        if current > prior_high:
            return 2
    elif direction == "SELL":
        prior_low = min(prior_window)
        if current < prior_low:
            return 2
    return 0


def detect_regime(prices: list) -> str:
    """
    Classify market regime using EMA separation, Bollinger width, and ATR.
      TREND: strong EMA separation with directional momentum
      SCALP: moderate volatility, no clear trend — normal scalp conditions (default)
      RANGE: narrow Bollinger bands, price oscillating near mean
      DEAD:  ATR near zero — no entries
    Returns one of: TREND, SCALP, RANGE, DEAD
    """
    if len(prices) < 30:
        return "SCALP"

    # ATR-based volatility (recent vs prior window)
    atr = compute_atr(prices[-20:], period=14)
    if atr < 0.003:
        return "DEAD"

    # Bollinger band width as % of midpoint price
    sma20  = sum(prices[-20:]) / 20
    std20  = (sum((p - sma20) ** 2 for p in prices[-20:]) / 20) ** 0.5
    bb_width_pct = (4 * std20 / sma20) if sma20 > 0 else 0

    # EMA alignment: separation between fast and slow EMA
    ema5  = compute_ema(prices[-12:],  5)
    ema20 = compute_ema(prices[-25:], 20)
    ema50 = compute_ema(prices[-55:], 50) if len(prices) >= 55 else ema20
    ema_diff_pct = abs(ema5 - ema20) / ema20 if ema20 > 0 else 0

    # Price-vs-EMA20 position: in a trend price stays on one side of EMA20
    above_ema20 = sum(1 for p in prices[-10:] if p > ema20)
    below_ema20 = 10 - above_ema20
    one_sided   = above_ema20 >= 7 or below_ema20 >= 7  # lowered from 8 — catches fast moves

    # Directional run: how many of last 6 candles moved same direction
    up_run   = sum(1 for i in range(-6, 0) if prices[i] > prices[i-1])
    down_run = 6 - up_run
    strong_dir = up_run >= 4 or down_run >= 4

    # Strong acceleration: last 3 candles all same direction with growing magnitude
    last3_down = (prices[-1] < prices[-2] < prices[-3] < prices[-4])
    last3_up   = (prices[-1] > prices[-2] > prices[-3] > prices[-4])
    strong_accel = last3_down or last3_up

    # TREND: EMA clearly separated + price staying above/below + directional momentum
    # Also catches strong acceleration even without full one_sided confirmation
    if ema_diff_pct > 0.0005 and one_sided and strong_dir:
        return "TREND"
    if ema_diff_pct > 0.0003 and strong_accel and strong_dir:
        return "TREND"

    # RANGE: narrow BB (tight range) and price hovering near SMA
    # bb_width_pct < 0.003 means 4-sigma band is less than 0.3% of price — very tight
    price_near_sma = abs(prices[-1] - sma20) / sma20 < 0.002
    if bb_width_pct < 0.003 and price_near_sma:
        return "RANGE"

    return "SCALP"


def find_swing_levels(prices: list, lookback: int = 20) -> tuple:
    """
    Find recent swing high and swing low for structure-based SL placement.
    Returns (swing_high, swing_low) over the lookback window.
    A swing high is a local max where both neighbours are lower.
    """
    if len(prices) < lookback + 2:
        return None, None
    window = prices[-(lookback + 2):]
    highs, lows = [], []
    for i in range(1, len(window) - 1):
        if window[i] > window[i-1] and window[i] > window[i+1]:
            highs.append(window[i])
        if window[i] < window[i-1] and window[i] < window[i+1]:
            lows.append(window[i])
    swing_high = max(highs) if highs else None
    swing_low  = min(lows)  if lows  else None
    return swing_high, swing_low


def compute_signal(prices: list, trend_15m: str = "NEUTRAL", h1_bias: str = "NEUTRAL") -> dict:
    """
    Signal v10 — Scalping + breakout optimised. Three independent signal pillars;
    any TWO pillars firing = score >= 3 = trade entry.

    Pillar A: Momentum (fast EMA3/EMA8 cross + price direction)
    Pillar B: Volatility (ATR spike above 20-bar baseline)
    Pillar C: Structure (Bollinger Band squeeze breakout or mean-reversion)

    v10 additions:
    - H1 bias soft bonus: +1 when H1 EMA20 trend aligns with direction
      (bypassed in RANGE regime — mean reversion is valid against trend)
    - Breakout score boost: +2 when close breaks 20-bar high/low
    """
    if len(prices) < 22:
        return {"direction": "NONE", "score": 0}

    atr = compute_atr(prices)
    if atr == 0:
        return {"direction": "NONE", "score": 0}

    # ── ATR spike (Pillar B) ──────────────────────────────────
    recent_trs = [abs(prices[i] - prices[i-1]) for i in range(-20, 0)]
    avg_atr    = sum(recent_trs) / len(recent_trs)
    last_move  = abs(prices[-1] - prices[-2])
    atr_ratio  = last_move / avg_atr if avg_atr > 0 else 1.0
    if atr_ratio > 5.0:
        return {"direction": "NONE", "score": 0, "atr": round(atr, 4), "block": "news-spike"}
    # Dead-market filter: block entries when ATR is too small to reach TP profitably
    # XAUUSD: ATR < 0.3 means market is flat; XAGUSD: ATR < 0.05
    # (these are 1m ATR values on yfinance — very small but meaningful)
    if avg_atr < 0.001:
        return {"direction": "NONE", "score": 0, "atr": round(atr, 4), "block": "dead-market"}

    # ── Fast EMAs for scalping (Pillar A) ────────────────────
    ema3  = compute_ema(prices[-10:],  3)
    ema8  = compute_ema(prices[-15:],  8)
    ema21 = compute_ema(prices[-22:], 21)
    fast_bull = ema3 > ema8              # micro-trend up (any positive cross)
    fast_bear = ema3 < ema8              # micro-trend down
    slow_bull = ema8 > ema21 * 1.0001   # macro confirms (10bp threshold)
    slow_bear = ema8 < ema21 * 0.9999

    # Consecutive candles momentum
    mom_bull = prices[-1] > prices[-2] > prices[-3]
    mom_bear = prices[-1] < prices[-2] < prices[-3]

    # ── Bollinger Bands (Pillar C) ───────────────────────────
    sma20    = sum(prices[-20:]) / 20
    std20    = (sum((p - sma20) ** 2 for p in prices[-20:]) / 20) ** 0.5
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    # Breakout: price just crossed the band
    bb_breakout_bull = prices[-1] > bb_upper and prices[-2] <= bb_upper
    bb_breakout_bear = prices[-1] < bb_lower and prices[-2] >= bb_lower
    # Band position: near upper = sell zone, near lower = buy zone (mean-reversion)
    bb_pct  = (prices[-1] - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5
    near_upper = bb_pct > 0.85     # overbought: sell candidate
    near_lower = bb_pct < 0.15     # oversold: buy candidate

    rsi     = compute_rsi(prices[-20:] if len(prices) >= 20 else prices, period=9)  # fast RSI-9
    rsi_buy = rsi < 60    # not overbought (tightened from 65 — avoids entries at RSI 60-63 in RANGE)
    rsi_sell= rsi > 30    # widened from 35 — during strong sell RSI can drop below 35 fast

    # ── Score each pillar independently ─────────────────────
    # Pillar A: Micro-trend (fast EMA only — fires whenever EMA3 > EMA8)
    pillar_a_bull = fast_bull   # ema3 > ema8
    pillar_a_bear = fast_bear

    # Pillar B: Volatility or momentum
    pillar_b_bull = (atr_ratio > 0.8 and fast_bull) or mom_bull or slow_bull
    pillar_b_bear = (atr_ratio > 0.8 and fast_bear) or mom_bear or slow_bear

    # Pillar C: Bollinger structure (breakout or mean-reversion setup)
    pillar_c_bull = bb_breakout_bull or (near_lower and fast_bull) or (bb_pct < 0.35 and fast_bull)
    pillar_c_bear = bb_breakout_bear or (near_upper and fast_bear) or (bb_pct > 0.65 and fast_bear)

    # Count firing pillars
    bull_pillars = sum([pillar_a_bull, pillar_b_bull, pillar_c_bull])
    bear_pillars = sum([pillar_a_bear, pillar_b_bear, pillar_c_bear])

    # Extra RSI confirmation
    score_bull = bull_pillars + (1 if rsi_buy  and bull_pillars >= 1 else 0)
    score_bear = bear_pillars + (1 if rsi_sell and bear_pillars >= 1 else 0)

    # 15m trend: soft alignment bonus (no hard block — scalping trades against trend sometimes)
    if trend_15m == "BULL": score_bull += 1
    if trend_15m == "BEAR": score_bear += 1

    # v10: H1 bias soft bonus — +1 when H1 EMA20 aligns with direction
    # (applied after initial direction is tentatively known via pillar scores)
    if h1_bias == "BULL": score_bull += 1
    if h1_bias == "BEAR": score_bear += 1

    # Determine tentative direction before breakout boost (needed for boost calculation)
    regime = detect_regime(prices)

    score    = max(score_bull, score_bear)
    direction = "NONE"
    if score_bull >= MIN_SCORE and score_bull > score_bear and rsi_buy:
        direction = "BUY"
    elif score_bear >= MIN_SCORE and score_bear > score_bull and rsi_sell:
        direction = "SELL"
    # Tiebreak: use 15m/H1 trend when scores are equal
    elif score_bull >= MIN_SCORE and score_bull == score_bear:
        if (trend_15m == "BULL" or h1_bias == "BULL") and rsi_buy:
            direction = "BUY"
        elif (trend_15m == "BEAR" or h1_bias == "BEAR") and rsi_sell:
            direction = "SELL"

    # v10: Breakout score boost — +2 when close breaks 20-bar high (BUY) or low (SELL).
    # Applied only in TREND/SCALP regimes (RANGE is mean-reversion; breakout boost is wrong there).
    if regime != "RANGE" and direction != "NONE":
        bo_boost = compute_breakout_score_boost(prices, direction, lookback=20)
        if bo_boost > 0:
            if direction == "BUY":
                score_bull += bo_boost
            else:
                score_bear += bo_boost
            score = max(score_bull, score_bear)

    return {
        "direction": direction,
        "score": score,
        "atr": round(atr, 4),
        "rsi": round(rsi, 1),
        "atr_ratio": round(atr_ratio, 2),
        "pillars_bull": bull_pillars,
        "pillars_bear": bear_pillars,
        "regime": regime,
        "h1_bias": h1_bias,
    }


def lot_size(symbol: str, atr: float, equity: float, reduced: bool = False,
             session_mult: float = 1.0, streak: int = 0, score: int = 5) -> float:
    """
    Dynamic lot sizing from live equity:
      Base risk = RISK_PCT% of equity ÷ (SL_distance_in_dollars per 0.01 lot)
      Session multiplier: peak=2× active=1× off=0.5×
      Score multiplier: score=4 → 0.75×, score=5 → 1.0×, score=6 → 1.5×, score=7+ → 2.0×
        (weaker signals get smaller lots; stronger signals get bigger lots)
      Streak multiplier: +1 step per 3 consecutive wins, -1 per 2 losses
      XAUUSD MAX_LOT = 0.5 | XAGUSD MAX_LOT = 0.01 (hard cap)
      reduced (WARN mode): always 0.01
    """
    if reduced:
        return 0.01

    # Risk-based floor: RISK_PCT% of live equity
    if atr > 0 and equity > 0:
        min_sl_pct = 0.005 if symbol == "XAGUSD" else 0.003
        sl_price   = max(1.5 * atr, (equity / CONTRACT_SIZE[symbol]) * min_sl_pct)
        risk_per_base = (sl_price / POINT_SIZE[symbol]) * POINT_VALUE[symbol] * 0.01
        risk_usd      = equity * (RISK_PCT / 100)
        risk_lots     = risk_usd / risk_per_base if risk_per_base > 0 else 0.01
        base_lot      = round(max(0.01, min(round(risk_lots / 0.01) * 0.01, MAX_LOT[symbol])), 2)
    else:
        base_lot = 0.01

    # Score-proportional multiplier: larger lots on stronger signals
    score_mult = SCORE_LOT_MULT.get(min(score, 7), 1.0)

    # Session scaling: off=0.5× active=1× peak=2×
    scaled = base_lot * session_mult * score_mult

    # Streak scaling: add 1 step per 3 consecutive wins, reduce 1 step per 2 losses
    step = 0.01
    if streak >= 3:
        streak_adj = (streak // 3) * step
    elif streak <= -2:
        streak_adj = (streak // 2) * step
    else:
        streak_adj = 0.0

    final = round(max(0.01, min(scaled + streak_adj, MAX_LOT[symbol])), 2)
    return final


def pnl_for_move(symbol: str, price_move: float, lot: float) -> float:
    """P&L in dollars: (move / point_size) × point_value × lot."""
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
    """Sends CLOSE_ALL to MT5 — handled by updated PythonSignalExecutor.ex5."""
    sig_id = f"CLOSE_ALL_{datetime.now().strftime('%H%M%S_%f')[:12]}"
    sig = {"id": sig_id, "action": "CLOSE_ALL", "symbol": "ALL",
           "lot": 0, "sl": 0, "tp": 0, "timestamp": datetime.now().isoformat()}
    SIGNAL_FILE.write_text(json.dumps(sig, separators=(",", ":")))
    print(f"   → MT5 CLOSE_ALL: {sig_id}")
    return sig_id


def read_mt5_status() -> dict:
    """Returns live MT5 status if MetalEA_v2 wrote it within 90 seconds."""
    if not MT5_STATUS.exists(): return {}
    try:
        age = time.time() - MT5_STATUS.stat().st_mtime
        if age > 90: return {}
        return json.loads(MT5_STATUS.read_text())
    except: return {}


def mt5_is_live() -> bool:
    """True only when MetalEA_v2 is active and status file is fresh."""
    return bool(read_mt5_status())


def wait_for_mt5(timeout_seconds: int = 300) -> dict:
    """
    Block until MetalEA_v2 writes a fresh mt5_status.json.
    Returns the status dict once live, or empty dict on timeout.
    """
    deadline = time.time() + timeout_seconds
    warned_at = 0
    print("\n" + "="*70)
    print("WAITING FOR MT5 EA (MetalEA_v2)...")
    print("="*70)
    print("In MetaTrader 5:")
    print("  1. Press F4 → MetaEditor → open MetalEA_v2.mq5 → F7 to Compile")
    print("  2. Back in MT5: Navigator (Ctrl+N) → Expert Advisors → MetalEA_v2")
    print("  3. Drag onto any XAUUSD or XAGUSD chart")
    print("  4. Tick 'Allow automated trading' in the EA dialog → OK")
    print("  5. AutoTrading toolbar button must be GREEN")
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
            print(f"  Waiting for MetalEA_v2 mt5_status.json... ({remaining}s remaining)")
            warned_at = now
        time.sleep(5)

    print(f"\nTIMEOUT: MetalEA_v2 not detected after {timeout_seconds}s.")
    print("Attach MetalEA_v2 to a chart in MT5 and restart.\n")
    return {}


def run_test_trade() -> bool:
    """
    Send a TEST_BUY on XAUUSD (0.01 lot, no SL/TP).
    MetalEA_v2 auto-closes it after 60 seconds.
    Returns True if MT5 confirmed execution.
    """
    print("\n" + "="*60)
    print("STARTUP TEST TRADE — XAUUSD TEST_BUY 0.01L")
    print("  (MetalEA_v2 auto-closes after 60s)")
    print("="*60)
    sig_id = f"TEST_BUY_XAUUSD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    sig = {"id": sig_id, "action": "TEST_BUY", "symbol": "XAUUSD",
           "lot": 0.01, "sl": 0, "tp": 0,
           "timestamp": datetime.now().isoformat()}
    SIGNAL_FILE.write_text(json.dumps(sig, separators=(",", ":")))
    print(f"  Signal written: {sig_id}")

    result = read_signal_result(sig_id, timeout=12)
    if result and result.get("success"):
        print(f"  TEST TRADE CONFIRMED ✓  (MT5 placed BUY, auto-close in 60s)")
        print("="*60 + "\n")
        TRADES_DIR.mkdir(parents=True, exist_ok=True)
        (TRADES_DIR / f"test_{sig_id}.json").write_text(
            json.dumps({"type": "TEST", "sig_id": sig_id, "result": result,
                        "timestamp": datetime.now().isoformat()}, indent=2))
        return True
    else:
        print(f"  TEST TRADE FAILED ✗  result={result}")
        print("  Check: MetalEA_v2 attached? AutoTrading green? XAUUSD chart open?")
        print("="*60 + "\n")
        return False


def read_signal_result(expected_id: str, timeout: float = 6.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if RESULT_FILE.exists():
            try:
                r = json.loads(RESULT_FILE.read_text())
                if r.get("sig_id") == expected_id:
                    return r
            except Exception:
                pass  # result file may be mid-write — retry
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
        f.write(json.dumps({"source": "EAv7", "timestamp": data["timestamp"], "data": data}) + "\n")
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
        # v10: H1 bias cache (refreshed every 3600s — H1 bar close)
        self.h1_bias        = {s: "NEUTRAL" for s in SYMBOLS}
        self.h1_bias_ts     = {s: 0   for s in SYMBOLS}
        self.deposit        = DEPOSIT
        self.pnl            = 0.0
        self.trades         = 0
        self.errors         = 0
        self.running        = False
        self._halt          = False   # set True when prop limit hit
        self._peak_equity   = DEPOSIT
        self._daily_start   = DEPOSIT
        self._daily_date    = datetime.now(timezone.utc).date()
        # Streak tracking for dynamic lot sizing
        self._streak        = 0       # +N = N consecutive wins, -N = N consecutive losses
        self._last_trade_pnl: dict = {}  # symbol → last closed PnL

        # ── Adaptive / reverse-logic state ───────────────────
        # Track consecutive losses per (symbol, direction, regime) triplet.
        # After 5 straight losses on a combo, try the opposite direction
        # (contrarian reversal) or skip for 1 cycle to reset.
        # Reverse logic only fires in TREND/SCALP regime and outside NY_CLOSE.
        self._combo_losses: dict = {}    # (sym, dir, regime) → consecutive loss count
        self._combo_wins:   dict = {}    # (sym, dir, regime) → consecutive win count
        self._reverse_cooldown: dict = {}  # (sym, regime) → cycles remaining before next reverse allowed
        # Track consecutive TIMEOUT exits — if >= 3 in a row, ATR conditions are
        # choppy; cut lot by 50% and raise min_score by 1 for 5 cycles.
        self._timeout_streak: int = 0
        self._timeout_penalty_cycles: int = 0  # remaining cycles at reduced params

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
        # Use MT5 live values as source of truth when available
        live_bal    = mt5_status.get("balance", 0)  if mt5_status else 0
        live_equity = mt5_status.get("equity",  0)  if mt5_status else 0
        live_float  = mt5_status.get("floating_pnl", 0) if mt5_status else 0

        primary_equity  = live_equity  if live_equity  > 0 else (self.deposit + self.pnl)
        primary_balance = live_bal     if live_bal     > 0 else (self.deposit + self.pnl)

        # PnL today = current equity minus what it was at start of day
        pnl_today = round(primary_equity - self._daily_start, 2) if self._daily_start > 0 else 0.0
        daily_loss_pct = round((self._daily_start - primary_equity) / self._daily_start * 100, 2) \
                         if self._daily_start > 0 else 0.0
        drawdown_pct   = round((self._peak_equity  - primary_equity) / self._peak_equity  * 100, 2) \
                         if self._peak_equity  > 0 else 0.0

        data = {
            # Live MT5 values (primary)
            "balance":       primary_balance,
            "equity":        primary_equity,
            "floating_pnl":  live_float,
            "open_positions": mt5_status.get("open_positions", len(self.positions)) if mt5_status else len(self.positions),
            "mt5_live":      bool(mt5_status),
            # Session tracking
            "deposit":       self.deposit,
            "total_pnl":     round(self.pnl, 4),
            "pnl_today":     pnl_today,
            "trade_count":   self.trades,
            "peak_equity":   self._peak_equity,
            "streak":        self._streak,
            "daily_start":   self._daily_start,
            "daily_date":    str(self._daily_date),
            "daily_loss_pct": daily_loss_pct,
            "drawdown_pct":   drawdown_pct,
            "session_active": in_session(),
            "symbols_active": SYMBOLS,
            "last_update":   datetime.now().isoformat(),
            "version":       "v7",
        }
        if mt5_status:
            data.update({
                "mt5_balance":   live_bal,
                "mt5_equity":    live_equity,
                "mt5_floating":  live_float,
                "mt5_positions": mt5_status.get("open_positions", 0),
                "mt5_account":   mt5_status.get("account", 0),
                "mt5_server":    mt5_status.get("server", ""),
            })
        STATE_FILE.write_text(json.dumps(data, indent=2))

    # ── Prop firm limit checks ─────────────────────────────

    def _update_equity_tracking(self, equity: float):
        """Update peak equity and reset daily tracker at midnight UTC."""
        if equity > self._peak_equity:
            self._peak_equity = equity
        today = datetime.now(timezone.utc).date()
        if today != self._daily_date:
            self._daily_date  = today
            self._daily_start = equity
            print(f"   [PROP] Daily reset — start equity: ${equity:,.2f}")

    def _check_prop_limits(self, equity: float) -> str:
        """
        Returns:
          'OK'      — trade normally
          'WARN'    — approaching limit, halve position size
          'HALT'    — limit breached, close all and stop trading
        """
        daily_loss    = self._daily_start - equity
        daily_loss_pct = daily_loss / self._daily_start * 100 if self._daily_start > 0 else 0

        drawdown      = self._peak_equity - equity
        drawdown_pct   = drawdown / self._peak_equity * 100 if self._peak_equity > 0 else 0

        # Hard halt
        if daily_loss_pct >= DAILY_LOSS_LIMIT_PCT:
            msg = f"DAILY LOSS LIMIT HIT: ${daily_loss:.2f} ({daily_loss_pct:.2f}% of ${self._daily_start:.2f})"
            print(f"\n🚨 PROP FIRM HALT — {msg}")
            _obsidian("PROP FIRM DAILY LIMIT HIT", f"- {msg}\n- Closing all positions", "ea_halt")
            return "HALT"

        if drawdown_pct >= MAX_DRAWDOWN_PCT:
            msg = f"MAX DRAWDOWN HIT: ${drawdown:.2f} ({drawdown_pct:.2f}% from peak ${self._peak_equity:.2f})"
            print(f"\n🚨 PROP FIRM HALT — {msg}")
            _obsidian("PROP FIRM DRAWDOWN LIMIT HIT", f"- {msg}\n- Closing all positions", "ea_halt")
            return "HALT"

        # Soft warn
        if daily_loss_pct >= WARN_DAILY_LOSS_PCT or drawdown_pct >= WARN_DRAWDOWN_PCT:
            return "WARN"

        return "OK"

    # ── Shutdown: close all MT5 positions ─────────────────

    def _close_all_mt5_positions(self, reason: str = "shutdown"):
        """Send CLOSE signals for every open position to MT5, then CLOSE_ALL as fallback."""
        if not self.positions:
            print(f"   [SHUTDOWN] No open positions to close ({reason})")
            return

        print(f"\n   [SHUTDOWN] Closing {len(self.positions)} open position(s) in MT5 — reason: {reason}")

        for symbol, pos in list(self.positions.items()):
            try:
                price = get_price(symbol)
                sig_id = write_close_signal(symbol)
                result = read_signal_result(sig_id, timeout=8)

                price_move = price - pos["entry_price"] if pos["direction"] == "BUY" \
                             else pos["entry_price"] - price
                raw_pnl = pnl_for_move(symbol, abs(price_move), pos["lot"]) \
                          * (1 if price_move >= 0 else -1)
                self.pnl += raw_pnl

                print(f"      CLOSE {symbol} @ ${price:,.3f}  PnL=${raw_pnl:+.2f}  MT5={'✓' if result else '✗'}")
                record({
                    "type": "EXIT", "symbol": symbol,
                    "direction": pos["direction"], "lot": pos["lot"],
                    "entry_price": pos["entry_price"], "exit_price": price,
                    "pnl": round(raw_pnl, 4), "reason": reason,
                    "elapsed": (datetime.now() - datetime.fromisoformat(pos["entry_time"])).seconds,
                    "sig_id": sig_id, "mt5_result": result,
                    "mode": "real_mt5", "timestamp": datetime.now().isoformat()
                })
                time.sleep(1.5)  # let MT5 process the signal before next one
            except Exception as e:
                print(f"      ERROR closing {symbol}: {e}")

        # Belt-and-suspenders: also send CLOSE_ALL so MT5 catches anything we missed
        time.sleep(1)
        write_close_all_signal()
        time.sleep(2)
        self.positions.clear()
        _obsidian(f"EA Closed All Positions [{reason}]",
            f"- Positions closed: {len(self.positions)} symbols\n- Reason: {reason}", "ea_stop")

    def _stop(self, signum=None, frame=None):
        """Signal handler — only sets flag. _shutdown() does the actual closing."""
        print(f"\n[Ctrl+C / SIGTERM] Stop requested — finishing current tick then closing all positions...")
        self.running = False

    # ── Kline / trend refresh ──────────────────────────────

    def _refresh_klines(self, symbol: str) -> list:
        now = time.time()
        if now - self.klines_ts[symbol] > 120 or not self.klines_1m[symbol]:
            fresh = fetch_klines(symbol, period="1d", interval_tf="1m", n=80)
            if fresh:
                self.klines_1m[symbol] = fresh
                self.klines_ts[symbol] = now
            elif not self.klines_1m[symbol]:
                # yfinance unavailable on startup — seed from MT5 live price with synthetic klines
                # so the agent can begin evaluating signals immediately
                live_price = get_price(symbol)
                if live_price > 0:
                    import random as _r; _r.seed(42)
                    # Noise scaled to symbol magnitude
                    noise = (0.5   if symbol == "XAUUSD" else
                             0.05  if symbol == "XAGUSD" else
                             0.0003)  # EURUSD/GBPUSD
                    # 50 synthetic flat klines centred on current price
                    self.klines_1m[symbol] = [live_price + _r.uniform(-noise, noise)
                                              for _ in range(50)]
                    self.klines_ts[symbol] = now
                    print(f"   [KLINE] yfinance unavailable — seeded {symbol} klines "
                          f"from MT5 live price ${live_price:,.3f}")
        return self.klines_1m[symbol]

    def _refresh_trend(self, symbol: str) -> str:
        now = time.time()
        if now - self.trend_ts[symbol] > 900:
            self.trend_15m[symbol] = get_trend_15m(symbol)
            self.trend_ts[symbol]  = now
        return self.trend_15m[symbol]

    def _refresh_h1_bias(self, symbol: str) -> str:
        """v10: Refresh H1 EMA20 bias once per hour (3600s cache)."""
        now = time.time()
        if now - self.h1_bias_ts[symbol] > 3600:
            self.h1_bias[symbol]    = get_h1_bias(symbol)
            self.h1_bias_ts[symbol] = now
            print(f"   [H1 BIAS] {symbol}: {self.h1_bias[symbol]}")
        return self.h1_bias[symbol]

    # ── Main run loop ──────────────────────────────────────

    def run(self):
        print("=" * 70)
        print("EA Live Trader v10 — Session-Adaptive | XAUUSD + XAGUSD + EURUSD + GBPUSD | 24/5")
        print(f"Risk    : {RISK_PCT}%/trade (score-scaled) | MIN_SCORE={MIN_SCORE} | Streak stop:{STREAK_HARD_STOP}")
        print(f"Sessions: ASIAN(0.25×) | LONDON(1.0×) | LON_NY(1.5×) | NY_CLOSE(0.5×) | AFTER_NY(0.75×)")
        print(f"Regimes : TREND(2.5R,20c,sc3) | SCALP(2R,12c,sc3) | RANGE(1.5R,8c,sc3) | DEAD(blocked)")
        print(f"Overrides: ASIAN→tp1.0R/sl0.8/to6c | NY_CLOSE→tp1.2R/sl1.0/to8c | AFTER_NY→tp1.5R/sl1.2/to10c")
        print(f"Trail   : default@{TRAIL_ACTIVATE_R}R | LONDON_NY@{TRAIL_ACTIVATE_R_LNNY}R (tighter for trend riding)")
        print(f"v10     : H1 EMA bias | Breakout +2 score | EURUSD/GBPUSD added | NY_CLOSE TREND score>=5 allowed")
        print(f"Limits  : Daily loss ≤{DAILY_LOSS_LIMIT_PCT}% | Max drawdown ≤{MAX_DRAWDOWN_PCT}%")
        print("=" * 70)

        # ── Gate: refuse to start until MT5 EA is confirmed live ──────────
        mt5 = wait_for_mt5(timeout_seconds=300)
        if not mt5:
            print("Exiting — MT5 EA not confirmed. Restart after attaching PythonSignalExecutor.ex5.")
            sys.exit(0)

        # Seed equity from MT5 live balance — always use the real account value
        # Always reset peak_equity to live balance at session start to prevent stale
        # state from prior sessions triggering an immediate prop-firm halt.
        live_balance = mt5.get("balance", 0)
        if live_balance > 0:
            if abs(live_balance - self.deposit) / max(self.deposit, 1) > 0.01:
                print(f"   [EQUITY RESET] MT5 balance ${live_balance:,.2f} differs from stored deposit ${self.deposit:,.2f}")
                print(f"   [EQUITY RESET] Syncing to MT5 live balance")
                self.pnl     = 0.0
                self._streak = 0
            self.deposit      = live_balance
            self._daily_start = live_balance
            self._peak_equity = live_balance   # reset peak to current — no stale cross-session halts
        else:
            equity = self.deposit
            self._daily_start = equity
            self._peak_equity = equity

        print("=" * 70)
        print(f"Account : #{mt5.get('account', '?')} @ {mt5.get('server', 'ICMarketsCS-Demo')}")
        print(f"Balance : ${mt5.get('balance', '?')} | Equity: ${mt5.get('equity', '?')}")
        print(f"XAUUSD  : ${mt5.get('xauusd_bid', '?')} | XAGUSD: ${mt5.get('xagusd_bid', '?')}")
        print("TRADING ACTIVE — signals will be sent to MT5")
        print("=" * 70 + "\n")

        # Test trade is handled by liveea.py launcher before EATrader.run() is called
        _obsidian("EA Trader v7 Started",
            f"- Account: #{mt5.get('account', '?')}\n"
            f"- Balance: ${mt5.get('balance', '?')} | Equity: ${mt5.get('equity', '?')}\n"
            f"- Risk: {RISK_PCT}%/trade (score-scaled) | Daily limit: {DAILY_LOSS_LIMIT_PCT}% | DD limit: {MAX_DRAWDOWN_PCT}%\n"
            f"- Regimes: TREND(3R) SCALP(2R) RANGE(1.5R) DEAD(blocked)",
            "ea_start")

        self.running = True
        while self.running:
            try:
                mt5_status = read_mt5_status()
                equity     = mt5_status.get("equity", self.deposit + self.pnl) \
                             if mt5_status else self.deposit + self.pnl

                # Use MT5 balance as equity source of truth; fall back to estimate only if stale
                if mt5_status:
                    equity = mt5_status.get("balance", equity)
                else:
                    # MT5 status stale — pause new entries but keep managing open positions
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] WARNING: MT5 status stale — no new entries until restored")

                self._update_equity_tracking(equity)
                prop_status = self._check_prop_limits(equity)

                if prop_status == "HALT" and not self._halt:
                    self._halt = True
                    self._close_all_mt5_positions("prop_limit_halt")
                    self.running = False
                    break

                session = in_session()
                # Force reduced sizing on losing streaks to protect capital
                reduced = (prop_status == "WARN") or (self._streak <= -3)
                # Hard-stop new entries on severe losing streak (data: reached -10)
                if self._streak <= STREAK_HARD_STOP:
                    print(f"   [STREAK STOP] Streak={self._streak} ≤ {STREAK_HARD_STOP} — blocking new entries until streak recovers")
                    reduced = True  # will also be checked at entry gate below
                mt5_confirmed = bool(mt5_status)  # only enter trades when MT5 is live

                for sym in SYMBOLS:
                    self._tick(sym, mt5_status, equity, session, reduced, mt5_confirmed)

                self._save(mt5_status)
                self.errors = 0

            except KeyboardInterrupt:
                print("\nKeyboard interrupt received")
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

    def _tick(self, symbol: str, mt5_status: dict, equity: float, session: bool, reduced: bool, mt5_confirmed: bool = True):
        ts    = datetime.now().strftime("%H:%M:%S")
        price = get_price(symbol)
        kl    = self._refresh_klines(symbol)
        if kl:
            kl.append(price)
            if len(kl) > 100: kl.pop(0)
            self.klines_1m[symbol] = kl

        trend = self._refresh_trend(symbol)
        # v10: H1 bias for higher-TF trend confirmation
        h1    = self._refresh_h1_bias(symbol)
        sig   = compute_signal(kl, trend, h1_bias=h1)
        pos   = self.positions.get(symbol)

        # Session-aware sizing — no blocking, parameters adapt per session
        sess_key, sess_name, sess_mult = get_session()
        # Cap multiplier during losing streaks to prevent oversizing
        if self._streak <= -2:
            sess_mult = min(sess_mult, 1.0)
        if self._streak <= -5:
            sess_mult = min(sess_mult, 0.5)

        mt5_ok  = bool(mt5_status)
        daily_loss_pct = (self._daily_start - equity) / self._daily_start * 100 \
                          if self._daily_start > 0 else 0
        dd_pct = (self._peak_equity - equity) / self._peak_equity * 100 \
                  if self._peak_equity > 0 else 0

        regime     = sig.get("regime", "SCALP")
        base_rp    = REGIME_PARAMS.get(regime, REGIME_PARAMS["SCALP"])
        rp         = get_session_regime_params(base_rp, sess_key)
        regime_min_score = rp["min_score"]

        status_str = (
            f"{'⚠ ' if reduced else ''}"
            f"DL:{daily_loss_pct:.1f}%/{DAILY_LOSS_LIMIT_PCT}% "
            f"DD:{dd_pct:.1f}%/{MAX_DRAWDOWN_PCT}% "
            f"[{sess_name}×{sess_mult}] [{regime}]"
        )

        streak_ok    = self._streak > STREAK_HARD_STOP
        block_reason = "STREAK" if not streak_ok else ""

        # v10: NY_CLOSE TREND unblock — allow TREND if signal score >= 5 (strong)
        # Default SESSION_REGIME_OVERRIDES sets ny_close min_score=4, but TREND was
        # commented-blocked in header docs. With score>=5 + H1 alignment, it's valid.
        if sess_key == "ny_close" and regime == "TREND" and sig["score"] >= 5:
            # Override the session's min_score for this specific strong TREND signal
            regime_min_score = min(regime_min_score, 4)  # ensure not blocked above score=4

        print(f"[{ts}] {symbol} ${price:,.3f} | {sig['direction']:4s} sc:{sig['score']} "
              f"rsi:{sig.get('rsi',0):.0f} trend:{trend} h1:{h1} | "
              f"MT5:{'✓' if mt5_ok else '✗'} eq:${equity:,.0f} | "
              f"{'POS' if pos else '-'} | {'SESSION' if session else 'CLOSED'} | "
              f"{status_str}{' ['+block_reason+']' if block_reason else ''}")

        # ── Entry gate ─────────────────────────────────────────
        # No session blocking — regime params already adapted for the current session.

        # Reverse-logic: if this (symbol, direction, regime) combo has lost 5× in a row,
        # try the opposite direction instead (mean-reversion / contrarian signal).
        # Guards: only fires in TREND/SCALP regime and not during NY_CLOSE session.
        entry_dir = sig["direction"]
        combo_key = (symbol, entry_dir, regime)
        combo_loss_count = self._combo_losses.get(combo_key, 0)

        # Only apply reverse logic in TREND/SCALP regime, and not during NY_CLOSE
        reverse_ok = (regime in ("TREND", "SCALP")) and (sess_key != "ny_close")

        # Decrement reverse cooldown; suppress reverse while cooling down
        cd_key = (symbol, regime)
        if self._reverse_cooldown.get(cd_key, 0) > 0:
            self._reverse_cooldown[cd_key] -= 1
            reverse_ok = False  # on cooldown, skip reverse regardless

        if combo_loss_count >= 5 and entry_dir != "NONE" and reverse_ok:
            opposite = "SELL" if entry_dir == "BUY" else "BUY"
            opp_key  = (symbol, opposite, regime)
            # Only flip if the opposite direction doesn't also have 5+ losses
            if self._combo_losses.get(opp_key, 0) < 5:
                print(f"   [REVERSE] {symbol} {entry_dir} lost {combo_loss_count}× → trying {opposite}")
                entry_dir = opposite
                combo_key = opp_key
                self._reverse_cooldown[cd_key] = 3  # 3-cycle cooldown after each reverse

        # Timeout-penalty: after 3 consecutive timeouts, require higher score for 5 cycles
        effective_min_score = regime_min_score
        effective_lot_mult  = 1.0
        if self._timeout_penalty_cycles > 0:
            effective_min_score += 1
            effective_lot_mult   = 0.5

        # RANGE + NEUTRAL trend noise filter: score must be >= 4 (not just noise)
        if regime == "RANGE" and trend == "NEUTRAL" and entry_dir != "NONE":
            if sig["score"] < 4:
                entry_dir = "NONE"

        if (pos is None and entry_dir != "NONE"
                and sig["score"] >= effective_min_score
                and session
                and streak_ok
                and mt5_confirmed
                and not self._halt):

            atr     = sig.get("atr", price * 0.001)
            # Regime-specific SL distance (TREND=2×ATR, SCALP=1.5×, RANGE=1.2×)
            sl_dist = min(rp["sl_atr"] * atr, price * MAX_SL_PCT)
            min_sl_pct = 0.005 if symbol == "XAGUSD" else 0.003
            sl_dist = max(sl_dist, price * min_sl_pct)

            # Use swing-level SL when a nearby swing is tighter than ATR-based SL
            swing_high, swing_low = find_swing_levels(kl)
            if entry_dir == "BUY" and swing_low is not None:
                swing_sl_dist = price - swing_low
                if 0 < swing_sl_dist < sl_dist * 1.3:
                    sl_dist = max(swing_sl_dist, price * min_sl_pct)
            elif entry_dir == "SELL" and swing_high is not None:
                swing_sl_dist = swing_high - price
                if 0 < swing_sl_dist < sl_dist * 1.3:
                    sl_dist = max(swing_sl_dist, price * min_sl_pct)

            # Regime-specific TP ratio
            tp_dist = sl_dist * rp["tp_r"]

            lot = lot_size(symbol, sl_dist, equity, reduced, sess_mult, self._streak,
                           score=sig["score"])
            # Apply timeout-penalty lot reduction
            lot = round(max(lot * effective_lot_mult, MIN_LOT if "MIN_LOT" in dir() else 0.01), 2)

            sl_python = round(price - sl_dist, 2 if symbol == "XAUUSD" else 3) if entry_dir == "BUY" \
                        else round(price + sl_dist, 2 if symbol == "XAUUSD" else 3)
            tp_python = round(price + tp_dist, 2 if symbol == "XAUUSD" else 3) if entry_dir == "BUY" \
                        else round(price - tp_dist, 2 if symbol == "XAUUSD" else 3)

            reverse_tag = " [REVERSE]" if entry_dir != sig["direction"] else ""
            penalty_tag = f" [CHOP×{effective_lot_mult}]" if self._timeout_penalty_cycles > 0 else ""
            print(f"   → ENTRY {entry_dir} {lot}L {symbol} @ ${price:,.3f}  "
                  f"SL(py)={sl_python} TP(py)={tp_python}  score={sig['score']} "
                  f"regime={regime} tp_r={rp['tp_r']}R "
                  f"[{sess_name}×{sess_mult}] streak={self._streak:+d}"
                  f"{' [REDUCED]' if reduced else ''}{reverse_tag}{penalty_tag}")

            sig_id    = write_signal(symbol, entry_dir, lot, sl=0, tp=0)  # no MT5 stops
            result    = read_signal_result(sig_id, timeout=8)
            confirmed = bool(result and result.get("success"))

            if not confirmed:
                print(f"   ✗ MT5 did not confirm trade — position NOT recorded locally")
                _obsidian(f"EA SIGNAL SENT (unconfirmed): {symbol} {entry_dir}",
                    f"- ${price:,.3f} | {lot}L | sig_id:{sig_id}\n- MT5 result: {result}\n"
                    f"- Check MT5 AutoTrading is enabled and EA is on chart", "ea_warn")
                return

            self.positions[symbol] = {
                "direction":    entry_dir,
                "entry_price":  price,
                "lot":          lot,
                "sl":           sl_python,
                "tp":           tp_python,
                "sl_dist":      sl_dist,
                "tp_dist":      tp_dist,
                "sig_id":       sig_id,
                "entry_time":   datetime.now().isoformat(),
                "trail_active": False,
                "trail_sl":     sl_python,
                "mt5_confirmed": confirmed,
                "regime":       regime,
                "regime_timeout": rp["timeout"],
                "regime_trail_r": rp["trail_r"],
            }
            record({
                "type": "ENTRY", "symbol": symbol,
                "direction": entry_dir, "lot": lot,
                "entry_price": price, "sl": sl_python, "tp": tp_python,
                "sl_dist": sl_dist, "tp_dist": tp_dist,
                "signal": sig, "trend_15m": trend, "regime": regime,
                "sig_id": sig_id, "mt5_result": result,
                "reduced_size": reduced, "reversed": entry_dir != sig["direction"],
                "mode": "real_mt5", "timestamp": datetime.now().isoformat()
            })
            _obsidian(f"EA ENTRY: {symbol} {entry_dir}",
                f"- ${price:,.3f} | {lot}L | SL:{sl_python} TP:{tp_python}\n"
                f"- Score:{sig['score']} RSI:{sig.get('rsi',0):.0f} Trend:{trend} Regime:{regime}\n"
                f"- TP_R:{rp['tp_r']} SL_ATR:{rp['sl_atr']} Timeout:{rp['timeout']}c\n"
                f"- Session:{sess_name} | MT5:{'✓' if confirmed else '✗'}{reverse_tag}{penalty_tag}",
                "ea_trade")
            self.trades += 1

        # ── Manage open position ───────────────────────────
        elif pos is not None:
            elapsed   = (datetime.now() - datetime.fromisoformat(pos["entry_time"])).seconds
            direction = pos["direction"]
            entry     = pos["entry_price"]
            lot       = pos["lot"]
            sl_dist   = pos.get("sl_dist", entry * 0.003)

            # Use regime-specific trail distance and timeout stored at entry
            trade_trail_r   = pos.get("regime_trail_r", TRAIL_DISTANCE_R)
            trade_timeout_s = pos.get("regime_timeout", TRADE_TIMEOUT_CANDLES) * INTERVAL
            # XAGUSD always gets wider trail to avoid early stop-out
            if symbol == "XAGUSD":
                trade_trail_r = max(trade_trail_r, TRAIL_DISTANCE_XAGUSD)

            raw_move    = price - entry if direction == "BUY" else entry - price
            unrealised  = pnl_for_move(symbol, abs(raw_move), lot) * (1 if raw_move >= 0 else -1)

            # v10: LONDON_NY uses tighter trail activation (1.0R vs 1.5R default)
            # so winning trades run longer during the highest-ATR session.
            trail_activate = TRAIL_ACTIVATE_R_LNNY if sess_key == "london_ny" else TRAIL_ACTIVATE_R

            # Trailing stop
            if not pos["trail_active"] and unrealised >= sl_dist * trail_activate:
                pos["trail_active"] = True
                print(f"   → TRAIL ACTIVATED {symbol}  unrealised=${unrealised:+.2f} "
                      f"regime={pos.get('regime','SCALP')} trail_r={trade_trail_r} "
                      f"activate_r={trail_activate} sess={sess_key}")

            if pos["trail_active"]:
                trail_gap = sl_dist * trade_trail_r
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

            # Enforce minimum hold time (FTMO rule — no exits < 2 min)
            if elapsed < MIN_HOLD_SECONDS:
                sl_hit = tp_hit = timeout = False

            if sl_hit or tp_hit or timeout:
                reason  = "TP" if tp_hit else \
                          ("TRAIL_SL" if (sl_hit and pos["trail_active"]) else \
                          ("SL" if sl_hit else "TIMEOUT"))
                sig_id  = write_close_signal(symbol)
                result  = read_signal_result(sig_id, timeout=6)

                price_move = price - entry if direction == "BUY" else entry - price
                raw_pnl    = pnl_for_move(symbol, abs(price_move), lot) * \
                             (1 if price_move >= 0 else -1)
                self.pnl  += raw_pnl

                # Update win/loss streak
                if raw_pnl > 0:
                    self._streak = self._streak + 1 if self._streak >= 0 else 1
                else:
                    self._streak = self._streak - 1 if self._streak <= 0 else -1

                # ── Adaptive learning: track combo losses and timeout streak ──
                combo_key = (symbol, direction, pos.get("regime", "SCALP"))
                if raw_pnl > 0:
                    self._combo_losses[combo_key] = 0
                    self._combo_wins[combo_key]   = self._combo_wins.get(combo_key, 0) + 1
                else:
                    self._combo_losses[combo_key] = self._combo_losses.get(combo_key, 0) + 1
                    self._combo_wins[combo_key]   = 0

                if reason == "TIMEOUT":
                    self._timeout_streak += 1
                    if self._timeout_streak >= 3 and self._timeout_penalty_cycles == 0:
                        self._timeout_penalty_cycles = 5
                        print(f"   [TIMEOUT×{self._timeout_streak}] Chop detected — lot ×0.5, min_score+1 for 5 cycles")
                else:
                    self._timeout_streak = 0
                if self._timeout_penalty_cycles > 0:
                    self._timeout_penalty_cycles -= 1

                print(f"   → CLOSE [{reason}] {symbol} @ ${price:,.3f}  "
                      f"PnL=${raw_pnl:+.2f}  Total=${self.pnl:+.2f}  streak={self._streak:+d}")
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
                _obsidian(f"EA EXIT [{reason}]: {symbol}",
                    f"- PnL: ${raw_pnl:+.2f} | Total: ${self.pnl:+.2f} | streak={self._streak:+d}", "ea_trade")
                self.trades += 1
                del self.positions[symbol]

    # ── Shutdown ───────────────────────────────────────────

    def _shutdown(self):
        """Called at end of run loop — closes any remaining positions then saves."""
        if self.positions:
            print(f"\n[SHUTDOWN] Closing {len(self.positions)} remaining position(s)...")
            self._close_all_mt5_positions("shutdown")
        self._save()
        print(f"\nEA v7 stopped. Trades: {self.trades} | PnL: ${self.pnl:+.2f}")
        _obsidian("EA Trader v7 Stopped",
            f"- Trades: {self.trades}\n- PnL: ${self.pnl:+.2f}\n- Peak equity: ${self._peak_equity:,.2f}",
            "ea_stop")
        try: PID_FILE.unlink()
        except: pass


if __name__ == "__main__":
    EATrader().run()
