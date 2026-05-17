#!/usr/bin/env python3
"""
Integrate GUI-Based Market Data Parser with VAB Core Logic for live data ingestion
Connects the GUI market data parser to the VAB core for real-time trading signal generation
"""

import sys
import time
import logging
import threading
import queue
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import numpy as np
import pandas as pd

# Import the GUI parser and VAB core
try:
    from data.parsers.binance_web_scraper import MarketDataParserGUI
except ImportError:
    # Fallback for different import paths
    try:
        from data.parsers.binance_web_scraper import MarketDataParserGUI
    except ImportError:
        MarketDataParserGUI = None
        logging.warning("Could not import MarketDataParserGUI")

try:
    from agents.trading_agent.strategies.binance.vab_logic import VABCore
except ImportError:
    # Fallback for different import paths
    try:
        from strategies.binance.vab_logic import VABCore
    except ImportError:
        VABCore = None
        logging.warning("Could not import VABCore")

logger = logging.getLogger(__name__)

class MarketDataIngestionEngine:
    """
    Integrates GUI-based market data parsing with VAB core logic
    Provides live data ingestion pipeline from GUI parser to trading signals
    """
    
    def __init__(self, 
                 gui_update_callback: Optional[Callable] = None,
                 signal_callback: Optional[Callable] = None,
                 update_interval: float = 1.0):
        """
        Initialize the data ingestion engine
        
        Args:
            gui_update_callback: Function to call when GUI needs updating
            signal_callback: Function to call when trading signals are generated
            update_interval: Seconds between data updates
        """
        self.gui_update_callback = gui_update_callback
        self.signal_callback = signal_callback
        self.update_interval = update_interval
        
        # Initialize components
        self.gui_parser = None
        self.vab_core = VABCore(volume_threshold=2.0, lookback_period=20) if VABCore else None
        
        # Data queues
        self.data_queue = queue.Queue(maxsize=100)
        self.signal_queue = queue.Queue(maxsize=50)
        
        # Control flags
        self.is_running = False
        self.gui_thread = None
        self.processing_thread = None
        
        # Data storage for technical analysis
        self.price_history = []  # List of {'timestamp': datetime, 'price': float, 'volume': float}
        self.max_history_length = 1000
        
        logger.info("MarketDataIngestionEngine initialized")
    
    def start(self):
        """Start the data ingestion engine"""
        if self.is_running:
            logger.warning("Ingestion engine already running")
            return
        
        if not self.vab_core:
            logger.error("VAB Core not available - cannot start ingestion engine")
            return
        
        self.is_running = True
        
        # Start GUI parser thread if available
        if MarketDataParserGUI:
            self.gui_thread = threading.Thread(target=self._run_gui_parser, daemon=True)
            self.gui_thread.start()
            logger.info("GUI parser thread started")
        else:
            logger.warning("GUI Parser not available - running in headless mode")
            # In headless mode, we'd connect to actual APIs instead
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._process_data_loop, daemon=True)
        self.processing_thread.start()
        logger.info("Data processing thread started")
        
        logger.info("MarketDataIngestionEngine started")
    
    def stop(self):
        """Stop the data ingestion engine"""
        logger.info("Stopping MarketDataIngestionEngine...")
        self.is_running = False
        
        # Wait for threads to finish (with timeout)
        if self.gui_thread and self.gui_thread.is_alive():
            self.gui_thread.join(timeout=5.0)
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
        
        logger.info("MarketDataIngestionEngine stopped")
    
    def _run_gui_parser(self):
        """Run the GUI market data parser in a separate thread"""
        try:
            # This would normally create and run the Tkinter GUI
            # For now, we'll simulate GUI data generation
            logger.info("Starting GUI market data parser simulation...")
            
            # Simulate GUI-generated data
            symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'SOL/USDT']
            base_prices = {'BTC/USDT': 65000, 'ETH/USDT': 3200, 'ADA/USDT': 0.45, 'SOL/USDT': 95}
            
            iteration = 0
            while self.is_running:
                try:
                    # Simulate market data update for each symbol
                    for symbol in symbols:
                        # Generate realistic price movement
                        base_price = base_prices[symbol]
                        # Add some random walk behavior
                        price_change = np.random.normal(0, base_price * 0.001)  # 0.1% volatility
                        volume = np.random.uniform(100, 1000)  # Random volume
                        
                        # Create market data point
                        market_data = {
                            'symbol': symbol,
                            'timestamp': datetime.now(),
                            'price': base_price + price_change,
                            'volume': volume,
                            'bid': base_price + price_change - np.random.uniform(0, 10),
                            'ask': base_price + price_change + np.random.uniform(0, 10)
                        }
                        
                        # Add to queue for processing
                        try:
                            self.data_queue.put_nowait(market_data)
                        except queue.Full:
                            # Remove oldest item if queue is full
                            try:
                                self.data_queue.get_nowait()
                                self.data_queue.put_nowait(market_data)
                            except queue.Empty:
                                pass
                        
                        # Update GUI if callback provided
                        if self.gui_update_callback:
                            try:
                                self.gui_update_callback(market_data)
                            except Exception as e:
                                logger.debug(f"GUI update callback error: {e}")
                    
                    # Sleep to maintain update interval
                    time.sleep(self.update_interval)
                    iteration += 1
                    
                except Exception as e:
                    logger.error(f"Error in GUI parser loop: {e}")
                    time.sleep(1.0)  # Brief pause before retrying
                    
        except Exception as e:
            logger.error(f"Failed to run GUI parser: {e}")
        finally:
            logger.info("GUI parser thread terminated")
    
    def _process_data_loop(self):
        """Main data processing loop that generates trading signals"""
        logger.info("Starting data processing loop...")
        
        while self.is_running:
            try:
                # Get market data from queue (with timeout to allow checking is_running)
                try:
                    market_data = self.data_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Store in price history for technical analysis
                self.price_history.append({
                    'timestamp': market_data['timestamp'],
                    'price': market_data['price'],
                    'volume': market_data['volume']
                })
                
                # Maintain history length
                if len(self.price_history) > self.max_history_length:
                    self.price_history.pop(0)
                
                # Convert to DataFrame for VAB analysis
                if len(self.price_history) >= self.vab_core.lookback_period if self.vab_core else 5:
                    df_data = []
                    for item in self.price_history[-self.vab_core.lookback_period:]:
                        df_data.append({
                            'close': item['price'],
                            'volume': item['volume']
                        })
                    
                    df = pd.DataFrame(df_data)
                    
                    # Generate VAB signals if we have enough data
                    if self.vab_core and len(df) >= self.vab_core.lookback_period:
                        try:
                            # Calculate volume signals
                            df_with_signals = self.vab_core.calculate_volume_signals(df)
                            
                            # Get trading signals
                            signals = self.vab_core.get_trading_signals(df_with_signals)
                            
                            # Process each signal
                            for signal in signals:
                                # Enhance signal with market data context
                                enhanced_signal = {
                                    **signal,
                                    'symbol': market_data['symbol'],
                                    'timestamp': market_data['timestamp'].isoformat(),
                                    'price': market_data['price'],
                                    'volume': market_data['volume']
                                }
                                
                                # Add to signal queue
                                try:
                                    self.signal_queue.put_nowait(enhanced_signal)
                                except queue.Full:
                                    # Remove oldest signal if queue is full
                                    try:
                                        self.signal_queue.get_nowait()
                                        self.signal_queue.put_nowait(enhanced_signal)
                                    except queue.Empty:
                                        pass
                                
                                # Call signal callback if provided
                                if self.signal_callback:
                                    try:
                                        self.signal_callback(enhanced_signal)
                                    except Exception as e:
                                        logger.debug(f"Signal callback error: {e}")
                                        
                        except Exception as e:
                            logger.debug(f"VAB processing error: {e}")
                
            except Exception as e:
                if self.is_running:  # Only log if we're supposed to be running
                    logger.error(f"Error in data processing loop: {e}")
                time.sleep(0.1)  # Brief pause on error
        
        logger.info("Data processing loop terminated")
    
    def get_latest_signal(self, timeout: float = 0.1) -> Optional[Dict]:
        """
        Get the latest trading signal from the queue
        
        Args:
            timeout: Seconds to wait for a signal
            
        Returns:
            Signal dictionary or None if no signal available
        """
        try:
            return self.signal_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_recent_signals(self, count: int = 10) -> List[Dict]:
        """
        Get recent trading signals from the queue
        
        Args:
            count: Number of signals to retrieve
            
        Returns:
            List of signal dictionaries
        """
        signals = []
        temp_signals = []
        
        # Extract signals from queue without emptying it completely
        for _ in range(min(count, self.signal_queue.qsize())):
            try:
                signal = self.signal_queue.get_nowait()
                signals.append(signal)
                temp_signals.append(signal)
            except queue.Empty:
                break
        
        # Put signals back in queue
        for signal in temp_signals:
            try:
                self.signal_queue.put_nowait(signal)
            except queue.Full:
                break  # Queue is full, stop putting back
        
        return list(reversed(signals))  # Return in chronological order
    
    def get_market_data_history(self, count: int = 100) -> List[Dict]:
        """
        Get recent market data history
        
        Args:
            count: Number of data points to retrieve
            
        Returns:
            List of market data dictionaries
        """
        return list(reversed(self.price_history[-count:])) if self.price_history else []
    
    def get_status(self) -> Dict:
        """Get current status of the ingestion engine"""
        return {
            'is_running': self.is_running,
            'gui_parser_available': MarketDataParserGUI is not None,
            'vab_core_available': self.vab_core is not None,
            'data_queue_size': self.data_queue.qsize(),
            'signal_queue_size': self.signal_queue.qsize(),
            'price_history_length': len(self.price_history),
            'last_update': datetime.now().isoformat() if self.price_history else None
        }

# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    def gui_update_callback(data):
        print(f"GUI Update: {data['symbol']} @ ${data['price']:.2f} (Vol: {data['volume']:.0f})")
    
    def signal_callback(signal):
        print(f"TRADING SIGNAL: {signal['signal']} {signal['symbol']} @ ${signal['price']:.2f} - {signal['reason']}")
    
    # Create and start the ingestion engine
    engine = MarketDataIngestionEngine(
        gui_update_callback=gui_update_callback,
        signal_callback=signal_callback,
        update_interval=0.5  # Update twice per second for demo
    )
    
    try:
        print("Starting Market Data Ingestion Engine...")
        engine.start()
        
        # Run for a demo period
        print("Engine running for 10 seconds...")
        time.sleep(10)
        
        # Show some statistics
        status = engine.get_status()
        print(f"Engine Status: {status}")
        
        # Show recent signals
        signals = engine.get_recent_signals(count=5)
        if signals:
            print(f"\nRecent Signals ({len(signals)}):")
            for signal in signals:
                print(f"  {signal['signal']} {signal['symbol']} - {signal['reason']}")
        else:
            print("\nNo signals generated yet (need more data)")
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        engine.stop()
        print("Market Data Ingestion Engine stopped.")