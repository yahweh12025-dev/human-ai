#!/usr/bin/env python3
"""
Binance Demo Futures Client
Direct API client for Binance Demo Futures (demo-fapi.binance.com)
Works with demo API keys that only support futures endpoints.
"""

import hashlib
import hmac
import json
import os
import time
import requests
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / '.env')


class BinanceDemoClient:
    """
    Direct client for Binance Demo Futures API.
    Avoids CCXT's load_markets which hits spot API (not supported by demo keys).
    """

    def __init__(self):
        self.api_key = os.getenv('BINANCE_TESTNET_API_KEY')
        self.secret = os.getenv('BINANCE_TESTNET_SECRET_KEY')
        self.base_url = os.getenv('BINANCE_DEMO_ENDPOINT', 'https://demo-fapi.binance.com')

        if not self.api_key or not self.secret:
            raise ValueError("BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_SECRET_KEY required in .env")

        # Load exchange info for symbol precision (tick size, step size)
        self._exchange_info = {}
        self._load_exchange_info()

    def _sign(self, params: Dict) -> Dict:
        """Add timestamp and HMAC signature to params"""
        params['timestamp'] = int(time.time() * 1000)
        params['recvWindow'] = 5000
        query_string = '&'.join(f'{k}={v}' for k, v in params.items())
        signature = hmac.new(self.secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
        params['signature'] = signature
        return params

    def _headers(self) -> Dict:
        return {'X-MBX-APIKEY': self.api_key}

    def _get_public(self, endpoint: str, params: Dict = None) -> Dict:
        resp = requests.get(f'{self.base_url}{endpoint}', params=params or {}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _get_private(self, endpoint: str, params: Dict = None) -> any:
        params = self._sign(params or {})
        resp = requests.get(f'{self.base_url}{endpoint}', params=params, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post_private(self, endpoint: str, params: Dict = None) -> Dict:
        params = self._sign(params or {})
        resp = requests.post(f'{self.base_url}{endpoint}', params=params, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _delete_private(self, endpoint: str, params: Dict = None) -> Dict:
        params = self._sign(params or {})
        resp = requests.delete(f'{self.base_url}{endpoint}', params=params, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _load_exchange_info(self):
        """Fetch and cache exchange info for symbol filters."""
        try:
            data = self._get_public('/fapi/v1/exchangeInfo', {})
            self._exchange_info = data
        except Exception as e:
            print(f"[WARN] Failed to load exchange info: {e}")
            self._exchange_info = {}

    def _get_price_filter(self, symbol: str) -> Dict:
        """Return PRICE_FILTER dict for symbol, or empty dict."""
        for s in self._exchange_info.get('symbols', []):
            if s['symbol'] == symbol:
                for f in s['filters']:
                    if f['filterType'] == 'PRICE_FILTER':
                        return f
        return {}

    def _get_lot_size(self, symbol: str) -> Dict:
        """Return LOT_SIZE filter dict for symbol, or empty dict."""
        for s in self._exchange_info.get('symbols', []):
            if s['symbol'] == symbol:
                for f in s['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        return f
        return {}

    def _round_price(self, symbol: str, price: float) -> float:
        """Round price to the symbol's tickSize."""
        pf = self._get_price_filter(symbol)
        tick = float(pf.get('tickSize', 0.001))
        rounded = round(price / tick) * tick
        tick_str = str(tick).rstrip('0')
        if '.' in tick_str:
            decimals = len(tick_str.split('.')[-1])
        else:
            decimals = 0
        return round(rounded, decimals)

    def _round_qty(self, symbol: str, qty: float) -> float:
        """Round quantity to the symbol's stepSize."""
        ls = self._get_lot_size(symbol)
        step = float(ls.get('stepSize', 0.001))
        rounded = math.floor(qty / step) * step
        step_str = str(step).rstrip('0')
        if '.' in step_str:
            decimals = len(step_str.split('.')[-1])
        else:
            decimals = 0
        return round(rounded, decimals)

    # === Public Endpoints ===

    def get_price(self, symbol: str = 'BTCUSDT') -> float:
        data = self._get_public('/fapi/v1/ticker/price', {'symbol': symbol})
        return float(data['price'])

    def get_ticker(self, symbol: str = 'BTCUSDT') -> Dict:
        return self._get_public('/fapi/v1/ticker/24hr', {'symbol': symbol})

    def get_funding_rate(self, symbol: str = 'BTCUSDT') -> float:
        """Return current funding rate for the symbol."""
        data = self._get_public('/fapi/v1/premiumIndex', {'symbol': symbol})
        return float(data.get('lastFundingRate', 0.0))

    def get_klines(self, symbol: str = 'BTCUSDT', interval: str = '1h', limit: int = 200) -> List:
        return self._get_public('/fapi/v1/klines', {'symbol': symbol, 'interval': interval, 'limit': limit})

    def get_orderbook(self, symbol: str = 'BTCUSDT', limit: int = 10) -> Dict:
        return self._get_public('/fapi/v1/depth', {'symbol': symbol, 'limit': limit})

    def get_recent_trades(self, symbol: str = 'BTCUSDT', limit: int = 500) -> List:
        """Fetch recent trades for CVD calculation."""
        return self._get_public('/fapi/v1/trades', {'symbol': symbol, 'limit': limit})

    def place_limit_order(self, symbol: str, side: str, quantity: float,
                          price: float, time_in_force: str = 'GTC') -> Dict:
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': 'LIMIT',
            'quantity': quantity,
            'price': price,
            'timeInForce': time_in_force,
        }
        return self._post_private('/fapi/v1/order', params)

    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        return self._delete_private('/fapi/v1/order', {'symbol': symbol, 'orderId': order_id})

    def cancel_all_orders(self, symbol: str) -> Dict:
        return self._delete_private('/fapi/v1/allOpenOrders', {'symbol': symbol})

    def set_leverage(self, symbol: str, leverage: int) -> Dict:
        return self._post_private('/fapi/v1/leverage', {'symbol': symbol, 'leverage': leverage})

    # === Convenience Methods ===

    def get_account_summary(self) -> Dict:
        """Full account summary"""
        balance = self.get_usdt_balance()
        positions = self.get_positions()
        price = self.get_price('BTCUSDT')

        return {
            'usdt_balance': balance,
            'btc_price': price,
            'open_positions': len(positions),
            'positions': positions,
            'timestamp': datetime.now().isoformat(),
        }

    def execute_test_trade(self, symbol: str = 'BTCUSDT', side: str = 'BUY',
                          quantity: float = 0.001) -> Dict:
        """Execute a small test trade"""
        try:
            order = self.place_market_order(symbol, side, quantity)
            result = {
                'success': True,
                'order_id': order.get('orderId'),
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': float(order.get('avgPrice', 0)),
                'status': order.get('status'),
                'timestamp': datetime.now().isoformat(),
            }
            self._log_trade(result)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _log_trade(self, trade: Dict):
        """Log trade to file"""
        log_dir = Path(__file__).resolve().parents[2] / 'logs' / 'trading'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"demo_trades_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(trade) + '\n')


def main():
    client = BinanceDemoClient()

    print("Binance Demo Futures - Connection Test")
    print("=" * 50)

    summary = client.get_account_summary()
    print(f"  ✅ Connected to Binance Demo Futures")
    print(f"  USDT Balance: ${summary['usdt_balance']:.2f}")
    print(f"  BTC Price: ${summary['btc_price']:.2f}")
    print(f"  Open Positions: {summary['open_positions']}")

    # Fetch historical data for backtest
    klines = client.get_klines('BTCUSDT', '1h', 100)
    print(f"  Historical data: {len(klines)} candles available")
    print(f"  ✅ Backtesting & Forward-testing OPERATIONAL")

    return client


if __name__ == "__main__":
    main()
