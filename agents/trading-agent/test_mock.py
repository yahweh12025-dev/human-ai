
import sys
import os
import time
import threading
sys.path.insert(0, '.')

# Import and create agent with test config
from trading_agent import TradingAgent

def run_agent():
    agent = TradingAgent(config_path='test_config.yaml')
    agent.config['data']['fetch_interval'] = 3  # Even faster for test
    print("Starting agent with mock data...")
    try:
        agent.run()
    except KeyboardInterrupt:
        print("\nAgent stopped by user")
    except Exception as e:
        print(f"\nAgent error: {e}")
        import traceback
        traceback.print_exc()

thread = threading.Thread(target=run_agent, daemon=True)
thread.start()
thread.join(timeout=15)  # Run for 15 seconds
if thread.is_alive():
    print("\nTest duration reached.")
else:
    print("\nAgent finished early.")
