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

# 1. Check Clock Drift
print("--- Clock Sync Check ---")
try:
    resp = requests.get('https://api.binance.com/api/v3/time', timeout=10)
    server_time = resp.json()['serverTime']
    local_time = int(time.time() * 1000)
    diff = abs(server_time - local_time)
    print(f"Server Time: {server_time}")
    print(f"Local Time:  {local_time}")
    print(f"Difference:  {diff}ms")
    if diff > 5000:
        print("❌ CLOCK DRIFT DETECTED: Your system time is out of sync.")
    else:
        print("✅ Clock is in sync.")
except Exception as e:
    print(f"Error checking time: {e}")

# 2. Test Spot Testnet Private Call
print("\n--- Spot Testnet Auth Check ---")
spot_url = 'https://testnet.binance.vision'
endpoint = '/api/v3/account'
params = {'timestamp': int(time.time() * 1000), 'recvWindow': 5000}
query_string = '&'.join(f'{k}={v}' for k, v in params.items())
signature = hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()
params['signature'] = signature
headers = {'X-MBX-APIKEY': api_key}

try:
    resp = requests.get(f'{spot_url}{endpoint}', params=params, headers=headers, timeout=10)
    print(f"Spot Response: {resp.status_code} - {resp.text}")
except Exception as e:
    print(f"Error: {e}")

# 3. Test Futures Demo Private Call
print("\n--- Futures Demo Auth Check ---")
fut_url = 'https://demo-fapi.binance.com'
endpoint_fut = '/fapi/v2/account'
params_fut = {'timestamp': int(time.time() * 1000), 'recvWindow': 5000}
query_string_fut = '&'.join(f'{k}={v}' for k, v in params_fut.items())
signature_fut = hmac.new(secret_key.encode(), query_string_fut.encode(), hashlib.sha256).hexdigest()
params_fut['signature'] = signature_fut

try:
    resp = requests.get(f'{fut_url}{endpoint_fut}', params=params_fut, headers=headers, timeout=10)
    print(f"Futures Response: {resp.status_code} - {resp.text}")
except Exception as e:
    print(f"Error: {e}")
