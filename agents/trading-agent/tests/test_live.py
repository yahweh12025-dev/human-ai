#!/usr/bin/env python3
"""
Live test against Binance testnet with provided API keys.
Runs one cycle only for verification.
"""
import sys
import os
import time
from trading_agent import TradingAgent

def main():
    print("="*50)
    print("LIVE BINANCE TESTNET VERIFICATION")
    print("="*50)

    # Initialize agent with live testnet config
    print("\n1. Initializing TradingAgent with Binance testnet keys...")
    agent = TradingAgent()
    print("   Agent initialized successfully.")

    # Test connection
    print("\n2. Testing connection to Binance testnet...")
    try:
        # Attempt to fetch data for one symbol
        data = agent.data_fetcher.fetch_latest_data("BTC/USDT")
        if data is not None and len(data) > 0:
            print(f"   SUCCESS: Fetched {len(data)} candles for BTC/USDT")
            print(f"   Latest close price: ${data['Close'].iloc[-1]:.2f}")
        else:
            print("   FAILURE: No data returned from testnet")
            return
    except Exception as e:
        print(f"   ERROR: Connection test failed: {e}")
        return

    # Run one full cycle
    print("\n3. Executing ONE full trading cycle (synchronous)...")
    print("   This will check for override commands, then process symbols...")
    try:
        # Manually run one iteration of the agent's logic
        for symbol in agent.symbols:
            print(f"   Processing {symbol}...")
            agent._process_symbol(symbol)
            print(f"   Completed processing for {symbol}")
    except KeyboardInterrupt:
        print("\n   Cycle interrupted by user")
        return
    except Exception as e:
        print(f"   ERROR during processing: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "="*50)
    print("LIVE TESTNET CYCLE COMPLETE")
    print("="*50)
    print("Check the agent logs for detailed execution.")
    print("Use Ctrl+C to stop if running in a loop (not active here).")

if __name__ == "__main__":
    main()