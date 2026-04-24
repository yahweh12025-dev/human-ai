"""
Data Fetcher Module

Responsible for fetching market data from various providers.
Currently supports CCXT (for Binance futures).
"""
import pandas as pd
import ccxt
from datetime import datetime, timedelta
import numpy as np
import logging

class DataFetcher:
    def __init__(self, config):
        """
        Initialize the data fetcher.
        :param config: Dictionary containing data configuration.
        """
        self.provider = config.get('provider', 'binance')
        self.history_length = config.get('history_length', 200)
        self.timeframe = config.get('timeframe', '1h')  # Default to 1-hour candles
        self.logger = logging.getLogger(__name__)
        
        # PROXY SUPPORT: Load from config
        self.proxies = config.get('proxies', {})
        
        # Initialize exchange
        if self.provider == 'binance':
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                },
            })
            # Apply proxy if configured
            if self.proxies:
                self.exchange.proxies = self.proxies

    def fetch_latest_data(self, symbol):
        """
        Fetch the latest historical data for a symbol.
        :param symbol: Trading symbol (e.g., 'BTC/USDT', 'ETH/USDT')
        :return: pandas DataFrame with OHLCV data or None if error.
        """
        # Only proceed to real API since we removed mock data support
        try:
            if self.provider == 'binance':
                return self._fetch_binance_futures(symbol)
            else:
                # Fallback to yfinance for other providers (for backwards compatibility)
                return self._fetch_yfinance(symbol)
        except Exception as e:
            self.logger.exception(f"Error fetching data for {symbol}: {e}")
            return None

    def _fetch_binance_futures(self, symbol):
        """
        Fetch futures data from Binance using CCXT.
        :param symbol: Trading symbol in CCXT format (e.g., 'BTC/USDT')
        :return: pandas DataFrame with OHLCV data
        """
        try:
            # Convert symbol to CCXT format if needed (e.g., BTC-USD -> BTC/USDT)
            ccxt_symbol = symbol.replace('-', '/')
            if '/' not in ccxt_symbol and 'USDT' not in ccxt_symbol:
                # Assume it's a crypto pair and add USDT
                if ccxt_symbol.endswith('USD'):
                    ccxt_symbol = ccxt_symbol[:-3] + '/USDT'
                elif len(ccxt_symbol) >= 3:  # Add USDT to the end
                    ccxt_symbol = ccxt_symbol + '/USDT'
            
            # Fetch OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(
                ccxt_symbol, 
                timeframe=self.timeframe,
                limit=self.history_length
            )
            
            if not ohlcv:
                self.logger.warning(f"No OHLCV data returned for symbol {ccxt_symbol}")
                return None
                
            # Convert to pandas DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            self.logger.debug(f"Fetched {len(df)} rows for {ccxt_symbol} from Binance futures")
            return df
            
        except Exception as e:
            self.logger.exception(f"Error fetching Binance futures data for {symbol}: {e}")
            return None

    def _fetch_yfinance(self, symbol):
        """
        Fetch data from Yahoo Finance (fallback for non-crypto or testing).
        :param symbol: Trading symbol (e.g., 'BTC-USD', 'AAPL')
        :return: pandas DataFrame with OHLCV data or None if error.
        """
        try:
            # Calculate the period needed: we want enough data for indicators.
            # We'll fetch a bit more than history_length to ensure we have enough after any potential NaNs.
            period_days = max(self.history_length, 100)  # at least 100 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)

            # Fetch data from yfinance
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date, interval='1d')
            if data.empty:
                self.logger.warning(f"No data returned for symbol {symbol}")
                return None

            # Keep only the last `history_length` rows for consistency
            if len(data) > self.history_length:
                data = data.tail(self.history_length)

            # Ensure we have the expected columns
            expected_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in data.columns for col in expected_cols):
                self.logger.warning(f"Unexpected columns in data for {symbol}: {data.columns}")
                return None

            self.logger.debug(f"Fetched {len(data)} rows for {symbol} from yfinance")
            return data

        except Exception as e:
            self.logger.exception(f"Error fetching yfinance data for {symbol}: {e}")
            return None
