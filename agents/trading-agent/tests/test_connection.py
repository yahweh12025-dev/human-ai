import logging
import sys
from data.fetcher import DataFetcher

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger('ConnectivityTest')

config = {
    'provider': 'binance',
    'history_length': 200,
    'timeframe': '1h',
    'proxies': {
        'http': 'http://127.0.0.1:40000',
        'https': 'http://127.0.0.1:40000'
    }
}

def test_connection():
    try:
        print("--- STARTING LIVE BINANCE TESTNET CONNECTION CHECK ---")
        fetcher = DataFetcher(config)
        print("Attempting to fetch LIVE data for BTC/USDT...")
        data = fetcher.fetch_latest_data('BTC/USDT')
        if data is not None:
            print(f"✅ SUCCESS: Live data fetched!")
            print(f"Current Live Price: ${data['Close'].iloc[-1]:.2f}")
        else:
            print("❌ FAILURE: No data returned from API.")
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")

if __name__ == '__main__':
    test_connection()
