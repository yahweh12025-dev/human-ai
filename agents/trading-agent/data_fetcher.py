import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import time

def fetch_klines(symbol, interval, start_time, end_time, is_spot=False):
    # Use spot API if requested to bypass futures gaps
    base_url = "https://api.binance.com/api/v3/klines" if is_spot else "https://fapi.binance.com/fapi/v1/klines"
    all_klines = []
    current_start = start_time
    while current_start < end_time:
        params = {"symbol": symbol, "interval": interval, "startTime": current_start, "limit": 1500}
        try:
            response = requests.get(base_url, params=params, timeout=10)
            data = response.json()
            if not data or not isinstance(data, list): 
                print(f"API Error or empty data at {current_start}: {data}")
                break
            all_klines.extend(data)
            current_start = data[-1][0] + 1
            time.sleep(0.1)
        except Exception as e:
            print(f"Request failed: {e}")
            break
    return all_klines

def main():
    os.makedirs('/home/yahwehatwork/human-ai/agents/trading-agent/data', exist_ok=True)
    symbol, interval = "BTCUSDT", "5m"
    
    # TARGET: Bridge the gap from April 2025 to April 2026
    # The session export noted that futures API was failing for April 2026
    # We use is_spot=True for the later window
    ranges = [
        ("2024-01-01", "2025-04-01", False), # Historical’s’
        ("2025-04-01", "2026-04-30", True),  # THE GAP: Using Spot API
    ]
    
    all_df = []
    for start, end, use_spot in ranges:
        s_ts = int(datetime.strptime(start, "%Y-%m-%d").timestamp() * 1000)
        e_ts = int(datetime.strptime(end, "%Y-%m-%d").timestamp() * 1000)
        print(f"Fetching {start} to {end} (Spot={use_spot})...")
        klines = fetch_klines(symbol, interval, s_ts, e_ts, is_spot=use_spot)
        if not klines:
            print(f"No data found for {start} to {end}")
            continue
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
        all_df.append(df)
    
    if not all_df:
        print("Failed to fetch any data.")
        return

    final_df = pd.concat(all_df).drop_duplicates(subset=['timestamp']).sort_values('timestamp')
    final_df = final_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    final_df['timestamp'] = pd.to_datetime(final_df['timestamp'], unit='ms')
    final_df.to_csv('/home/yahwehatwork/human-ai/agents/trading-agent/data/btc_5m_ohlcv.csv', index=False)
    
    # Funding Rate Alignment (Still synthetic since Spot doesn't have funding)
    funding_data = []
    start_date, end_date = final_df['timestamp'].min(), final_df['timestamp'].max()
    curr = start_date
    while curr <= end_date:
        funding_data.append([curr, np.random.uniform(-0.0001, 0.0003)])
        curr += timedelta(hours=8)
    funding_df = pd.DataFrame(funding_data, columns=['timestamp', 'funding_rate'])
    funding_df['timestamp'] = pd.to_datetime(funding_df['timestamp'])
    funding_df.to_csv('/home/yahwehatwork/human-ai/agents/trading-agent/data/btc_funding_rates.csv', index=False)
    
    print(f"Summary: {len(final_df)} candles, Range: {start_date} to {end_date}")

if __name__ == "__main__":
    main()
