"""
Market Intelligence Module
Fetches live crypto news, calculates sentiment, and ranks assets for dynamic trading.
"""
import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MarketIntel:
    """
    Analyzes market news and data to influence trading decisions.
    """
    def __init__(self):
        self.news_api_url = "https://newsapi.org/v2/everything"
        # Using a generic crypto query; in production, use specific API keys
        self.params = {
            'q': 'cryptocurrency OR bitcoin OR ethereum OR altcoin',
            'language': 'en',
            'sortBy': 'publishedAt',
            'pageSize': 10
        }

    def fetch_crypto_news(self):
        """
        Fetch the latest cryptocurrency news headlines.
        Returns a list of articles.
        """
        try:
            # Attempt to fetch news (may fail without API key, fallback to mock)
            response = requests.get(self.news_api_url, params=self.params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('articles', [])
            else:
                logger.warning("News API unavailable, using synthetic market events.")
                return self._generate_synthetic_news()
        except Exception as e:
            logger.error(f"News fetch error: {e}, using synthetic data.")
            return self._generate_synthetic_news()

    def _generate_synthetic_news(self):
        """
        Generates synthetic news for testing the agent's reaction logic.
        """
        now = datetime.utcnow()
        return [
            {
                'title': 'Major BTC ETF Approval Expected This Week',
                'description': 'Analysts predict a surge in Bitcoin price following regulatory approval.',
                'publishedAt': now.isoformat(),
                'source': {'name': 'CryptoAlert'}
            },
            {
                'title': 'Ethereum Network Upgrade Reduces Gas Fees by 40%',
                'description': 'ETH scalability improvement boosts DeFi activity.',
                'publishedAt': (now - timedelta(minutes=30)).isoformat(),
                'source': {'name': 'BlockTech'}
            }
        ]

    def calculate_sentiment(self, articles):
        """
        Simple keyword-based sentiment analysis for crypto news.
        Returns a dict of {symbol: sentiment_score}.
        """
        sentiment_scores = {'BTC/USDT': 0, 'ETH/USDT': 0, 'SOL/USDT': 0, 'XRP/USDT': 0}
        
        positive_keywords = ['upgrade', 'approval', 'surge', 'bullish', 'rally', 'adoption', 'boost']
        negative_keywords = ['hack', 'ban', 'crash', 'bearish', 'regulation', 'drop', 'fraud']

        for article in articles:
            text = (article['title'] + " " + article.get('description', '')).lower()
            
            # Check for BTC mentions
            if 'bitcoin' in text or 'btc' in text:
                score = sum(1 for w in positive_keywords if w in text) - sum(1 for w in negative_keywords if w in text)
                sentiment_scores['BTC/USDT'] += score
            
            # Check for ETH mentions
            if 'ethereum' in text or 'eth' in text:
                score = sum(1 for w in positive_keywords if w in text) - sum(1 for w in negative_keywords if w in text)
                sentiment_scores['ETH/USDT'] += score

        return sentiment_scores

    def get_priority_symbol(self, sentiment_scores):
        """
        Selects the symbol with the highest positive sentiment score.
        Default to BTC if all scores are neutral.
        """
        # Filter for only positive scores
        positive = {k: v for k, v in sentiment_scores.items() if v > 0}
        if positive:
            # Return the symbol with the highest score
            return max(positive, key=positive.get)
        else:
            return 'BTC/USDT' # Default anchor