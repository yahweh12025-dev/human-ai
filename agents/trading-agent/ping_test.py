import requests
try:
    resp = requests.get('https://testnet.binance.vision/api/v3/ping', timeout=10)
    print(f"Ping Response: {resp.status_code}")
except Exception as e:
    print(f"Error: {e}")
