import pandas as pd
import numpy as np

def run_virtual_backtest(data_gold, data_silver):
    # Simulation of MasterMetalsEA logic
    equity = 10000
    position = 0
    trades = []
    
    for i in range(100, len(data_gold)):
        # Simplified regime and ATR spike check
        atr_gold = data_gold['atr'].iloc[i]
        atr_ma = data_gold['atr_ma'].iloc[i]
        
        if atr_gold > atr_ma * 1.12 and position == 0:
            # Enter Long
            position = 1
            entry_price = data_gold['close'].iloc[i]
            trades.append({'type': 'LONG', 'entry': entry_price, 'time': data_gold.index[i]})
            
        elif position == 1 and data_gold['close'].iloc[i] > entry_price * 1.02:
            # Exit with 2% profit
            equity += (data_gold['close'].iloc[i] - entry_price) * 10
            position = 0
            
    return equity, trades

print("Virtual Backtest Engine Initialized. Awaiting data...")
