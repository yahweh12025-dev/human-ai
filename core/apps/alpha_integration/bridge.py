import json
import os
import requests
from signal_factory import get_ai_signal, save_signal

# Configuration for Freqtrade API
FREQTRADE_URL = os.getenv('FREQTRADE_URL', 'http://localhost:8080')
FREQTRADE_USERNAME = os.getenv('FREQTRADE_USERNAME')
FREQTRADE_PASSWORD = os.getenv('FREQTRADE_PASSWORD')

# Mapping from asset to Freqtrade pair
# Note: This is a placeholder. You must adjust based on what pairs are available in your Freqtrade setup.
ASSET_TO_PAIR = {
    "XAU": "XAU/USD",   # Gold/USD - might not be available; consider PAXG/USD or similar
    "XAG": "XAG/USD",   # Silver/USD
    "BTC": "BTC/USDT"   # Example for Bitcoin
}

def get_freqtrade_auth():
    """Return auth tuple for Freqtrade API."""
    return (FREQTRADE_USERNAME, FREQTRADE_PASSWORD)

def force_buy(pair):
    """Send a forcebuy signal to Freqtrade for the given pair."""
    url = f"{FREQTRADE_URL}/api/v1/forcebuy"
    payload = {
        "pair": pair,
        "price": None,  # Let Freqtrade use the current market price
        "stake_amount": None,  # Use default stake amount
        "leverage": None  # Use default leverage
    }
    try:
        response = requests.post(url, json=payload, auth=get_freqtrade_auth())
        response.raise_for_status()
        print(f"Forcebuy successful for {pair}: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error forcing buy for {pair}: {e}")
        return False

def main():
    # Get the AI signal
    signal = get_ai_signal()
    print("AI Signal:", json.dumps(signal, indent=2))
    
    # Save the signal for record
    save_signal(signal, "signal.json")
    
    # Process each asset in the signal
    for asset, action in signal.items():
        if asset == "timestamp":
            continue
        if action in ["strong_buy", "buy"]:
            pair = ASSET_TO_PAIR.get(asset)
            if pair:
                print(f"Received '{action}' for {asset}. Attempting to force buy {pair}.")
                force_buy(pair)
            else:
                print(f"No pair mapping for asset {asset}. Skipping.")
        else:
            print(f"Action for {asset} is '{action}'. No buy order placed.")

if __name__ == "__main__":
    main()
