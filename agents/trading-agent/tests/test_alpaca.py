import alpaca_trade_api as tradeapi
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger('AlpacaTest')

def test_alpaca():
    try:
        print('--- STARTING ALPACA API CONNECTION TEST ---')
        api = tradeapi.REST(
            'h9Dj9ohkgoROPYy8xzw219lxs82dD7MyMYt4qhobAOuGq0t649JLUQnGqeqZHHH9',
            'uJXGeCY1LwwppsGwZ2RMHU8g2gdE9QSW7ocLFTUsqHhwMAqSCzg5xIpCNmJiorD8',
            base_url='https://paper-api.alpaca.markets'
        )
        
        account = api.get_account()
        print(f'✅ Connection Successful!')
        print(f'Account Status: {account.status}')
        print(f'Account Cash: ${account.cash}')
        
        trade = api.get_latest_trade('BTC/USD')
        print(f'✅ Price Fetch Successful!')
        print(f'Latest BTC Truth Price: ${trade.price}')
        print('--- TEST COMPLETE ---')
        
    except Exception as e:
        print(f'❌ Alpaca API Error: {e}')

if __name__ == '__main__':
    test_alpaca()
