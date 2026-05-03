import pandas as pd
import pandas_ta as ta
import numpy as np
import sys

# Setup paths
sys.path.insert(0, '/home/yahwehatwork/freqtrade/user_data/strategies')
from HyperScalperV3 import HyperScalperV3

# Mock data loader (sampling from actual freqtrade data if exists)
import os
data_path = '/home/yahwehatwork/freqtrade/user_data/data/binance/futures/BTC_USDT_USDT-5m-futures.feather' # Adjust to actual filename

def debug_indicators():
    if not os.path.exists(data_path):
        print(f"Data file not found at {data_path}")
        return

    # Load a sample of the data
    df = pd.read_feather(data_path)
    # Freqtrade data is usually structured; ensure it has high, low, close, volume
    
    # Dummy config for strategy initialization
    dummy_config = {'dry_run': True, 'stake_amount': 1.5}
    strategy = HyperScalperV3(config=dummy_config)
    df = strategy.populate_indicators(df, {})
    
    print("--- Indicator Stats ---")
    print(df[['atr', 'adx', 'sma20', 'sma50', 'rsi', 'atr_pct']].describe())
    print("\n--- NaN Counts ---")
    print(df[['atr', 'adx', 'sma20', 'sma50', 'rsi', 'atr_pct']].isna().sum())
    print("\n--- Sample of Signals ---")
    # check if any rows would trigger entry
    long_signals = (df['sma20'] > df['sma50']) & (df['rsi'] < 70) & (df['rsi'] > 30)
    print(f"Potential Longs (SMA+RSI): {long_signals.sum()}")

if __name__ == '__main__':
    debug_indicators()
