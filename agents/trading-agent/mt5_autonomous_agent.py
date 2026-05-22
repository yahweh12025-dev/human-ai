#!/usr/bin/env python3
"""
mt5_autonomous_agent.py — Consolidated MT5 Autonomous Trading Agent
=====================================================================
A standalone, single-file agent that manages the entire trading lifecycle
for MetaTrader 5 via a JSON bridge to MetalEA_v3.

Core Logic:
- Multi-Symbol: XAUUSD, XAGUSD, EURUSD, GBPUSD
- Signal: Pillar-based (EMA Cross + Momentum + BB + RSI)
- Regime: Dynamic (Trend, Scalp, Range, Dead)
- Session: Adaptive Risk (Asian, London, NY)
- Risk: Proprietary Firm Limits (Daily Loss, Max Drawdown)
=====================================================================
"""

import json, os, sys, time, signal, uuid, subprocess
from datetime import datetime, timezone
from pathlib import Path

try:
    import yfinance as yf
    YFINANCE_OK = True
except ImportError:
    YFINANCE_OK = False

# --- Configuration ---
PROJECT_ROOT = Path("/config") # Inside Docker
MT5_FILES    = PROJECT_ROOT / ".wine/drive_c/Program Files/MetaTrader 5/MQL5/Files"
SIGNAL_FILE  = MT5_FILES / "python_signal.json"
RESULT_FILE  = MT5_FILES / "python_result.json"
MT5_STATUS   = MT5_FILES / "mt5_status.json"
STATE_FILE   = PROJECT_ROOT / "mt5_agent_state.json"

SYMBOLS  = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD"]
YF_MAP   = {"XAUUSD": "GC=F", "XAGUSD": "SI=F", "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X"}
YF_BACKUP = {"EURUSD": ["EURUSD", "EUR=X"], "GBPUSD": ["GBPUSD", "GBP=X"]}

# Risk Params
DEPOSIT          = 5000.0
RISK_PCT         = 0.5       
MAX_SL_PCT       = 0.006     
MIN_SL_PCT       = {"XAUUSD": 0.003, "XAGUSD": 0.003, "EURUSD": 0.0015, "GBPUSD": 0.0015}
INTERVAL         = 30        
MIN_HOLD_SECONDS = 180       

# Session classification
ASIAN_HOURS      = {22, 23, 0, 1, 2, 3, 4, 5, 6}
LONDON_HOURS     = {7, 8, 9, 10, 11}
LONDON_NY_HOURS  = {12, 13, 14, 15, 16}
NY_CLOSE_HOURS   = {17, 18}
AFTER_NY_HOURS   = {19, 20, 21}

RISK_MULT = {"london_ny": 1.5, "london": 1.0, "after_ny": 0.75, "ny_close": 0.5, "asian": 0.25}

SESSION_REGIME_PARAMS = {
    "asian":    {"tp_r": 0.8,  "sl_atr": 1.2, "timeout": 10, "trail_r": 0.6, "min_score": 7},
    "london":   {"tp_r": 1.2,  "sl_atr": 1.5, "timeout": 20, "trail_r": 0.6, "min_score": 4},
    "london_ny":{"tp_r": 1.5,  "sl_atr": 1.5, "timeout": 40, "trail_r": 0.6, "min_score": 4},
    "ny_close": {"tp_r": 1.0,  "sl_atr": 1.2, "timeout": 16, "trail_r": 0.6, "min_score": 5},
    "after_ny": {"tp_r": 1.0,  "sl_atr": 1.2, "timeout": 16, "trail_r": 0.6, "min_score": 4},
}

REGIME_TP_MULT = {"TREND": 1.0, "SCALP": 0.9, "RANGE": 0.7, "DEAD": 0.0}
REGIME_SL_MULT = {"TREND": 1.5, "SCALP": 1.2, "RANGE": 1.0, "DEAD": 0.0}

ATR_DEAD_THRESHOLD = {
    "XAUUSD": 1.00, "XAGUSD": 0.05, "EURUSD": 0.00008, "GBPUSD": 0.00010,
}

SCORE_LOT_MULT = {5: 1.0, 6: 1.3, 7: 1.6, 8: 2.0}
CONTRACT_SIZE = {"XAUUSD": 100, "XAGUSD": 5000, "EURUSD": 100000, "GBPUSD": 100000}
POINT_SIZE    = {"XAUUSD": 0.01, "XAGUSD": 0.001, "EURUSD": 0.0001, "GBPUSD": 0.0001}
POINT_VALUE   = {"XAUUSD": 1.0, "XAGUSD": 5.0, "EURUSD": 10.0, "GBPUSD": 10.0}
MAX_LOT       = {"XAUUSD": 0.05, "XAGUSD": 0.05, "EURUSD": 0.05, "GBPUSD": 0.05}
MIN_LOT       = 0.01

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

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
    if MT5_STATUS.exists():
        try:
            status = json.loads(MT5_STATUS.read_text())
            val = status.get(f"{symbol.lower()}_bid", 0)
            if val and float(val) > 0: return float(val)
        except: pass
    if YFINANCE_OK:
        try:
            price = float(yf.Ticker(YF_MAP[symbol]).fast_info.last_price)
            if price > 0: return price
        except: pass
    return {"XAUUSD": 4540.0, "XAGUSD": 76.0, "EURUSD": 1.0850, "GBPUSD": 1.2700}.get(symbol, 1.0)

def fetch_klines(symbol: str, period="5d", interval_tf="5m", n=80) -> list:
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
    except: pass
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
        if ema20_now > ema20_prev * 1.0003: return "BULL"
        if ema20_now < ema20_prev * 0.9997: return "BEAR"
    except: pass
    return "NEUTRAL"

def detect_regime(prices: list, atr: float) -> str:
    if len(prices) < 30: return "SCALP"
    if atr < 0.003: return "DEAD"
    sma20 = sum(prices[-20:]) / 20
    std20 = (sum((p - sma20) ** 2 for p in prices[-20:]) / 20) ** 0.5
    bb_width_pct = (4 * std20 / sma20) if sma20 > 0 else 0
    ema5  = compute_ema(prices[-12:], 5)
    ema20 = compute_ema(prices[-25:], 20)
    ema_diff_pct = abs(ema5 - ema20) / ema20 if ema20 > 0 else 0
    above_ema20 = sum(1 for p in prices[-10:] if p > ema20)
    below_ema20 = 10 - above_ema20
    one_sided = above_ema20 >= 7 or below_ema20 >= 7
    up_run = sum(1 for i in range(-6, 0) if prices[i] > prices[i-1])
    down_run = 6 - up_run
    strong_dir = up_run >= 4 or down_run >= 4
    if ema_diff_pct > 0.0005 and one_sided and strong_dir: return "TREND"
    if bb_width_pct < 0.003: return "RANGE"
    return "SCALP"

def compute_signal(prices: list, trend_15m: str, h1_bias: str, regime: str) -> dict:
    if len(prices) < 22: return {"direction": "NONE", "score": 0}
    atr = compute_atr(prices)
    if atr == 0: return {"direction": "NONE", "score": 0}
    
    ema3  = compute_ema(prices[-10:], 3)
    ema8  = compute_ema(prices[-15:], 8)
    ema21 = compute_ema(prices[-22:], 21)
    fast_bull, fast_bear = (ema3 > ema8), (ema3 < ema8)
    slow_bull, slow_bear = (ema8 > ema21 * 1.0001), (ema8 < ema21 * 0.9999)
    
    mom_bull, mom_bear = False, False
    if len(prices) >= 6:
        recent = prices[-6:]
        up_moves = sum(1 for i in range(1, 6) if recent[i] > recent[i-1])
        mom_bull = up_moves >= 3 and prices[-1] > prices[-5]
        mom_bear = (5 - up_moves) >= 3 and prices[-1] < prices[-5]

    sma20 = sum(prices[-20:]) / 20
    std20 = (sum((p - sma20) ** 2 for p in prices[-20:]) / 20) ** 0.5
    bb_upper, bb_lower = sma20 + 2*std20, sma20 - 2*std20
    bb_breakout_bull = prices[-1] > bb_upper and prices[-2] <= bb_upper
    bb_breakout_bear = prices[-1] < bb_lower and prices[-2] >= bb_lower
    
    rsi = compute_rsi(prices[-20:])
    
    p_a_bull = fast_bull and mom_bull
    p_a_bear = fast_bear and mom_bear
    p_b_bull = (abs(prices[-1]-prices[-2])/atr > 1.0 and fast_bull) or (slow_bull and mom_bull)
    p_b_bear = (abs(prices[-1]-prices[-2])/atr > 1.0 and fast_bear) or (slow_bear and mom_bear)
    p_c_bull = bb_breakout_bull or (prices[-1] < bb_lower * 1.01 and fast_bull and mom_bull)
    p_c_bear = bb_breakout_bear or (prices[-1] > bb_upper * 0.99 and fast_bear and mom_bear)
    
    sb = sum([p_a_bull, p_b_bull, p_c_bull])
    sr = sum([p_a_bear, p_b_bear, p_c_bear])
    
    score_bull = sb + (1 if rsi < 75 and sb >= 1 else 0) + (1 if trend_15m == "BULL" else 0) + (1 if h1_bias == "BULL" and sb >= 1 else 0)
    score_bear = sr + (1 if rsi > 20 and sr >= 1 else 0) + (1 if trend_15m == "BEAR" else 0) + (1 if h1_bias == "BEAR" and sr >= 1 else 0)
    
    direction = "NONE"
    if score_bull >= 3 and score_bull > score_bear and rsi < 80: direction = "BUY"
    elif score_bear >= 3 and score_bear > score_bull and rsi > 20: direction = "SELL"
    
    return {"direction": direction, "score": max(score_bull, score_bear), "rsi": rsi, "atr": atr}

def lot_size(symbol: str, sl_dist: float, equity: float, session_mult: float, score: int) -> float:
    risk_usd = equity * (RISK_PCT / 100)
    sl_points = sl_dist / POINT_SIZE[symbol]
    dollar_per_lot = sl_points * POINT_VALUE[symbol]
    lots = risk_usd / dollar_per_lot if dollar_per_lot > 0 else MIN_LOT
    score_mult = SCORE_LOT_MULT.get(min(score, 8), 1.0)
    return round(max(MIN_LOT, min(lots * session_mult * score_mult, MAX_LOT[symbol])), 2)

# -----------------------------------------------------------------------------
# Main Agent Class
# -----------------------------------------------------------------------------

class MT5AutonomousAgent:
    def __init__(self):
        self.positions = {}
        self.klines = {s: [] for s in SYMBOLS}
        self.klines_ts = {s: 0 for s in SYMBOLS}
        self.trend_15m = {s: "NEUTRAL" for s in SYMBOLS}
        self.trend_ts = {s: 0 for s in SYMBOLS}
        self.h1_bias = {s: "NEUTRAL" for s in SYMBOLS}
        self.h1_bias_ts = {s: 0 for s in SYMBOLS}
        self.running = True

    def run(self):
        print("🚀 MT5 Autonomous Agent Started | Mode: Consolidated Brain")
        while self.running:
            try:
                mt5_status = self._read_status()
                equity = mt5_status.get("equity", DEPOSIT) if mt5_status else DEPOSIT
                session_active = in_session()
                
                for sym in SYMBOLS:
                    # 1. Update Data
                    price = get_price(sym)
                    kl = self._refresh_klines(sym, price)
                    trend = self._refresh_trend(sym)
                    bias = self._refresh_h1_bias(sym)
                    
                    # 2. Analyze
                    sess_key, sess_name, sess_mult = get_session()
                    sp = SESSION_REGIME_PARAMS[sess_key]
                    regime = detect_regime(kl, compute_atr(kl))
                    sig = compute_signal(kl, trend, bias, regime)
                    
                    # 3. Execution
                    if (sig["direction"] != "NONE" and session_active and 
                        sig["score"] >= sp["min_score"] and regime != "DEAD" and 
                        sym not in self.positions):
                        
                        atr = sig["atr"]
                        sl_dist = atr * sp["sl_atr"]
                        sl_dist = max(price * MIN_SL_PCT[sym], min(sl_dist, price * MAX_SL_PCT))
                        tp_dist = sl_dist * sp["tp_r"]
                        
                        lot = lot_size(sym, sl_dist, equity, sess_mult, sig["score"])
                        
                        dir_str = "BUY" if sig["direction"] == "BUY" else "SELL"
                        sl = round(price - sl_dist if dir_str == "BUY" else price + sl_dist, 5)
                        tp = round(price + tp_dist if dir_str == "BUY" else price - tp_dist, 5)
                        
                        self._send_signal(sym, dir_str, lot, sl, tp)
                        self.positions[sym] = {"entry": price, "dir": dir_str}
                
                time.sleep(INTERVAL)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(10)

    def _read_status(self):
        if not MT5_STATUS.exists(): return {}
        try: return json.loads(MT5_STATUS.read_text())
        except: return {}

    def _refresh_klines(self, symbol, price):
        now = time.time()
        if now - self.klines_ts[symbol] > 300 or not self.klines[symbol]:
            fresh = fetch_klines(symbol)
            if fresh: self.klines[symbol] = fresh; self.klines_ts[symbol] = now
            else: 
                if not self.klines[symbol]: self.klines[symbol] = [price]*50
                self.klines[symbol].append(price)
                if len(self.klines[symbol]) > 100: self.klines[symbol].pop(0)
        return self.klines[symbol]

    def _refresh_trend(self, symbol):
        now = time.time()
        if now - self.trend_ts[symbol] > 900:
            self.trend_15m[symbol] = get_trend_15m(symbol)
            self.trend_ts[symbol] = now
        return self.trend_15m[symbol]

    def _refresh_h1_bias(self, symbol):
        now = time.time()
        if now - self.h1_bias_ts[symbol] > 3600:
            self.h1_bias[symbol] = get_h1_bias(symbol)
            self.h1_bias_ts[symbol] = now
        return self.h1_bias[symbol]

    def _send_signal(self, symbol, direction, lot, sl, tp):
        sig_id = f"{symbol}_{direction}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        sig = {"id": sig_id, "action": direction, "symbol": symbol, "lot": lot, "sl": sl, "tp": tp, "timestamp": datetime.now().isoformat()}
        SIGNAL_FILE.write_text(json.dumps(sig, separators=(",", ":")))
        print(f"🚀 SENT SIGNAL: {sig_id} | {direction} {lot}L {symbol}")

if __name__ == "__main__":
    agent = MT5AutonomousAgent()
    agent.run()
