"""
Trading Agent Main Module

This module contains the main trading agent class that orchestrates data fetching,
signal generation, order execution, and risk management.
"""
import time
import yaml
import logging
from pathlib import Path
from data.fetcher import DataFetcher
from strategies.sma_crossover import SMACrossover
from execution.paper_trader import PaperTrader
from risk.manager import RiskManager

class TradingAgent:
    def __init__(self, config_path='config.yaml'):
        """Initialize the trading agent with configuration."""
        self.config = self._load_config(config_path)
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.data_fetcher = DataFetcher(self.config['data'])
        self.strategy = SMACrossover(self.config['strategy']['sma_crossover'])
        self.executor = PaperTrader(self.config['execution'])
        self.risk_manager = RiskManager(self.config['risk'])
        
        self.symbols = self.config['data']['default_symbols']
        self.logger.info(f"Trading Agent initialized for symbols: {self.symbols}")

    def _load_config(self, config_path):
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config

    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = self.config['general']['log_level']
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("logs/trading_agent.log"),
                logging.StreamHandler()
            ]
        )

    def run(self):
        """Main trading loop."""
        self.logger.info("Starting trading agent main loop")
        try:
            while True:
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
                return  # Don't open new positions if we're closing

            # Generate trading signal for new entries
            signal = self.strategy.generate_signal(data)
            self.logger.debug(f"Signal for {symbol}: {signal}")

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