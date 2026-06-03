import requests
try:
    resp = requests.get('https://demo-fapi.binance.com/fapi/v1/ticker/price?symbol=BTCUSDT', timeout=10)
    print(f"Public Endpoint Response: {resp.status_code}")
    print(f"Data: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
