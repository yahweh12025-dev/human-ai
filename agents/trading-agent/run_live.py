#!/usr/bin/env python3
import argparse
import os
from trading_agent import TradingAgent

def main():
    parser = argparse.ArgumentParser(description="Live Trading Agent Runtime")
    parser.add_argument('--test-safety', action='store_true', help="Simulate failure and verify kill-switch")
    args = parser.parse_args()

    agent = TradingAgent()
    
    if args.test_safety:
        print("[SAFETY-TEST] Simulating critical failure...")
        # Force a failure state in the risk manager
        agent.risk_manager.current_equity = 0.5 * agent.risk_manager.initial_equity 
        # Trigger health check
        if not agent.health_check():
            print("[SAFETY-TEST] Heartbeat failure detected!")
        
        # Verify kill-switch logic
        if agent.risk_manager.check_kill_switch():
            print("[SAFETY-TEST] SUCCESS: Kill-switch triggered correctly.")
        else:
            print("[SAFETY-TEST] FAILURE: Kill-switch did not trigger.")
        return

    # Normal execution loop
    agent.run_live()

if __name__ == "__main__":
    main()
