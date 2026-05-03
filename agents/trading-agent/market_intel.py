#!/usr/bin/env python3
"""
Market Intelligence module for cryptocurrency trading.
Uses CryptoCompare for news and sentiment analysis, CoinGecko for market data fallback.
"""

import logging
import time
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class MarketIntel:
    def __init__(self):
        self.logger = logger
        self.last_request_time = 0
        self.min_request_interval = 1.0  # seconds between requests to avoid rate limiting
        
        # Load API keys from environment
        self.cryptocompare_api_key = os.getenv('CRYPTOCOMPARE_API_KEY')
        
        # Symbol mapping for different APIs
        self.coingecko_symbol_map = {
            'BTC/USD': 'bitcoin',
            'ETH/USD': 'ethereum',
            'SOL/USD': 'solana',
            'XRP/USD': 'ripple',
            'ADA/USD': 'cardano',
            'DOGE/USD': 'dogecoin',
            'DOT/USD': 'polkadot',
            'WLD/USD': 'worldcoin',
            'BCH/USD': 'bitcoin-cash',
            'LDO/USD': 'lido-dao'
        }
        
        # CryptoCompare symbol mapping (uses fsym/tsym format)
        self.cryptocompare_symbol_map = {
            'BTC/USD': ('BTC', 'USD'),
            'ETH/USD': ('ETH', 'USD'),
            'SOL/USD': ('SOL', 'USD'),
            'XRP/USD': ('XRP', 'USD'),
            'ADA/USD': ('ADA', 'USD'),
            'DOGE/USD': ('DOGE', 'USD'),
            'DOT/USD': ('DOT', 'USD'),
            'WLD/USD': ('WLD', 'USD'),
            'BCH/USD': ('BCH', 'USD'),
            'LDO/USD': ('LDO', 'USD')
        }
        
        # Simple sentiment word lists (can be expanded)
        self.positive_words = {
            'surge', 'rises', 'gain', 'bullish', 'up', 'high', 'breakthrough', 'rally',
            'adoption', 'institutional', 'approval', 'etf', 'partnership', 'upgrade',
            'expansion', 'growth', 'profit', 'beat', 'exceeds', 'outperform', 'strong',
            'buy', 'long', 'accumulate', 'positive', 'optimistic', 'momentum'
        }
        self.negative_words = {
            'drop', 'fall', 'decline', 'bearish', 'down', 'low', 'crash', 'dump',
            'resistance', 'rejection', 'sell-off', 'liquidation', 'ban', 'regulation',
            'lawsuit', 'hack', 'exploit', 'vulnerability', 'delay', 'postpone',
            'concern', 'risk', 'uncertainty', 'fear', 'panic', 'sell', 'short',
            'distribution', 'negative', 'pessimistic', 'weak'
        }

    def _rate_limit(self):
        """Simple rate limiting to avoid hitting API limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def fetch_crypto_news(self, symbols: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch cryptocurrency news from CryptoCompare API.
        Args:
            symbols: List of symbols like ['BTC/USD', 'ETH/USD']
            limit: Maximum number of news articles to return
        Returns:
            List of news article dictionaries
        """
        if not self.cryptocompare_api_key:
            self.logger.warning("CryptoCompare API key not configured - returning empty news list")
            return []
        
        try:
            self._rate_limit()
            # CryptoCompare news endpoint
            url = "https://min-api.cryptocompare.com/data/v2/news/"
            params = {
                'api_key': self.cryptocompare_api_key,
                'limit': min(limit * 2, 100)  # Get extra to allow for filtering
            }
            
            # Add category filter if we have specific symbols
            if symbols and len(symbols) == 1:
                # Map single symbol to CryptoCompare category
                symbol_map = {
                    'BTC/USD': 'BTC',
                    'ETH/USD': 'ETH',
                    'SOL/USD': 'SOL',
                    'XRP/USD': 'XRP',
                    'ADA/USD': 'ADA',
                    'DOGE/USD': 'DOGE',
                    'DOT/USD': 'DOT',
                    'WLD/USD': 'WLD',
                    'BCH/USD': 'BCH',
                    'LDO/USD': 'LDO'
                }
                if symbols[0] in symbol_map:
                    params['categories'] = symbol_map[symbols[0]]
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('Response') == 'Error':
                self.logger.error(f"CryptoCompare API error: {data.get('Message')}")
                return []
            
            news_items = data.get('Data', [])
            
            # Filter news by requested symbols if multiple symbols provided
            filtered_news = []
            if symbols and len(symbols) > 1:
                for item in news_items:
                    # Check tags and categories for symbol mentions
                    tags = item.get('tags', '').upper()
                    categories = item.get('categories', '')
                    # Also check title and body
                    title = item.get('title', '').upper()
                    body = item.get('body', '').upper()
                    
                    match = False
                    for sym in symbols:
                        sym_clean = sym.replace('/', '').replace('-', '')
                        if (sym_clean in tags or 
                            sym_clean in categories or 
                            sym_clean in title or 
                            sym_clean in body):
                            match = True
                            break
                    if match:
                        filtered_news.append(item)
            else:
                filtered_news = news_items
            
            # Limit results
            filtered_news = filtered_news[:limit]
            
            # Convert to standard format
            formatted_news = []
            for item in filtered_news:
                formatted_news.append({
                    'id': item.get('id'),
                    'headline': item.get('title'),
                    'summary': item.get('body', '')[:500] + '...' if len(item.get('body', '')) > 500 else item.get('body', ''),
                    'source': item.get('source'),
                    'published_at': datetime.fromtimestamp(item.get('published_on', 0)).isoformat() if item.get('published_on') else None,
                    'url': item.get('url'),
                    'symbols': self._extract_symbols_from_news(item),
                    'categories': item.get('categories', '').split('|') if item.get('categories') else []
                })
            
            self.logger.info(f"Fetched {len(formatted_news)} news articles from CryptoCompare")
            return formatted_news
            
        except Exception as e:
            self.logger.error(f"Error fetching news from CryptoCompare: {e}")
            return []

    def _extract_symbols_from_news(self, news_item: Dict) -> List[str]:
        """Extract cryptocurrency symbols mentioned in a news item."""
        symbols = []
        text = f"{news_item.get('title', '')} {news_item.get('body', '')} {news_item.get('tags', '')} {news_item.get('categories', '')}".upper()
        
        # Check for common cryptocurrency symbols
        crypto_symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'DOT', 'WLD', 'BCH', 'LDO']
        for sym in crypto_symbols:
            if sym in text:
                # Convert to our format
                if sym in ['BTC', 'ETH']:
                    symbols.append(f"{sym}/USD")
                else:
                    symbols.append(f"{sym}/USD")
        
        return list(set(symbols))  # Remove duplicates

    def calculate_sentiment(self, articles: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate sentiment scores for symbols based on news articles.
        Returns a dict mapping symbol to sentiment score between -1 and 1.
        """
        sentiment_scores = {}
        if not articles:
            return sentiment_scores
            
        # Initialize scores for all symbols found in articles
        for article in articles:
            symbols = article.get('symbols', [])
            for sym in symbols:
                if sym not in sentiment_scores:
                    sentiment_scores[sym] = 0.0
        
        # If no symbols found, return empty dict
        if not sentiment_scores:
            return sentiment_scores
            
        # Process each article
        for article in articles:
            headline = article.get('headline', '').lower()
            summary = article.get('summary', '').lower()
            text = f"{headline} {summary}"
            symbols = article.get('symbols', [])
            
            # Simple keyword counting
            pos_count = sum(1 for word in self.positive_words if word in text)
            neg_count = sum(1 for word in self.negative_words if word in text)
            
            # Calculate sentiment for this article (-1 to 1)
            total = pos_count + neg_count
            if total > 0:
                article_sentiment = (pos_count - neg_count) / total
            else:
                article_sentiment = 0.0
                
            # Distribute sentiment to symbols mentioned
            if symbols:
                weight = 1.0 / len(symbols)
                for sym in symbols:
                    sentiment_scores[sym] = sentiment_scores.get(sym, 0.0) + (article_sentiment * weight)
        
        # Normalize scores to [-1, 1] range (already is, but ensure)
        for sym in sentiment_scores:
            score = sentiment_scores[sym]
            if score > 1.0:
                sentiment_scores[sym] = 1.0
            elif score < -1.0:
                sentiment_scores[sym] = -1.0
                
        return sentiment_scores

    def get_priority_symbol(self, sentiment_scores: Dict[str, float]) -> Optional[str]:
        """
        Determine the symbol with the strongest positive sentiment.
        Returns None if no symbol has sufficient positive sentiment.
        """
        if not sentiment_scores:
            return None
            
        # Filter for positive sentiment above threshold
        positive_symbols = {sym: score for sym, score in sentiment_scores.items() if score > 0.1}
        if not positive_symbols:
            return None
            
        # Return symbol with highest score
        priority = max(positive_symbols, key=positive_symbols.get)
        return priority

    def get_market_data(self, symbol: str, limit: int = 100, timeframe: str = '1H') -> List[Dict[str, Any]]:
        """
        Get market data (OHLCV) for a symbol.
        Tries CryptoCompare first, falls back to CoinGecko.
        """
        # Try CryptoCompare first
        data = self._get_cryptocompare_market_data(symbol, limit, timeframe)
        if data:
            return data
            
        # Fall back to CoinGecko
        self.logger.info(f"Falling back to CoinGecko for {symbol} market data")
        return self._get_coingecko_market_data(symbol, limit, timeframe)

    def _get_cryptocompare_market_data(self, symbol: str, limit: int = 100, timeframe: str = '1H') -> List[Dict[str, Any]]:
        """Get market data from CryptoCompare"""
        if not self.cryptocompare_api_key:
            return []
            
        try:
            self._rate_limit()
            
            # Convert symbol format (BTC/USD -> BTC,USD)
            if symbol not in self.cryptocompare_symbol_map:
                self.logger.warning(f"Symbol {symbol} not supported for CryptoCompare")
                return []
                
            fsym, tsym = self.cryptocompare_symbol_map[symbol]
            
            # Map timeframe to CryptoCompare limit parameter
            # CryptoCompare returns last N data points based on limit
            # We'll use the limit parameter directly for histohour/histoday
            if timeframe == '1H':
                # Hourly data
                url = f"https://min-api.cryptocompare.com/data/v2/histohour"
                params = {
                    'fsym': fsym,
                    'tsym': tsym,
                    'limit': min(limit, 2000),  # CryptoCompare max limit
                    'api_key': self.cryptocompare_api_key
                }
            elif timeframe == '4H':
                # 4-hourly - we'll get hourly and aggregate, or use daily as fallback
                url = f"https://min-api.cryptocompare.com/data/v2/histohour"
                params = {
                    'fsym': fsym,
                    'tsym': tsym,
                    'limit': min(limit * 4, 2000),  # Get 4x more hourly points
                    'api_key': self.cryptocompare_api_key
                }
            elif timeframe == '1D':
                # Daily data
                url = f"https://min-api.cryptocompare.com/data/v2/histoday"
                params = {
                    'fsym': fsym,
                    'tsym': tsym,
                    'limit': min(limit, 2000),
                    'api_key': self.cryptocompare_api_key
                }
            elif timeframe == '1W':
                # Weekly - get daily and aggregate, or use histohour with larger limit
                url = f"https://min-api.cryptocompare.com/data/v2/histoday"
                params = {
                    'fsym': fsym,
                    'tsym': tsym,
                    'limit': min(limit * 7, 2000),  # Approximate weekly
                    'api_key': self.cryptocompare_api_key
                }
            else:
                # Default to hourly
                url = f"https://min-api.cryptocompare.com/data/v2/histohour"
                params = {
                    'fsym': fsym,
                    'tsym': tsym,
                    'limit': min(limit, 2000),
                    'api_key': self.cryptocompare_api_key
                }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('Response') == 'Error':
                self.logger.error(f"CryptoCompare market data error: {data.get('Message')}")
                return []
            
            raw_data = data.get('Data', {}).get('Data', [])
            
            # Convert to OHLCV format
            ohlcv_data = []
            for item in raw_data:
                timestamp = item.get('time')
                if timestamp is None:
                    continue
                    
                # CryptoCompare provides: open, high, low, close, volumefrom, volumeto
                # We'll use volumefrom (amount of cryptocurrency traded)
                ohlcv_data.append({
                    'timestamp': datetime.fromtimestamp(timestamp).isoformat(),
                    'open': item.get('open', 0),
                    'high': item.get('high', 0),
                    'low': item.get('low', 0),
                    'close': item.get('close', 0),
                    'volume': item.get('volumefrom', 0)
                })
            
            # Apply timeframe aggregation if needed
            if timeframe in ['4H', '1W']:
                ohlcv_data = self._aggregate_ohlcv(ohlcv_data, timeframe)
            
            # Limit to requested number (most recent first)
            return ohlcv_data[-limit:] if len(ohlcv_data) > limit else ohlcv_data
            
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol} from CryptoCompare: {e}")
            return []

    def _aggregate_ohlcv(self, ohlcv_data: List[Dict[str, Any]], timeframe: str) -> List[Dict[str, Any]]:
        """Aggregate OHLCV data to higher timeframes."""
        if not ohlcv_data or timeframe == '1H':
            return ohlcv_data
            
        if timeframe == '4H':
            # Aggregate every 4 hours
            aggregated = []
            for i in range(0, len(ohlcv_data), 4):
                batch = ohlcv_data[i:i+4]
                if len(batch) < 4:
                    continue  # Skip incomplete batches
                    
                # Calculate aggregated values
                open_price = batch[0]['open']
                close_price = batch[-1]['close']
                high_price = max(item['high'] for item in batch)
                low_price = min(item['low'] for item in batch)
                total_volume = sum(item['volume'] for item in batch)
                # Use timestamp of the last item in batch
                timestamp = batch[-1]['timestamp']
                
                aggregated.append({
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': total_volume
                })
            return aggregated
            
        elif timeframe == '1W':
            # Aggregate by week (simplified: every 7 days)
            aggregated = []
            for i in range(0, len(ohlcv_data), 7):
                batch = ohlcv_data[i:i+7]
                if len(batch) < 7:
                    continue
                    
                open_price = batch[0]['open']
                close_price = batch[-1]['close']
                high_price = max(item['high'] for item in batch)
                low_price = min(item['low'] for item in batch)
                total_volume = sum(item['volume'] for item in batch)
                timestamp = batch[-1]['timestamp']
                
                aggregated.append({
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': total_volume
                })
            return aggregated
            
        return ohlcv_data

    def _get_coingecko_market_data(self, symbol: str, limit: int = 100, timeframe: str = '1H') -> List[Dict[str, Any]]:
        """Fallback to get market data from CoinGecko"""
        try:
            # Convert symbol format (BTC/USD -> bitcoin)
            coin_id = self.coingecko_symbol_map.get(symbol, 
                                   symbol.lower().replace('/usd', '').replace('-usd', ''))
            
            # Map timeframe to CoinGecko days parameter
            days_map = {
                '1H': 1,   # Last 24 hours
                '4H': 2,   # Last 2 days
                '1D': 7,   # Last week
                '1W': 30   # Last month
            }
            days = days_map.get(timeframe, 1)
            
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': days,
                'interval': 'hourly' if days <= 1 else 'daily'
            }
            
            self._rate_limit()
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Convert to OHLCV format
            prices = data.get('prices', [])
            volumes = data.get('total_volumes', [])
            
            ohlcv_data = []
            for i in range(len(prices)):
                timestamp = prices[i][0]
                price = prices[i][1]
                volume = volumes[i][1] if i < len(volumes) else 0
                
                # For simplicity, using close price for all OHLC (would need more complex calculation for real OHLC)
                ohlcv_data.append({
                    'timestamp': datetime.fromtimestamp(timestamp/1000).isoformat(),
                    'open': price,
                    'high': price * 1.02,  # Estimated
                    'low': price * 0.98,   # Estimated
                    'close': price,
                    'volume': volume
                })
            
            # Limit to requested number
            return ohlcv_data[-limit:] if len(ohlcv_data) > limit else ohlcv_data
            
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol} from CoinGecko: {e}")
            return []