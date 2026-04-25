#!/usr/bin/env python3
"""
Test script to run the trading agent for a short period.
"""
import sys
import os
import time
import threading
from trading_agent import TradingAgent

def run_agent_for_duration(duration_seconds):
    """Run the agent for a specified duration."""
    agent = TradingAgent()
    # Override the fetch interval to be shorter for testing
    agent.config['data']['fetch_interval'] = 5  # 5 seconds
    print(f"Starting test run for {duration_seconds} seconds...")
    print("Press Ctrl+C to stop early")
    
    # We'll run the agent in a separate thread so we can timeout it
    def agent_loop():
        try:
            agent.run()
        except KeyboardInterrupt:
            print("\nAgent stopped by user")
        except Exception as e:
            print(f"\nAgent error: {e}")
            import traceback
            traceback.print_exc()
    
    thread = threading.Thread(target=agent_loop, daemon=True)
    thread.start()
    
    # Wait for the specified duration or until thread finishes
    thread.join(timeout=duration_seconds)
    
    if thread.is_alive():
        print(f"\nTest duration ({duration_seconds}s) reached. Stopping agent...")
        # In a real scenario, we'd have a proper shutdown mechanism
        # For now, we'll just exit - the daemon thread will be killed
        print("Test completed.")
    else:
        print("\nAgent finished before timeout.")

if __name__ == "__main__":
    # Run for 30 seconds by default, but allow override from command line
    duration = 30
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print("Usage: python test_run.py [duration_seconds]")
            sys.exit(1)
    
    run_agent_for_duration(duration)