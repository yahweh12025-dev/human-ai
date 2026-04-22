#!/usr/bin/env python3
"""
Simple performance analysis for the trading agent test.
Analyzes the logs to show basic performance metrics.
"""
import re
import os
from collections import defaultdict

def analyze_trading_log(log_file_path):
    """Analyze the trading agent log file."""
    if not os.path.exists(log_file_path):
        print(f"Log file not found: {log_file_path}")
        return
    
    with open(log_file_path, 'r') as f:
        lines = f.readlines()
    
    # Extract relevant information
    orders = []
    positions = []
    signals = []
    pnl_info = []
    
    for line in lines:
        # Look for order executions
        if 'Executing paper order:' in line:
            # Extract order info (simplified)
            orders.append(line.strip())
        # Look for opened positions
        elif 'Opened position for' in line:
            positions.append(line.strip())
        # Look for signals
        elif 'Generated signal for' in line and 'signal:' in line:
            signals.append(line.strip())
        # Look for PnL information
        elif 'Closed position for' in line and 'PnL:' in line:
            pnl_info.append(line.strip())
    
    print("=== Trading Agent Performance Analysis ===")
    print(f"Total order executions: {len(orders)}")
    print(f"Total positions opened: {len(positions)}")
    print(f"Total signals generated: {len(signals)}")
    print(f"Total positions closed: {len(pnl_info)}")
    
    if pnl_info:
        print("\n--- PnL Information ---")
        for pnl_line in pnl_info[-5:]:  # Show last 5 PnL entries
            print(pnl_line)
    
    print("\n--- Recent Activity ---")
    print("Last 5 orders:")
    for order in orders[-5:]:
        print(f"  {order}")
    
    print("\nLast 5 signals:")
    for signal in signals[-5:]:
        print(f"  {signal}")

if __name__ == "__main__":
    log_file = "/home/ubuntu/human-ai/agents/trading-agent/logs/trading_agent.log"
    analyze_trading_log(log_file)