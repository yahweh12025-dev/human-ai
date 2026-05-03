import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt

def main():
    trades_path = 'results/trades.csv'
    equity_path = 'results/equity_curve.csv'
    
    if not os.path.exists(trades_path) or not os.path.exists(equity_path):
        print("Error: Results files not found.")
        return

    trades = pd.read_csv(trades_path)
    equity = pd.read_csv(equity_path)
    
    # 1. OVERALL SUMMARY
    start_bal = 1.0
    end_bal = equity['active_balance'].iloc[-1] + equity['vault_balance'].iloc[-1]
    net_return = ((end_bal - start_bal) / start_bal) * 100
    
    total_trades = len(trades)
    win_rate = (trades['net_pnl'] > 0).mean() * 100 if total_trades > 0 else 0
    
    wins = trades[trades['net_pnl'] > 0]['net_pnl'].sum()
    losses = abs(trades[trades['net_pnl'] < 0]['net_pnl'].sum())
    profit_factor = wins / losses if losses > 0 else float('inf')
    
    print("=== OVERALL SUMMARY ===")
    print(f"Starting Balance: ${start_bal:.2f}")
    print(f"Ending Balance: ${end_bal:.2f}")
    print(f"Net Return: {net_return:.2f}%")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Profit Factor: {profit_factor:.2f}")
    print("-" * 30)
    
    # 2. REGIME BREAKDOWN
    if total_trades > 0:
        regime_stats = trades.groupby('regime').agg({
            'net_pnl': ['count', 'mean', lambda x: (x > 0).mean() * 100]
        })
        regime_stats.columns = ['Trades', 'Avg PnL', 'Win Rate %']
        print("\n=== REGIME BREAKDOWN ===")
        print(regime_stats)
    
    # 3. VAULT PERFORMANCE
    total_vaulted = equity['vault_balance'].iloc[-1]
    print("\n=== VAULT PERFORMANCE ===")
    print(f"Final Vault Balance: ${total_vaulted:.2f}")
    
    # 4. RED FLAGS
    print("\n=== RED FLAGS ===")
    if win_rate < 54: print("🚩 Win Rate below 54%")
    if profit_factor < 1.3: print("🚩 Profit Factor below 1.3")
    
if __name__ == "__main__":
    main()
