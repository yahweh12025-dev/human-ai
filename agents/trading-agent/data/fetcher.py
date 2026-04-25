"""
Data Fetcher Module

Responsible for fetching market data from various providers.
Currently supports CCXT (Binance) and Alpaca Markets.
"""

import pandas as pd
import ccxt
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta
import numpy as np
import logging

class DataFetcher:
    def __init__(self, config):
        """
        Initialize the data fetcher with dual-source support.
        """
        self.config = config
        self.provider = config.get('provider', 'binance')
        self.history_length = config.get('history_length', 200)
        self.timeframe = config.get('timeframe', '1h')
        self.logger = logging.getLogger(__name__)
        
        # Proxy Support
        self.proxies = config.get('proxies', {})
        
        # Initialize Binance
        self.exchange = None
        if self.provider == 'binance':
            try:
                # Get API keys from execution config if available
                execution_config = config.get('execution', {})
                api_key = execution_config.get('api_key')
                api_secret = execution_config.get('api_secret')
                exchange_id = execution_config.get('exchange', 'binance')
                # Determine if testnet: either exchange name contains 'testnet' or futures.testnet is true
                testnet = ('testnet' in exchange_id.lower()) or \
                          config.get('futures', {}).get('testnet', False)
                
                self.exchange = ccxt.binance({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                    'options': {'defaultType': 'future'},
                })
                if testnet:
                    self.exchange.set_sandbox_mode(True)
                    self.logger.info("Binance testnet mode enabled.")
                else:
                    self.logger.info("Binance live mode enabled.")
            except Exception as e:
                self.logger.error(f"Binance Init Error: {e}")

        # Initialize Alpaca Fallback
        self.alpaca = None
        # Check for alpaca_enabled or just use keys if provided in config
        if config.get('alpaca_enabled', False) or config.get('alpaca_trading', {}):
            try:
                # Prefer alpaca_trading keys from config
                alpaca_cfg = config.get('alpaca_trading', {})
                api_key = alpaca_cfg.get('api_key') or config.get('alpaca_key')
                api_secret = alpaca_cfg.get('api_secret') or config.get('alpaca_secret')
                base_url = alpaca_cfg.get('base_url', config.get('alpaca_base_url', 'https://paper-api.alpaca.markets')).replace('/v2', '')
                
                self.alpaca = tradeapi.REST(
                    api_key,
                    api_secret,
                    base_url=base_url
                )
                self.logger.info("Alpaca Fallback initialized successfully.")
            except Exception as e:
                self.logger.error(f"Alpaca Init Error: {e}")

    def fetch_latest_data(self, symbol):
        """
        Fetch latest data with an automatic fallback to Alpaca.
        """
        try:
            if self.provider == 'binance' and self.exchange:
                return self._fetch_binance_futures(symbol)
            elif self.alpaca:
                return self._fetch_alpaca_data(symbol)
            else:
                raise ConnectionError("No active data providers available.")
        except Exception as e:
            self.logger.error(f"Fetch failed for {symbol}: {e}")
            # Final attempt: Alpaca
            if self.alpaca:
                return self._fetch_alpaca_data(symbol)
            raise ConnectionError(f"CRITICAL: All data sources failed for {symbol}")

    def _fetch_binance_futures(self, symbol):
        """
        Fetch data from Binance via CCXT.
        """
        ohlcv = self.exchange.fetch_ohlcv(symbol, self.timeframe, limit=self.history_length)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df

    def _fetch_alpaca_data(self, symbol):
        """
        Fetch data from Alpaca API.
        """
        # Map Binance symbol (BTC/USDT) to Alpaca (BTC/USD)
        alpaca_symbol = symbol.replace('USDT', 'USD').replace('/', '').upper()
        try:
            # Fetch bars using Alpaca SDK
            # Ensure timeframe is compatible with Alpaca (e.g., '1Hour', '1Day', '1Min')
            alpaca_tf = self.timeframe.replace('h', 'Hour').replace('m', 'Min').replace('d', 'Day')
            
            bars = self.alpaca.get_crypto_bars(alpaca_symbol, alpaca_tf).df
            if bars is None or bars.empty:
                return None
            
            # Normalize to Binance format
            # Alpaca's get_crypto_bars().df has a DatetimeIndex and columns: open, high, low, close, volume, trade_count
            df = bars[['open', 'high', 'low', 'close', 'volume']].copy()
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            return df
        except Exception as e:
            self.logger.error(f"Alpaca fetch failed for {symbol} ({alpaca_symbol}): {e}")
            return None
