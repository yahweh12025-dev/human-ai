import alpaca_trade_api as tradeapi
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger('AlpacaMarketTest')

def test_market_data():
    try:
        print('--- STARTING ALPACA MARKET DATA TEST ---')
        # Using the Market Data API keys
        api = tradeapi.REST(
            'h9Dj9ohkgoROPYy8xzw219lxs82dD7MyMYt4qhobAOuGq0t649JLUQnGqeqZHHH9',
            'uJXGeCY1LwwppsGwZ2RMHU8g2gdE9QSW7ocLFTUsqHhwMAqSCzg5xIpCNmJiorD8',
            base_url='https://paper-api.alpaca.markets'
        )
        
        # Test 1: Get Latest Trade (This should work with Market Data keys)
        trade = api.get_latest_trade('BTC/USD')
        print(f'✅ Market Data Fetch Successful!')
        print(f'Live BTC Truth Price: ${trade.price}')
        print('--- TEST COMPLETE ---')
        
    except Exception as e:
        print(f'❌ Market Data Error: {e}')

if __name__ == '__main__':
    test_market_data()
