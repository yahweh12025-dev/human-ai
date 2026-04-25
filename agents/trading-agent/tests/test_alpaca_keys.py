import alpaca_trade_api as tradeapi
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger('AlpacaLiveTest')

def test_alpaca_trading_flow():
    # credentials from user images
    API_KEY = 'PKZARYKMOIN6AAA3TOBRCEZMCS'
    API_SECRET = 'BcJKxDaus4SdvMpoPJvnkhpNHnXeE'
    BASE_URL = 'https://paper-api.alpaca.markets'

    print("--- STARTING ALPACA TRADING API TEST ---")
    try:
        # 1. Test Connectivity & Authentication
        logger.info(f"Connecting to {BASE_URL}...")
        api = tradeapi.REST(API_KEY, API_SECRET, base_url=BASE_URL)
        
        account = api.get_account()
        print(f"✅ SUCCESS: Connected to Alpaca Paper Account")
        print(f"   Account Status: {account.status}")
        print(f"   Buying Power: ${account.buying_power}")
        print(f"   Equity: ${account.equity}")

        # 2. Test Order Placement (Paper Trading)
        print("\nAttempting small test order (1 share of SPY)...")
        order = api.submit_order(
            symbol='SPY',
            qty=1,
            side='buy',
            type='market',
            time_in_force='gtc'
        )
        print(f"✅ SUCCESS: Order Submitted! ID: {order.id}")
        print(f"   Order Status: {order.status}")

    except Exception as e:
        print(f"❌ FAILURE: {e}")
        # Provide detailed debugging info
        if "unauthorized" in str(e).lower():
            print("\nDEBUG: Error is 'Unauthorized'. This means the API Key/Secret is incorrect for this endpoint.")
        elif "connection refused" in str(e).lower():
            print("\nDEBUG: Connection refused. Check if the Base URL is correct or if there is a network block.")

if __name__ == '__main__':
    test_alpaca_trading_flow()
