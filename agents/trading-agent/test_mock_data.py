
import sys
import os
import time
import threading
sys.path.insert(0, '.')

# Import and create agent with test config
from trading_agent import TradingAgent

def run_agent():
    # Create a minimal config in memory for testing
    class MockConfig:
        def __init__(self):
            self.data = {
                'default_symbols': ['BTC-USD', 'ETH-USD', 'AAPL'],
                'fetch_interval': 3,
                'history_length': 30,
                'provider': 'yfinance',
                'use_mock_data': True
            }
            self.strategy = {
                'sma_crossover': {
                    'fast_period': 5,
                    'slow_period': 15,
                    'rsi_period': 10,
                    'rsi_overbought': 70,
                    'rsi_oversold': 30
                }
            }
            self.execution = {
                'broker': 'paper',
                'order_size_percent': 10,
                'slippage_tolerance': 0.001
            }
            self.risk = {
                'max_risk_per_trade': 2.0,
                'max_open_positions': 5,
                'stop_loss_percent': 5.0,
                'take_profit_percent': 15.0,
                'max_daily_loss_percent': 10.0
            }
            self.general = {
                'agent_name': 'trading_agent',
                'log_level': 'INFO',
                'timezone': 'UTC',
                'paper_trading': True
            }
            self.notifications = {
                'telegram': {
                    'enabled': False,
                    'bot_token': '',
                    'chat_id': ''
                }
            }
    
    # Create agent with our mock config
    agent = TradingAgent.__new__(TradingAgent)
    agent.config = MockConfig().__dict__
    agent.logger = agent._setup_logging()
    from data.fetcher import DataFetcher
    from strategies.sma_crossover import SMACrossover
    from execution.paper_trader import PaperTrader
    from risk.manager import RiskManager
    
    agent.data_fetcher = DataFetcher(agent.config['data'])
    agent.strategy = SMACrossover(agent.config['strategy']['sma_crossover'])
    agent.executor = PaperTrader(agent.config['execution'])
    agent.risk_manager = RiskManager(agent.config['risk'])
    agent.symbols = agent.config['data']['default_symbols']
    
    print("Agent created with mock data config")
    print(f"Data fetcher use_mock_data: {agent.data_fetcher.use_mock_data}")
    
    # Test fetching data for one symbol
    data = agent.data_fetcher.fetch_latest_data('BTC-USD')
    if data is not None:
        print(f"Successfully fetched mock data for BTC-USD: {len(data)} rows")
        print(f"Columns: {list(data.columns)}")
        print(f"First few close prices: {data['Close'].head().tolist()}")
    else:
        print("Failed to fetch mock data")
    
    # Test strategy signal generation
    if data is not None and len(data) > 0:
        signal = agent.strategy.generate_signal(data)
        print(f"Generated signal for BTC-USD: {signal}")
    
    print("Mock data test completed successfully!")

try:
    run_agent()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
