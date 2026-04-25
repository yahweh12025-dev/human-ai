import alpaca_trade_api as tradeapi
import logging
import sys
import os
from dotenv import load_dotenv

# Load environment variables from the file we created
load_dotenv('/home/yahwehatwork/human-ai/human-ai.env')

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger('AlpacaEnvTest')

def test_alpaca_env():
    try:
        print('--- STARTING ALPACA ENV CONNECTION TEST ---')
        
        # Get keys from env
        api_key = os.getenv('ALPACA_API_KEY')
        api_secret = os.getenv('ALPACA_SECRET_KEY')
        base_url = os.getenv('ALPACA_ENDPOINT')
        
        if not all([api_key, api_secret, base_url]):
            print('❌ Missing environment variables in human-ai.env')
            return

        # Debug: Print the endpoint being used (without keys)
        print(f"Using Endpoint: {base_url}")

        # IMPORTANT: Alpaca REST class expects the base URL WITHOUT /v2 for some versions
        # Let's try removing /v2 if it's present
        cleaned_url = base_url.replace('/v2', '')
        
        api = tradeapi.REST(
            api_key,
            api_secret,
            base_url=cleaned_url
        )
        
        account = api.get_account()
        print(f'✅ Connection Successful!')
        print(f'Account Status: {account.status}')
        print(f'Account Cash: ${account.cash}')
        
        try:
            trade = api.get_latest_trade('BTC/USD')
            print(f'✅ Price Fetch Successful!')
            print(f'Latest BTC Price: ${trade.price}')
        except Exception as price_err:
            print(f'⚠️ Price fetch failed: {price_err}')
            
        print('--- TEST COMPLETE ---')
        
    except Exception as e:
        print(f'❌ Alpaca API Error: {e}')

if __name__ == '__main__':
    test_alpaca_env()
