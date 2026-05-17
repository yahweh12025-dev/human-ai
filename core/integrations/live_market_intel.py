#!/usr/bin/env python3
"""
Live Market Intelligence — v1.0
================================
Aggregates real-time signals from multiple free APIs:
  1. Fear & Greed Index   — alternative.me (no key)
  2. BTC dominance + MCap — CoinGecko global (no key)
  3. Alpaca BTC H1 trend  — Alpaca data API (key from .env)
  4. BTC 4H macro trend   — Binance public klines (no key)
  5. Crypto news sentiment — CryptoCompare news (no key)

Cache: data/market_cache/live_intel.json — 10 min TTL
NEVER raises — all sources wrapped in try/except with safe defaults.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

try:
    import requests as _requests
except ImportError:
    _requests = None  # type: ignore

_CACHE_DIR  = Path(__file__).resolve().parents[2] / "data" / "market_cache"
_CACHE_FILE = _CACHE_DIR / "live_intel.json"
_CACHE_TTL  = 600  # 10 minutes

_DEFAULT = {
    "fear_greed":          {"value": 50, "label": "Neutral"},
    "btc_dominance":       50.0,
    "market_cap_change_24h": 0.0,
    "alpaca_btc_trend":    "NEUTRAL",
    "macro_trend_4h":      "NEUTRAL",
    "news_sentiment":      0.0,
    "composite_bias":      "NEUTRAL",
    "composite_score":     0.0,
    "cached_at":           "",
}

# ── positive/negative keyword sets for headline scoring ────────────────────
_POS_WORDS = {
    "surge", "surges", "surged", "rally", "rallies", "rallied", "bullish",
    "bull", "pump", "pumps", "pumped", "rise", "rises", "rose", "gain",
    "gains", "gained", "breakout", "adoption", "upgrade", "partnership",
    "record", "high", "growth", "positive", "buy", "bought", "recovering",
    "recover", "recovery", "strong", "outperform", "soar", "soars", "soared",
}
_NEG_WORDS = {
    "crash", "crashes", "crashed", "dump", "dumps", "dumped", "bearish",
    "bear", "drop", "drops", "dropped", "fall", "falls", "fell", "plunge",
    "plunges", "plunged", "hack", "hacked", "scam", "fraud", "ban", "bans",
    "banned", "sell", "selling", "selloff", "sold", "decline", "declines",
    "declined", "loss", "losses", "risk", "warning", "negative", "concern",
    "concerns", "down", "fear", "fears", "collapse", "collapses", "weak",
}


def _get(url: str, params=None, headers=None, timeout: int = 8):
    """Safe HTTP GET — returns parsed JSON or None."""
    if _requests is None:
        return None
    try:
        r = _requests.get(url, params=params, headers=headers, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


# ── 1. Fear & Greed ────────────────────────────────────────────────────────
def _fetch_fear_greed() -> dict:
    data = _get("https://api.alternative.me/fng/?limit=1")
    try:
        entry = data["data"][0]
        return {
            "value": int(entry.get("value", 50)),
            "label": entry.get("value_classification", "Neutral"),
        }
    except Exception:
        pass
    return {"value": 50, "label": "Neutral"}


# ── 2. CoinGecko global ────────────────────────────────────────────────────
def _fetch_coingecko_global() -> dict:
    data = _get(
        "https://api.coingecko.com/api/v3/global",
        headers={"Accept": "application/json"},
    )
    defaults = {"btc_dominance": 50.0, "market_cap_change_24h": 0.0}
    try:
        d = data["data"]
        return {
            "btc_dominance":       float(d.get("btc_dominance", {}) if not isinstance(d.get("btc_dominance"), float) else d["btc_dominance"]),
            "market_cap_change_24h": float(d.get("market_cap_change_percentage_24h_usd", 0.0)),
        }
    except Exception:
        pass
    # second-pass: handle nested dict structure
    try:
        d = data["data"]
        dom = d.get("market_cap_percentage", {}).get("btc", 50.0)
        chg = d.get("market_cap_change_percentage_24h_usd", 0.0)
        return {"btc_dominance": float(dom), "market_cap_change_24h": float(chg)}
    except Exception:
        pass
    return defaults


# ── 3. Alpaca BTC H1 EMA trend ────────────────────────────────────────────
def _fetch_alpaca_btc_h1() -> str:
    key    = os.environ.get("ALPACA_API_KEY", "")
    secret = os.environ.get("ALPACA_SECRET_KEY", "")
    if not key or not secret:
        return "NEUTRAL"
    data = _get(
        "https://data.alpaca.markets/v1beta3/crypto/us/bars",
        params={"symbols": "BTC/USD", "timeframe": "1Hour", "limit": 10, "sort": "asc"},
        headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret},
    )
    try:
        bars   = data["bars"]["BTC/USD"]
        closes = [float(b["c"]) for b in bars]
        if len(closes) < 5:
            return "NEUTRAL"
        # EMA5
        k = 2 / (5 + 1)
        ema = closes[0]
        for c in closes[1:]:
            ema = c * k + ema * (1 - k)
        last = closes[-1]
        if last > ema * 1.0005:
            return "BULL"
        if last < ema * 0.9995:
            return "BEAR"
    except Exception:
        pass
    return "NEUTRAL"


# ── 4. Binance 4H macro trend ─────────────────────────────────────────────
def _fetch_binance_4h_trend() -> str:
    data = _get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": "BTCUSDT", "interval": "4h", "limit": 20},
    )
    try:
        closes = [float(k[4]) for k in data]
        if len(closes) < 5:
            return "NEUTRAL"
        sma20 = sum(closes) / len(closes)
        last  = closes[-1]
        if last > sma20 * 1.001:
            return "BULL"
        if last < sma20 * 0.999:
            return "BEAR"
    except Exception:
        pass
    return "NEUTRAL"


# ── 5. CryptoCompare news sentiment ───────────────────────────────────────
def _fetch_news_sentiment() -> float:
    data = _get(
        "https://min-api.cryptocompare.com/data/v2/news/",
        params={"lang": "EN", "categories": "BTC,ETH", "sortOrder": "popular"},
    )
    try:
        articles = data.get("Data", [])[:10]
        if not articles:
            return 0.0
        pos = neg = 0
        for a in articles:
            title = (a.get("title", "") + " " + a.get("body", "")[:200]).lower().split()
            pos += sum(1 for w in title if w in _POS_WORDS)
            neg += sum(1 for w in title if w in _NEG_WORDS)
        total = pos + neg
        if total == 0:
            return 0.0
        return round((pos - neg) / total, 3)
    except Exception:
        pass
    return 0.0


# ── Composite scoring ─────────────────────────────────────────────────────
def _composite(fg_val: int, alpaca_trend: str, macro_4h: str,
                market_cap_change: float, news_score: float) -> tuple:
    """Returns (composite_score, composite_bias)."""
    score = 0.0

    # Fear & Greed contribution
    if fg_val < 25:
        score -= 0.5
    elif fg_val < 45:
        score -= 0.2
    elif fg_val <= 55:
        score += 0.0
    elif fg_val <= 75:
        score += 0.2
    else:
        score += 0.5

    # Alpaca H1 trend
    if alpaca_trend == "BULL":
        score += 0.2
    elif alpaca_trend == "BEAR":
        score -= 0.2

    # Binance 4H macro trend
    if macro_4h == "BULL":
        score += 0.2
    elif macro_4h == "BEAR":
        score -= 0.2

    # Market cap change (altcoin season proxy — falling BTC dom is handled via dominance)
    # Use market_cap_change as overall risk-on/off
    if market_cap_change < -2.0:
        score -= 0.1
    elif market_cap_change > 2.0:
        score += 0.1

    # News sentiment (weight 0.1)
    score += news_score * 0.1

    score = round(max(-1.0, min(1.0, score)), 4)
    if score > 0.15:
        bias = "BULL"
    elif score < -0.15:
        bias = "BEAR"
    else:
        bias = "NEUTRAL"

    return score, bias


# ── Main public function ───────────────────────────────────────────────────
def get_live_intel() -> dict:
    """
    Return live market intelligence, cached for 10 minutes.
    NEVER raises — always returns a valid dict with safe defaults.
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Serve from cache if fresh enough
    try:
        if _CACHE_FILE.exists():
            age = time.time() - _CACHE_FILE.stat().st_mtime
            if age < _CACHE_TTL:
                cached = json.loads(_CACHE_FILE.read_text())
                if cached:
                    return cached
    except Exception:
        pass

    # ── Fetch all sources (each individually guarded) ──────────────────────
    fg      = _DEFAULT["fear_greed"].copy()
    cg      = {"btc_dominance": 50.0, "market_cap_change_24h": 0.0}
    alpaca  = "NEUTRAL"
    macro   = "NEUTRAL"
    news    = 0.0

    try:
        fg = _fetch_fear_greed()
    except Exception:
        pass

    try:
        cg = _fetch_coingecko_global()
    except Exception:
        pass

    try:
        alpaca = _fetch_alpaca_btc_h1()
    except Exception:
        pass

    try:
        macro = _fetch_binance_4h_trend()
    except Exception:
        pass

    try:
        news = _fetch_news_sentiment()
    except Exception:
        pass

    comp_score, comp_bias = _DEFAULT["composite_score"], _DEFAULT["composite_bias"]
    try:
        comp_score, comp_bias = _composite(
            fg_val=fg["value"],
            alpaca_trend=alpaca,
            macro_4h=macro,
            market_cap_change=cg.get("market_cap_change_24h", 0.0),
            news_score=news,
        )
    except Exception:
        pass

    result = {
        "fear_greed":            fg,
        "btc_dominance":         round(cg.get("btc_dominance", 50.0), 3),
        "market_cap_change_24h": round(cg.get("market_cap_change_24h", 0.0), 3),
        "alpaca_btc_trend":      alpaca,
        "macro_trend_4h":        macro,
        "news_sentiment":        news,
        "composite_bias":        comp_bias,
        "composite_score":       comp_score,
        "cached_at":             datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
    }

    # Write cache (best effort)
    try:
        _CACHE_FILE.write_text(json.dumps(result, indent=2))
    except Exception:
        pass

    return result


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    import json as _json
    print(_json.dumps(get_live_intel(), indent=2))
