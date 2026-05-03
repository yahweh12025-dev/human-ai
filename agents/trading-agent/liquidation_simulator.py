import pandas as pd
import numpy as np
import os

def main():
    data_path = '/home/yahwehatwork/human-ai/agents/trading-agent/data/btc_5m_ohlcv.csv'
    output_path = '/home/yahwehatwork/human-ai/agents/trading-agent/data/synthetic_liq_clusters.csv'
    
    if not os.path.exists(data_path):
        print("Error: OHLCV data not found.")
        return

    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Parameters
    lookback = 20
    
    # Arrays to store the simulation
    long_liq_levels = []
    short_liq_levels = []
    long_liq_strengths = []
    short_liq_strengths = []
    
    # We simulate "liquidation zones" by finding swing points and attributing 
    # strength to volume spikes at those points.
    
    # Initialize lists
    near_long = [np.nan] * len(df)
    near_short = [np.nan] * len(df)
    long_str = [0.0] * len(df)
    short_str = [0.0] * len(df)
    
    # Simple swing identification
    for i in range(lookback, len(df)):
        window = df.iloc[i-lookback:i]
        
        # Local Low (Long Liquidation Cluster)
        if df.iloc[i]['low'] == window['low'].min():
            # Place a cluster below the low
            level = df.iloc[i]['low'] * 0.995 # 0.5% below
            strength = (df.iloc[i]['volume'] / df['volume'].mean()) * 10
            long_liq_levels.append((df.iloc[i]['timestamp'], level, strength))
            
        # Local High (Short Liquidation Cluster)
        if df.iloc[i]['high'] == window['high'].max():
            # Place a cluster above the high
            level = df.iloc[i]['high'] * 1.005 # 0.5% above
            strength = (df.iloc[i]['volume'] / df['volume'].mean()) * 10
            short_liq_levels.append((df.iloc[i]['timestamp'], level, strength))
            
    # Now, for every candle, find the nearest active cluster
    # (In a real scenario, clusters persist until hit; here we simulate a 48h decay)
    for i in range(len(df)):
        ts = df.iloc[i]['timestamp']
        price = df.iloc[i]['close']
        
        # Filter for clusters that appeared before now and haven't decayed
        valid_longs = [l for l in long_liq_levels if l[0] <= ts and (ts - l[0]).total_seconds() < 172800]
        valid_shorts = [s for s in short_liq_levels if s[0] <= ts and (ts - s[0]).total_seconds() < 172800]
        
        if valid_longs:
            # Find nearest cluster below price
            below = [l for l in valid_longs if l[1] < price]
            if below:
                best = min(below, key=lambda x: abs(price - x[1]))
                near_long[i] = best[1]
                long_str[i] = min(100, best[2])
                
        if valid_shorts:
            # Find nearest cluster above price
            above = [s for s in valid_shorts if s[1] > price]
            if above:
                best = min(above, key=lambda x: abs(price - x[1]))
                near_short[i] = best[1]
                short_str[i] = min(100, best[2])

    # Save result
    res_df = pd.DataFrame({
        'timestamp': df['timestamp'],
        'nearest_long_liq_level': near_long,
        'nearest_short_liq_level': near_short,
        'long_liq_strength': long_str,
        'short_liq_strength': short_str
    })
    
    res_df.to_csv(output_path, index=False)
    print(f"Synthetic Liquidation Clusters saved to {output_path}")

if __name__ == "__main__":
    main()
