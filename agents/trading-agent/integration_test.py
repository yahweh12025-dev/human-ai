#!/usr/bin/env python3
"""
Integration test for the trading agent with mock data.
"""
import sys
import os
import time
import threading
from unittest.mock import patch

# Add the agent directory to the path
sys.path.insert(0, '/home/ubuntu/human-ai/agents/trading-agent')

def test_agent_with_mock_data():
    """Test the agent with mock data for a few iterations."""
    from trading_agent import TradingAgent
    
    # Create a custom agent class that overrides the run method to limit iterations
    class TestTradingAgent(TradingAgent):
        def __init__(self):
            # Initialize with default config
            super().__init__('config.yaml')
            # Override to use mock data and shorter intervals
            self.config['data']['use_mock_data'] = True
            self.config['data']['fetch_interval'] = 2  # 2 seconds for testing
            self.config['data']['history_length'] = 30  # Shorter history for faster indicator calc
            
        def run(self):
            """Run the agent for a limited number of iterations."""
            self.logger.info("Starting test trading agent main loop")
            iterations = 0
            max_iterations = 5  # Run for 5 cycles
            
            try:
                while iterations < max_iterations:
                    for symbol in self.symbols:
                        self._process_symbol(symbol)
                    iterations += 1
                    self.logger.info(f"Completed iteration {iterations}/{max_iterations}")
                    if iterations < max_iterations:
                        time.sleep(self.config['data']['fetch_interval'])
            except KeyboardInterrupt:
                self.logger.info("Test trading agent stopped by user")
            except Exception as e:
                self.logger.exception(f"Unexpected error in test main loop: {e}")
                raise
            finally:
                self.logger.info("Test trading agent main loop finished")
    
    # Run the test
    print("Creating test trading agent...")
    agent = TestTradingAgent()
    print("Starting test run (5 iterations)...")
    agent.run()
    print("Test completed successfully!")

if __name__ == "__main__":
    test_agent_with_mock_data()