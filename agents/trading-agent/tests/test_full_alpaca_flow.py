import alpaca_trade_api as tradeapi
import logging
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/home/yahwehatwork/human-ai/human-ai.env')

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger('AlpacaIntegrationTest')

def test_integration():
    try:
        print('--- STARTING ALPACA TRADING AGENT INTEGRATION TEST ---')
        
        api_key = os.getenv('ALPACA_API_KEY')
        api_secret = os.getenv('ALPACA_SECRET_KEY')
        base_url = os.getenv('ALPACA_ENDPOINT')
        
        if not all([api_key, api_secret, base_url]):
            print('❌ Missing environment variables in human-ai.env')
            return

        # Clean URL for the SDK
        cleaned_url = base_url.replace('/v2', '')
        
        api = tradeapi.REST(api_key, api_secret, base_url=cleaned_url)
        
        # 1. Verify Account
        account = api.get_account()
        print(f'✅ Account Verified: Status {account.status}, Cash ${account.cash}')

        # 2. Try a small market order (Paper)
        # Using SPY as it is a highly liquid asset usually available on all paper accounts
        print('Attempting to buy 1 share of SPY...')
        order = api.submit_order(
            symbol='SPY',
            qty=1,
            side='buy',
            type='market',
            time_in_force='gtc'
        )
        print(f'✅ Order Submitted! ID: {order.id}, Status: {order.status}')

        # 3. Immediately cancel or sell to clean up
        print('Cleaning up: Cancelling or selling the test order...')
        # Check if it filled
        order_status = api.get_order(order.id)
        if order_status.status == 'filled':
            api.submit_order(
                symbol='SPY',
                qty=1,
                side='sell',
                type='market',
                time_in_force='gtc'
            )
            print('✅ Successfully sold the test share.')
        else:
            api.cancel_order(order.id)
            print('✅ Successfully cancelled the pending order.')

        print('--- INTEGRATION TEST COMPLETE: SUCCESS ---')
        
    except Exception as e:
        print(f'❌ Integration Error: {e}')

if __name__ == '__main__':
    test_integration()
