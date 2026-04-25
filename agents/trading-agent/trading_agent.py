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
from researcher_agent import ResearcherAgent

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
        self.market_intel = MarketIntel()
        self.researcher = ResearcherAgent(self.config)
        self.paused = False
        self.last_market_intel_update = 0
        self.market_intel_interval = 300  # Update market intel every 5 minutes
        self.sentiment_scores = {}
        ensure_bridge_dir()
        self.logger.info(f"Trading Agent initialized for symbols: {self.symbols}")

    def _load_config(self, config_path):
        """Load configuration from YAML file."""
        # Use absolute path to ensure the file is found regardless of where the script is run from
        absolute_config_path = os.path.join(os.path.dirname(__file__), config_path)
        with open(absolute_config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config

    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = self.config['general']['log_level']
        log_file = os.path.join(os.path.dirname(__file__), 'logs', 'trading_agent.log')
        # Simplified logging to avoid conflicts with nohup/wrappers
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file)
            ]
        )

    def run(self):
        """Main trading loop with synchronous controller integration."""
        self.logger.info("Starting trading agent main loop")
        try:
            while True:
                # Poll for commands from the bridge
                cmd = self.controller.check_for_commands()
                if cmd:
                    self.controller.apply_command(self, cmd)

                # HARD STOP: Termination at target profit of $1,000,000 (10x starting equity of $100,000)
                if self.risk_manager.current_equity >= 1000000.0:
                    self.logger.info(f"🎯 ULTIMATE TARGET REACHED: Equity ${self.risk_manager.current_equity:.2f}. Terminating for total profit protection.")
                    self.generate_final_report()
                    break

                if self.paused:
                    self.logger.info("Trading paused. Waiting for resume command...")
                    time.sleep(self.config['data']['fetch_interval'] * 2)
                    continue

                # Update market intelligence periodically
                current_time = time.time()
                if current_time - self.last_market_intel_update > self.market_intel_interval:
                    self.logger.info("Updating market intelligence...")
                    self.update_market_intelligence()
                    self.last_market_intel_update = current_time

                for symbol in self.symbols:
                    self._process_symbol(symbol)
                
                time.sleep(self.config['data']['fetch_interval'])
        except KeyboardInterrupt:
            self.logger.info("Trading agent stopped by user")
        except Exception as e:
            self.logger.exception(f"Unexpected error in main loop: {e}")
            raise

    def generate_final_report(self):
        """Generate a final report of the trading session."""
        self.logger.info("Generating final report...")
        self.logger.info(f"Starting Equity: ${self.risk_manager.starting_equity:.2f}")
        self.logger.info(f"Final Equity: ${self.risk_manager.current_equity:.2f}")
        self.logger.info(f"Total PnL: ${self.risk_manager.current_equity - self.risk_manager.starting_equity:.2f}")
        self.logger.info(f"Return: {((self.risk_manager.current_equity / self.risk_manager.starting_equity) - 1) * 100:.2f}%")
        self.logger.info(f"Total Trades: {len(self.risk_manager.trade_history)}")
        if self.risk_manager.trade_history:
            wins = sum(1 for t in self.risk_manager.trade_history if t.get('pnl', 0) > 0)
            losses = sum(1 for t in self.risk_manager.trade_history if t.get('pnl', 0) < 0)
            win_rate = (wins / len(self.risk_manager.trade_history)) * 100 if self.risk_manager.trade_history else 0
            self.logger.info(f"Win Rate: {win_rate:.2f}% ({wins}W/{losses}L)")
        self.logger.info("Report complete.")

    def update_market_intelligence(self):
        """Fetch and process market intelligence to influence trading decisions."""
        try:
            articles = self.market_intel.fetch_crypto_news()
            if articles:
                self.sentiment_scores = self.market_intel.calculate_sentiment(articles)
                priority_symbol = self.market_intel.get_priority_symbol(self.sentiment_scores)
                self.logger.info(f"Market Intel Update: Sentiment={self.sentiment_scores}, Priority={priority_symbol}")
                
                # Optional: Adjust trading based on sentiment
                # For example, we could increase position size for high-confidence symbols
                # or temporarily avoid symbols with extremely negative sentiment
            else:
                self.logger.warning("No market intelligence articles fetched")
        except Exception as e:
            self.logger.error(f"Failed to update market intelligence: {e}")

    def _process_symbol(self, symbol):
        """Process a single symbol: fetch data, check exits, generate signal, execute trade."""
        self.logger.debug(f"Processing symbol: {symbol}")
        try:
            # Fetch latest data
            data = self.data_fetcher.fetch_latest_data(symbol)
            if data is None or len(data) < 2:
                self.logger.warning(f"Insufficient data for {symbol}")
                return
            
            # Update risk manager with latest data
            self.risk_manager.update_portfolio(data, symbol)
            current_price = data['Close'].iloc[-1]

            # Generate trading signal
            signal = self.strategy.generate_signal(data)
            self.logger.info(f"DEBUG: Signal for {symbol}: {signal}")

            # Check exit conditions for existing positions
            exit_signal = self.risk_manager.check_exit_conditions(symbol, current_price)
            if exit_signal != 0:
                self.logger.info(f"Exit signal for {symbol}: {exit_signal}")
                order = self.executor.create_order(symbol, exit_signal, data)
                if order:
                    if symbol in self.risk_manager.open_positions:
                        pos = self.risk_manager.open_positions[symbol]
                        order['quantity'] = pos['quantity']
                self.executor.execute_order(order)
                if order.get('status') == 'filled':
                    self.risk_manager.close_position(symbol, order['filled_price'])
                else:
                    self.logger.warning(f"Exit order for {symbol} failed: {order.get('error', 'Unknown error')}")
                # Return after closing to avoid logic conflicts in this loop
                return

            # ENTRY LOGIC: Only try to enter if not already in a position
            if symbol not in self.risk_manager.open_positions:
                if not self.risk_manager.can_trade(symbol):
                    self.logger.debug(f"Risk limits prevent trading {symbol}")
                    return

                if signal != 0:
                    self.logger.info(f"ATTEMPTING TRADE for {symbol}: Signal {signal}")
                    order = self.executor.create_order(symbol, signal, data)
                    if order:
                        entry_price = data['Close'].iloc[-1]
                        if signal == 1:  # long
                            stop_loss_price = entry_price * (1 - self.risk_manager.stop_loss_percent / 100)
                        else:  # short
                            stop_loss_price = entry_price * (1 + self.risk_manager.stop_loss_percent / 100)
                        
                        quantity = self.risk_manager.calculate_position_size(symbol, entry_price, stop_loss_price)
                        self.logger.info(f"Calculated quantity for {symbol}: {quantity}")
                        
                        if quantity <= 0:
                            self.logger.warning(f"Calculated quantity invalid")
                            return
                        
                        # Set the quantity on the order before execution
                        order['quantity'] = quantity
                        self.executor.execute_order(order)
                        if order and order.get('status') == 'filled':
                            self.risk_manager.update_position(order)
                            self.logger.info(f"SUCCESSFULLY EXECUTED order for {symbol}")
                        else:
                            self.logger.warning(f"Order for {symbol} was not filled: {order.get('status') if order else 'None'}")
                    else:
                        self.logger.warning(f"executor.create_order returned None for {symbol}")
            else:
                self.logger.debug(f"Already in position for {symbol}")

        except Exception as e:
            self.logger.exception(f"Error processing symbol {symbol}: {e}")

if __name__ == "__main__":
    agent = TradingAgent()
    agent.run()
