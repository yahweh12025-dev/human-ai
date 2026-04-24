from dotenv import load_dotenv
load_dotenv()

"""
Trading Agent Main Module

This module contains the main trading agent class that orchestrates data fetching,
signal generation, order execution, and risk management.
"""
import time
import yaml
import logging
import os
from pathlib import Path
from data.fetcher import DataFetcher
from strategies.grid import GridStrategy
from execution.paper_trader import PaperTrader
from risk.manager import RiskManager
from controller import TradingController, ensure_bridge_dir
from market_intel import MarketIntel

class TradingAgent:
    def __init__(self, config_path='config.yaml'):
        """Initialize the trading agent with configuration."""
        self.config = self._load_config(config_path)
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        # Override data settings from environment variables
        data_config = self.config.get('data', {})
        data_config['provider'] = os.getenv('DATA_PROVIDER', data_config.get('provider', 'binance'))
        data_config['history_length'] = int(os.getenv('DATA_HISTORY_LENGTH', data_config.get('history_length', 200)))
        data_config['timeframe'] = os.getenv('TIMEFRAME', data_config.get('timeframe', '1h'))
        data_config['use_mock_data'] = os.getenv('USE_MOCK_DATA', str(data_config.get('use_mock_data', False))).lower() == 'true'
        self.config['data'] = data_config
        
        # Initialize components
        self.data_fetcher = DataFetcher(self.config['data'])
        self.strategy = GridStrategy(self.config['futures']['grid'])
        self.executor = PaperTrader(self.config['execution'])
        self.risk_manager = RiskManager(self.config['risk'])
        
        self.symbols = self.config['futures']['default_symbols']
        self.controller = TradingController()
        self.paused = False
        ensure_bridge_dir()
        self.logger.info(f"Trading Agent initialized for symbols: {self.symbols}")

    def _load_config(self, config_path):
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config

    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = self.config['general']['log_level']
        log_file = os.path.join(os.path.dirname(__file__), 'logs', 'trading_agent.log')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

    def run(self):
        """Main trading loop with synchronous controller integration."""
        self.logger.info("Starting trading agent main loop")
        try:
            while True:
                # Poll for commands from the bridge (synchronous)
                cmd = self.controller.check_for_commands()
                if cmd:
                    self.controller.apply_command(self, cmd)

                if self.paused:
                    self.logger.info("Trading paused. Waiting for resume command...")
                    time.sleep(self.config['data']['fetch_interval'] * 2)
                    continue

                for symbol in self.symbols:
                    self._process_symbol(symbol)
                
                # Wait for the next iteration
                time.sleep(self.config['data']['fetch_interval'])
        except KeyboardInterrupt:
            self.logger.info("Trading agent stopped by user")
        except Exception as e:
            self.logger.exception(f"Unexpected error in main loop: {e}")
            raise

    def _process_symbol(self, symbol):
        """Process a single symbol: fetch data, check exits, generate signal, execute trade."""
        self.logger.debug(f"Processing symbol: {symbol}")
        try:
            # Fetch latest data
            data = self.data_fetcher.fetch_latest_data(symbol)
            if data is None or len(data) < 2:
                self.logger.warning(f"Insufficient data for {symbol}")
                return
            # Generate trading signal
            signal = self.strategy.generate_signal(data)

            # Update risk manager with latest data (for portfolio value, etc.)
            self.risk_manager.update_portfolio(data, symbol)

            # Check exit conditions for existing positions
            current_price = data['Close'].iloc[-1]
            exit_signal = self.risk_manager.check_exit_conditions(symbol, current_price)
            if exit_signal != 0:
                self.logger.info(f"Exit signal for {symbol}: {exit_signal}")
                # Create a closing order
                order = self.executor.create_order(symbol, exit_signal, data)
                if order:
                    # Let risk manager calculate the quantity for closing
                    if symbol in self.risk_manager.open_positions:
                        pos = self.risk_manager.open_positions[symbol]
                        order['quantity'] = pos['quantity']  # Close the full position
                    self.executor.execute_order(order)
                    # Update risk manager (this will close the position and update PnL)
                    self.risk_manager.close_position(symbol, order['filled_price'])
                # We don't return here; we continue to see if a new entry is immediately possible
            else:
                # If order creation failed, we still might want to try entering later
                pass
            
            # Check if we can enter a new position
            # This is only relevant if we're not currently in a position
            if symbol not in self.risk_manager.open_positions:
                # Proceed to signal generation
                pass
            else:
                return # Already in a position, skip entry signal


            # Check if we can trade based on risk limits
            if not self.risk_manager.can_trade(symbol):
                self.logger.debug(f"Risk limits prevent trading {symbol}")
                return

            # Execute trade based on signal
            if signal != 0:  # 0 means hold
                order = self.executor.create_order(symbol, signal, data)
                if order:
                    # Let risk manager calculate position size
                    if symbol in self.risk_manager.open_positions:
                        # We shouldn't be here if can_trade returned True, but double-check
                        self.logger.warning(f"Attempting to open position in {symbol} while already open")
                        return
                    
                    # For simplicity, we'll use a fixed percentage of equity for now
                    # In a more advanced version, we'd calculate based on volatility, etc.
                    # The risk manager's calculate_position_size needs entry and stop loss
                    # We'll use a simplified approach: risk per trade % of equity, with stop loss at risk%
                    entry_price = data['Close'].iloc[-1]
                    if signal == 1:  # long
                        stop_loss_price = entry_price * (1 - self.risk_manager.stop_loss_percent / 100)
                    else:  # short
                        stop_loss_price = entry_price * (1 + self.risk_manager.stop_loss_percent / 100)
                    
                    quantity = self.risk_manager.calculate_position_size(symbol, entry_price, stop_loss_price)
                    if quantity <= 0:
                        self.logger.warning(f"Calculated quantity is zero or negative for {symbol}")
                        return
                    
                    order['quantity'] = quantity
                    self.logger.info(f"Executing order for {symbol}: {order}")
                    # In a real agent, we would send the order to the broker here
                    # For paper trader, it simulates and updates internal state
                    self.executor.execute_order(order)
                    # Update risk manager with the new position
                    self.risk_manager.update_position(order)
                else:
                    self.logger.debug(f"No order created for {symbol} with signal {signal}")
            else:
                self.logger.debug(f"Hold signal for {symbol}")

        except Exception as e:
            self.logger.exception(f"Error processing symbol {symbol}: {e}")

if __name__ == "__main__":
    agent = TradingAgent()
    agent.run()