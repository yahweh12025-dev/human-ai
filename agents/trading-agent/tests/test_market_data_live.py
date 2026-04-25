import alpaca_trade_api as tradeapi
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger('AlpacaMarketTest')

def test_market_data():
    try:
        print('--- TESTING LIVE DATA ENDPOINT ---')
        # Try the Live Market Data endpoint instead of paper
        api = tradeapi.REST(
            'h9Dj9ohkgoROPYy8xzw219lxs82dD7MyMYt4qhobAOuGq0t649JLUQnGqeqZHHH9',
            'uJXGeCY1LwwppsGwZ2RMHU8g2gdE9QSW7ocLFTUsqHhwMAqSCzg5xIpCNmJiorD8',
            base_url='https://api.alpaca.markets' # Changed from paper-api to api
        )
        
        trade = api.get_latest_trade('BTC/USD')
        print(f'✅ SUCCESS: Live Market Data Fetched!')
        print(f'Latest BTC Truth Price: ${trade.price}')
        print('--- TEST COMPLETE ---')
        
    except Exception as e:
        print(f'❌ Live Endpoint Error: {e}')

if __name__ == '__main__':
    test_market_data()
