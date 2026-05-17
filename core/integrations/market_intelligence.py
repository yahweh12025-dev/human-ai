#!/usr/bin/env python3
"""
Market Intelligence Hub
Aggregates signals from: Alpaca, CoinMarketCap, yfinance, Fear&Greed index
Used by both trading agents to improve entry/exit decisions.
"""

import json
import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "market_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cached(key: str, ttl: int, fn):
    """Simple file-based cache with TTL seconds."""
    cache_file = _CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < ttl:
            try:
                return json.loads(cache_file.read_text())
            except Exception:
                pass
    result = fn()
    if result:
        try:
            cache_file.write_text(json.dumps(result))
        except Exception:
            pass
    return result


class AlpacaDataClient:
    """Alpaca paper trading account + market data."""

    PAPER_BASE = "https://paper-api.alpaca.markets/v2"
    DATA_BASE  = "https://data.alpaca.markets"

    def __init__(self):
        self.key    = os.getenv("ALPACA_API_KEY", "")
        self.secret = os.getenv("ALPACA_SECRET_KEY", "")
        self._h     = {"APCA-API-KEY-ID": self.key, "APCA-API-SECRET-KEY": self.secret}

    def get_account(self) -> Dict:
        try:
            r = requests.get(f"{self.PAPER_BASE}/account", headers=self._h, timeout=8)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.warning(f"Alpaca account error: {e}")
        return {}

    def get_crypto_bars(self, symbol: str = "BTC/USD", timeframe: str = "1Min", limit: int = 60) -> List[Dict]:
        """Get crypto OHLCV bars from Alpaca v1beta3."""
        def _fetch():
            try:
                r = requests.get(
                    f"{self.DATA_BASE}/v1beta3/crypto/us/bars",
                    params={"symbols": symbol, "timeframe": timeframe, "limit": limit, "sort": "asc"},
                    headers=self._h, timeout=10,
                )
                if r.status_code == 200:
                    return r.json().get("bars", {}).get(symbol, [])
            except Exception as e:
                logger.warning(f"Alpaca bars error: {e}")
            return []
        return _cached(f"alpaca_{symbol.replace('/','_')}_{timeframe}", 30, _fetch)

    def get_stock_bars(self, symbol: str = "GLD", timeframe: str = "1Min", limit: int = 60) -> List[Dict]:
        """Get stock/ETF bars (GLD for gold proxy)."""
        def _fetch():
            try:
                r = requests.get(
                    f"{self.DATA_BASE}/v2/stocks/bars",
                    params={"symbols": symbol, "timeframe": timeframe, "limit": limit, "sort": "asc"},
                    headers=self._h, timeout=10,
                )
                if r.status_code == 200:
                    return r.json().get("bars", {}).get(symbol, [])
            except Exception as e:
                logger.warning(f"Alpaca stock bars error: {e}")
            return []
        return _cached(f"alpaca_stock_{symbol}_{timeframe}", 30, _fetch)

    def get_crypto_orderbook(self, symbol: str = "BTC/USD") -> Dict:
        try:
            r = requests.get(
                f"{self.DATA_BASE}/v1beta3/crypto/us/quotes/latest",
                params={"symbols": symbol},
                headers=self._h, timeout=8,
            )
            if r.status_code == 200:
                return r.json().get("quotes", {}).get(symbol, {})
        except Exception as e:
            logger.warning(f"Alpaca quote error: {e}")
        return {}


class CoinMarketCapClient:
    """CoinMarketCap API — 10k requests/month budget."""

    BASE = "https://pro-api.coinmarketcap.com/v1"

    def __init__(self):
        self.key = os.getenv("COINMARKETCAP_API_KEY", "")
        self._h  = {"X-CMC_PRO_API_KEY": self.key, "Accept": "application/json"}

    def get_global_metrics(self) -> Dict:
        def _fetch():
            try:
                r = requests.get(f"{self.BASE}/global-metrics/quotes/latest", headers=self._h, timeout=8)
                if r.status_code == 200:
                    return r.json().get("data", {})
            except Exception as e:
                logger.warning(f"CMC global metrics error: {e}")
            return {}
        return _cached("cmc_global", 300, _fetch)  # 5 min TTL

    def get_fear_greed(self) -> Dict:
        """Fear & Greed index (via alternative.me — free, no key)."""
        def _fetch():
            try:
                r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=8)
                if r.status_code == 200:
                    d = r.json().get("data", [{}])[0]
                    return {"value": int(d.get("value", 50)), "label": d.get("value_classification", "Neutral")}
            except Exception as e:
                logger.warning(f"Fear/Greed error: {e}")
            return {"value": 50, "label": "Neutral"}
        return _cached("fear_greed", 300, _fetch)

    def get_btc_dominance(self) -> float:
        metrics = self.get_global_metrics()
        return float(metrics.get("btc_dominance", 50.0))

    def get_top_movers(self, limit: int = 5) -> List[Dict]:
        """Get top gaining cryptos — useful for BTC sentiment."""
        def _fetch():
            try:
                r = requests.get(f"{self.BASE}/cryptocurrency/listings/latest",
                    params={"limit": limit, "sort": "percent_change_24h", "sort_dir": "desc"},
                    headers=self._h, timeout=8)
                if r.status_code == 200:
                    return [{"symbol": c["symbol"], "change_24h": c["quote"]["USD"]["percent_change_24h"]}
                            for c in r.json().get("data", [])]
            except Exception as e:
                logger.warning(f"CMC top movers error: {e}")
            return []
        return _cached("cmc_movers", 300, _fetch)


class MarketSentiment:
    """
    Aggregates market sentiment from multiple sources.
    Returns a sentiment score -1.0 (bearish) to +1.0 (bullish).
    """

    def __init__(self):
        self.alpaca = AlpacaDataClient()
        self.cmc    = CoinMarketCapClient()

    def get_crypto_sentiment(self) -> Dict:
        """Crypto market sentiment for Binance BTC/USDT agent."""
        fg = self.cmc.get_fear_greed()
        fg_score = (fg["value"] - 50) / 50  # -1 to +1

        btc_dom = self.cmc.get_btc_dominance()
        dom_score = (btc_dom - 50) / 50  # high dominance = risk-off (slightly bearish for alts)

        # Alpaca crypto trend from recent bars
        bars = self.alpaca.get_crypto_bars("BTC/USD", "15Min", 8)
        trend_score = 0.0
        if len(bars) >= 4:
            closes = [b["c"] for b in bars]
            sma4 = sum(closes[-4:]) / 4
            trend_score = 0.3 if closes[-1] > sma4 * 1.001 else (-0.3 if closes[-1] < sma4 * 0.999 else 0)

        combined = (fg_score * 0.4 + trend_score * 0.4 + (-dom_score) * 0.2)
        combined = max(-1.0, min(1.0, combined))

        return {
            "score": round(combined, 3),
            "bias": "BUY" if combined > 0.15 else ("SELL" if combined < -0.15 else "NEUTRAL"),
            "fear_greed": fg,
            "btc_dominance": btc_dom,
            "trend_score": trend_score,
            "timestamp": datetime.now().isoformat(),
        }

    def get_metals_sentiment(self) -> Dict:
        """Metals sentiment for EA XAUUSD/XAGUSD agent."""
        # Gold proxy via GLD ETF on Alpaca
        gld_bars = self.alpaca.get_stock_bars("GLD", "5Min", 12)
        trend_score = 0.0
        gold_price = None
        if len(gld_bars) >= 6:
            closes = [b["c"] for b in gld_bars]
            gold_price = closes[-1] * 10  # GLD ≈ 1/10 gold price
            sma6 = sum(closes[-6:]) / 6
            trend_score = 0.4 if closes[-1] > sma6 * 1.0005 else (-0.4 if closes[-1] < sma6 * 0.9995 else 0)

        # DXY inverse correlation (dollar up → gold down)
        # Use UUP ETF as dollar proxy
        uup_bars = self.alpaca.get_stock_bars("UUP", "5Min", 6)
        dollar_score = 0.0
        if len(uup_bars) >= 3:
            uup_closes = [b["c"] for b in uup_bars]
            dollar_up = uup_closes[-1] > uup_closes[0] * 1.0002
            dollar_score = -0.3 if dollar_up else (0.2 if uup_closes[-1] < uup_closes[0] * 0.9998 else 0)

        combined = (trend_score * 0.6 + dollar_score * 0.4)
        combined = max(-1.0, min(1.0, combined))

        return {
            "score": round(combined, 3),
            "bias": "BUY" if combined > 0.1 else ("SELL" if combined < -0.1 else "NEUTRAL"),
            "gold_proxy_price": gold_price,
            "trend_score": trend_score,
            "dollar_score": dollar_score,
            "timestamp": datetime.now().isoformat(),
        }


def get_sentiment_for_trading() -> Dict:
    """One-shot call for both agents — cached 5 min."""
    ms = MarketSentiment()
    result = {
        "crypto": ms.get_crypto_sentiment(),
        "metals": ms.get_metals_sentiment(),
        "timestamp": datetime.now().isoformat(),
    }
    # v9.2: also refresh live_intel cache alongside the legacy sentiment update
    try:
        from core.integrations.live_market_intel import get_live_intel
        get_live_intel()
    except Exception:
        pass
    return result


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / '.env')
    result = get_sentiment_for_trading()
    print(json.dumps(result, indent=2))
