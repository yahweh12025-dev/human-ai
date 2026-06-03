import requests
import hmac
import hashlib
import time
import os
from pathlib import Path
from dotenv import load_dotenv

# Setup
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)
api_key = os.getenv('BINANCE_TESTNET_API_KEY')
secret_key = os.getenv('BINANCE_TESTNET_SECRET_KEY')

print("Testing Alternative Futures Endpoint: testnet.binancefuture.com")

endpoint = '/fapi/v2/account'
params = {'timestamp': int(time.time() * 1000), 'recvWindow': 5000}
query_string = '&'.join(f'{k}={v}' for k, v in params.items())
signature = hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()
params['signature'] = signature
headers = {'X-MBX-APIKEY': api_key}

try:
    resp = requests.get('https://testnet.binancefuture.com' + endpoint, params=params, headers=headers, timeout=10)
    print(f"Response: {resp.status_code} - {resp.text}")
except Exception as e:
    print(f"Error: {e}")
