import json
import datetime
import numpy as np
from typing import List, Dict, Any

def generate_daily_sentiment():
    """
    Aggregates mock sentiment data from crypto news feeds.
    In a real system, this would call APIs like CryptoPanic or LunarCrush.
    """
    assets = ["BTC", "ETH", "SOL", "BNB", "XRP"]
    daily_state = {
        "date": datetime.datetime.now().isoformat(),
        "global_sentiment": np.random.uniform(-1, 1),
        "asset_sentiment": {
            asset: {
                "score": np.random.uniform(-1, 1),
                "volume": np.random.randint(1000, 100000),
                "trend": np.random.choice(["bullish", "bearish", "neutral"])
            } for asset in assets
        }
    }
    return daily_state

if __name__ == "__main__":
    state = generate_daily_sentiment()
    with open("data/sentiment/daily_sentiment.json", "w") as f:
        json.dump(state, f, indent=2)
    print("Daily sentiment state updated.")
