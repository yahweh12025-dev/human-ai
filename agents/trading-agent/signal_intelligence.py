import requests
import time
import json
import os
import numpy as np
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv('/home/yahwehatwork/human-ai/.env')
COINGECKO_KEY = os.getenv('COINGECKO_API_KEY', '')
CRYPTOCOMPARE_KEY = os.getenv('CRYPTOCOMPARE_API_KEY', '')

# ── CoinGecko Signals ──────────────────────────────────────────────────────────

def get_btc_sentiment():
    try:
        r = requests.get(
            'https://api.coingecko.com/api/v3/coins/bitcoin',
            params={'localization': False, 'sparkline': False},
            headers={'x-cg-demo-api-key': COINGECKO_KEY} if COINGECKO_KEY else {},
            timeout=10
        )
        data = r.json()['market_data']
        sentiment_up = data.get('sentiment_votes_up_percentage', 50)
        change_24h = data.get('price_change_percentage_24h', 0)
        change_1h = data.get('price_change_percentage_1h_in_currency', {}).get('usd', 0)

        if change_24h < -5 or change_1h < -2:
            market_state = 'EXTREME_FEAR'
        elif change_24h > 5 or change_1h > 2:
            market_state = 'EXTREME_GREED'
        else:
            market_state = 'NEUTRAL'

        return {
            'sentiment_up_pct': sentiment_up,
            'change_24h': change_24h,
            'change_1h': change_1h,
            'market_state': market_state,
            'long_bias': sentiment_up > 60 and market_state != 'EXTREME_FEAR',
            'short_bias': sentiment_up < 40 and market_state != 'EXTREME_GREED',
            'halt_trading': market_state == 'EXTREME_FEAR' and change_24h < -8
        }
    except Exception as e:
        return {'sentiment_up_pct': 50, 'market_state': 'UNKNOWN', 'long_bias': False, 'short_bias': False, 'halt_trading': False, 'error': str(e)}

def get_btc_dominance():
    try:
        r = requests.get('https://api.coingecko.com/api/v3/global', timeout=10)
        btc_dom = r.json()['data']['market_cap_percentage']['btc']
        return {'btc_dominance': btc_dom, 'risk_on': btc_dom < 55, 'risk_off': btc_dom > 60}
    except Exception as e:
        return {'btc_dominance': 55, 'risk_on': True, 'risk_off': False, 'error': str(e)}

def get_trending_coins():
    try:
        r = requests.get('https://api.coingecko.com/api/v3/search/trending', timeout=10)
        trending = [c['item']['symbol'].upper() for c in r.json()['coins']]
        btc_trending = 'BTC' in trending
        return {'trending': trending, 'btc_trending': btc_trending, 'position_multiplier': 1.0 if btc_trending else 0.7}
    except Exception as e:
        return {'trending': [], 'btc_trending': False, 'position_multiplier': 0.7, 'error': str(e)}

# ── CryptoCompare Signals ──────────────────────────────────────────────────────

def get_order_book_delta():
    try:
        headers = {'authorization': f'Apikey {CRYPTOCOMPARE_KEY}'} if CRYPTOCOMPARE_KEY else {}
        r = requests.get(
            'https://min-api.cryptocompare.com/data/v2/ob/l2/snapshot',
            params={'market': 'binance', 'instrument': 'BTC-USDT'},
            headers=headers,
            timeout=10
        )
        data = r.json().get('Data', {})
        bids = data.get('bids', [])
        asks = data.get('asks', [])

        if not bids or not asks:
            return {'delta': 0, 'signal': 'NEUTRAL', 'weight': 0}

        bid_vol = sum(float(b[1]) for b in bids[:10])
        ask_vol = sum(float(a[1]) for a in asks[:10])
        delta = (bid_vol - ask_vol) / (bid_vol + ask_vol)

        signal = 'STRONG_BUY' if delta > 0.3 else 'BUY' if delta > 0.1 else 'STRONG_SELL' if delta < -0.3 else 'SELL' if delta < -0.1 else 'NEUTRAL'
        return {'delta': delta, 'signal': signal, 'bid_volume': bid_vol, 'ask_volume': ask_vol, 'weight': 2}
    except Exception as e:
        return {'delta': 0, 'signal': 'NEUTRAL', 'weight': 0, 'error': str(e)}

def get_news_sentiment():
    try:
        headers = {'authorization': f'Apikey {CRYPTOCOMPARE_KEY}'} if CRYPTOCOMPARE_KEY else {}
        r = requests.get(
            'https://min-api.cryptocompare.com/data/v2/news/',
            params={'categories': 'BTC,Blockchain', 'sortOrder': 'latest', 'limit': 10},
            headers=headers,
            timeout=10
        )
        articles = r.json().get('Data', [])[:10]
        titles = [a['title'] for a in articles]

        bullish_words = ['surge', 'rally', 'bull', 'pump', 'breakout', 'high', 'gain', 'rise', 'adoption', 'ETF', 'institutional']
        bearish_words = ['crash', 'dump', 'bear', 'drop', 'fall', 'ban', 'hack', 'sell', 'fear', 'regulation', 'liquidation']

        bull_count = sum(1 for t in titles for w in bullish_words if w.lower() in t.lower())
        bear_count = sum(1 for t in titles for w in bearish_words if w.lower() in t.lower())

        score = (bull_count - bear_count) / max(len(titles), 1)
        signal = 'BULLISH' if score > 0.3 else 'BEARISH' if score < -0.3 else 'NEUTRAL'
        return {'score': score, 'signal': signal, 'bull_count': bull_count, 'bear_count': bear_count, 'titles': titles[:3]}
    except Exception as e:
        return {'score': 0, 'signal': 'NEUTRAL', 'error': str(e)}

# ── Binance Funding Rate ───────────────────────────────────────────────────────

def get_funding_rate():
    try:
        r = requests.get(
            'https://fapi.binance.com/fapi/v1/fundingRate',
            params={'symbol': 'BTCUSDT', 'limit': 3},
            timeout=10
        )
        rates = r.json()
        latest_rate = float(rates[-1]['fundingRate'])
        avg_rate = np.mean([float(r['fundingRate']) for r in rates])

        signal = 'BEARISH' if latest_rate > 0.0005 else 'BULLISH' if latest_rate < -0.0001 else 'NEUTRAL'
        extreme = abs(latest_rate) > 0.001
        return {
            'latest_rate': latest_rate,
            'avg_rate': avg_rate,
            'signal': signal,
            'extreme': extreme,
            'weight': 2,
            'halt_longs': latest_rate > 0.001,
            'halt_shorts': latest_rate < -0.001
        }
    except Exception as e:
        return {'latest_rate': 0, 'signal': 'NEUTRAL', 'extreme': False, 'weight': 2, 'halt_longs': False, 'halt_shorts': False, 'error': str(e)}

def is_funding_blackout():
    now = datetime.now(timezone.utc)
    minutes = now.hour * 60 + now.minute
    funding_windows = [0, 480, 960] # 00:00, 08:00, 16:00 UTC in minutes
    for fw in funding_windows:
        if fw - 10 <= minutes <= fw + 5:
            return True
    return False

# ── Master Signal Aggregator ───────────────────────────────────────────────────

def get_master_signal():
    if is_funding_blackout():
        return {'action': 'HALT', 'reason': 'FUNDING_BLACKOUT', 'score': 0, 'position_multiplier': 0}

    sentiment = get_btc_sentiment()
    dominance = get_btc_dominance()
    trending = get_trending_coins()
    order_book = get_order_book_delta()
    news = get_news_sentiment()
    funding = get_funding_rate()

    if sentiment.get('halt_trading'):
        return {'action': 'HALT', 'reason': 'EXTREME_MARKET_FEAR', 'score': 0, 'position_multiplier': 0}

    score = 0
    direction = 0

    if order_book['signal'] in ['STRONG_BUY', 'BUY']:
        score += order_book['weight']
        direction += 1
    elif order_book['signal'] in ['STRONG_SELL', 'SELL']:
        score += order_book['weight']
        direction -= 1

    if funding['signal'] == 'BULLISH':
        score += funding['weight']
        direction += 1
    elif funding['signal'] == 'BEARISH':
        score += funding['weight']
        direction -= 1

    if sentiment.get('long_bias'):
        score += 1
        direction += 1
    elif sentiment.get('short_bias'):
        score += 1
        direction -= 1

    if news['signal'] == 'BULLISH':
        score += 1
        direction += 1
    elif news['signal'] == 'BEARISH':
        score += 1
        direction -= 1

    pos_multiplier = trending['position_multiplier'] * (0.8 if dominance['risk_off'] else 1.0)

    if funding.get('halt_longs') and direction > 0:
        return {'action': 'HALT', 'reason': 'EXTREME_FUNDING_LONG', 'score': score, 'position_multiplier': 0}
    if funding.get('halt_shorts') and direction < 0:
        return {'action': 'HALT', 'reason': 'EXTREME_FUNDING_SHORT', 'score': score, 'position_multiplier': 0}

    action = 'LONG' if direction > 0 and score >= 3 else 'SHORT' if direction < 0 and score >= 3 else 'WEAK_LONG' if direction > 0 and score == 2 else 'WEAK_SHORT' if direction < 0 and score == 2 else 'NEUTRAL'

    return {
        'action': action,
        'score': score,
        'direction': direction,
        'position_multiplier': pos_multiplier,
        'full_size': score >= 5,
        'half_size': score in [3, 4],
        'quarter_size': score == 2,
        'components': {
            'sentiment': sentiment['market_state'],
            'order_book': order_book['signal'],
            'funding': funding['signal'],
            'news': news['signal'],
            'btc_trending': trending['btc_trending'],
            'risk_on': dominance['risk_on']
        }
    }

if __name__ == '__main__':
    print(json.dumps(get_master_signal(), indent=2))
