import logging
import time
from typing import Dict, Any, Optional, Tuple

class TradingAgent:
    def __init__(self, enable_market_intel=True):
        """Initialize the Trading Agent and its core components."""
        self.logger = logging.getLogger(__name__)
        
        # Core Components
        # NOTE: These imports are local to __init__ to prevent circular dependency errors
        # when this file is loaded by other scripts (like run_live.py).
        from data_fetcher import DataFetcher
        from risk_manager import RiskManager
        from signal_intelligence import SignalIntelligence
        from market_intel import MarketIntelligence
        from execution.paper_trader import PaperTrader
        from trading_strategy import TradingStrategy

        self.data_fetcher = DataFetcher()
        self.risk_manager = RiskManager()
        self.signal_intelligence = SignalIntelligence()
        self.market_intel = MarketIntelligence()
        self.executor = PaperTrader()
        self.strategy = TradingStrategy()
        
        # Circuit Breaker Configuration
        self.circuit_breaker_enabled = True
        self.circuit_breaker_thresholds = {
            'consecutive_losses': 5,      # Halt after 5 consecutive losses
            'daily_loss_limit': 0.10,     # Halt after 10% daily loss
            'drawdown_limit': 0.15,       # Halt after 15% drawdown from peak
            'volatility_spike': 3.0       # Halt if volatility exceeds 3x normal
        }
        self.circuit_breaker_state = {
            'is_tripped': False,
            'trip_reason': None,
            'trip_time': None,
            'consecutive_losses': 0,
            'daily_pnl': 0.0,
            'peak_equity': 0.0,
            'current_equity': 0.0,
            'volatility_measure': 0.0
        }
        
        # Configuration
        self.enable_market_intel = enable_market_intel
        self.latest_market_intel = {
            "articles": [],
            "sentiment_scores": {},
            "priority_symbol": None,
            "timestamp": 0
        }
        self.sentiment_scores = {}

    def health_check(self):
        """Perform a system health check. Returns True if healthy, False otherwise."""
        try:
            # Attempt to load markets as a basic connectivity test
            # Note: PaperTrader creates a binance instance
            self.executor.binance.load_markets()
            return True
        except Exception as e:
            self.logger.error(f"Health Check Failed: {e}")
            return False

    def run(self, symbols=["BTC/USDT", "ETH/USDT"]):
        """Main execution loop."""
        while True:
            # Check circuit breaker before processing
            if not self._is_trading_allowed():
                self.logger.warning(f"Trading halted by circuit breaker: {self.circuit_breaker_state['trip_reason']}")
                # Still sleep to avoid spamming logs
                time.sleep(60)
                continue
                
            self.update_market_intelligence()
            for symbol in symbols:
                self._process_symbol(symbol)
            time.sleep(60) # Run every 60 seconds

    def update_market_intelligence(self):
        """Fetch and process market intelligence to influence trading decisions."""
        try:
            articles = self.market_intel.fetch_crypto_news()
            if articles:
                self.sentiment_scores = self.market_intel.calculate_sentiment(articles)
                priority_symbol = self.market_intel.get_priority_symbol(self.sentiment_scores)
                self.logger.info(f"Market Intel Update: Sentiment={self.sentiment_scores}, Priority={priority_symbol}")
                
                self.latest_market_intel = {
                    'articles': articles,
                    'sentiment_scores': self.sentiment_scores,
                    'priority_symbol': priority_symbol,
                    'timestamp': time.time()
                }
            else:
                self.latest_market_intel = {
                    'articles': [],
                    'sentiment_scores': {},
                    'priority_symbol': None,
                    'timestamp': time.time()
                }
        except Exception as e:
            self.logger.error(f"Failed to update market intelligence: {e}")
            self.latest_market_intel = {
                'articles': [],
                'sentiment_scores': {},
                'priority_symbol': None,
                'timestamp': time.time()
            }

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

            # Apply market intelligence adjustment to signal
            intel_adjusted_signal = self._apply_market_intelligence_filter(symbol, signal)
            if intel_adjusted_signal != signal:
                self.logger.info(f"Market intelligence adjusted {symbol} signal from {signal} to {intel_adjusted_signal}")
                signal = intel_adjusted_signal

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
                if order and order.get('status') == 'filled':
                    self.risk_manager.close_position(symbol, order['filled_price'])
                else:
                    self.logger.warning(f"Exit order for {symbol} failed: {order.get('error', 'Unknown error')}")
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
                        
            # Check circuit breaker before executing trade
            if not self._is_trading_allowed():
                self.logger.warning(f"Trade blocked by circuit breaker for {symbol}: {self.circuit_breaker_state['trip_reason']}")
                return
            
            # Apply market intelligence position sizing adjustment
            adjusted_quantity = self._apply_market_intelligence_sizing(symbol, quantity)
            if adjusted_quantity != quantity:
                self.logger.info(f"Market intelligence adjusted {symbol} quantity from {quantity} to {adjusted_quantity}")
                quantity = adjusted_quantity
            
            # Set the quantity on the order before execution
            order['quantity'] = quantity
            self.executor.execute_order(order)
            if order and order.get('status') == 'filled':
                self.risk_manager.update_position(order)
                self.logger.info(f"SUCCESSFULLY EXECUTED order for {symbol}")
            else:
                self.logger.warning(f"Order for {symbol} was not filled: {order.get('status') if order else 'None'}")

        except Exception as e:
            self.logger.exception(f"Error processing symbol {symbol}: {e}")

    def _apply_market_intelligence_filter(self, symbol: str, original_signal: int) -> int:
        """Apply market intelligence filter to trading signals"""
        if not hasattr(self, 'latest_market_intel') or not self.latest_market_intel:
            return original_signal
        
        sentiment_scores = self.latest_market_intel.get('sentiment_scores', {})
        if not sentiment_scores:
            return original_signal
        
        symbol_sentiment = sentiment_scores.get(symbol, 0)
        if original_signal > 0 and symbol_sentiment < -0.3:
            self.logger.info(f"Filtering BUY signal for {symbol} due to negative sentiment: {symbol_sentiment:.3f}")
            return 0
        if original_signal < 0 and symbol_sentiment > 0.3:
            self.logger.info(f"Filtering SELL signal for {symbol} due to positive sentiment: {symbol_sentiment:.3f}")
            return 0
        return original_signal

    def _apply_market_intelligence_sizing(self, symbol: str, original_quantity: float) -> float:
        """Apply market intelligence adjustment to position sizing"""
        if not hasattr(self, 'latest_market_intel') or not self.latest_market_intel:
            return original_quantity
        
        sentiment_scores = self.latest_market_intel.get('sentiment_scores', {})
        if not sentiment_scores:
            return original_quantity
        
        symbol_sentiment = sentiment_scores.get(symbol, 0)
        sentiment_multiplier = 0.5 + (symbol_sentiment + 1) * 0.5
        sentiment_multiplier = max(0.3, min(2.0, sentiment_multiplier))
        adjusted_quantity = original_quantity * sentiment_multiplier
        
        if abs(sentiment_multiplier - 1.0) > 0.1:
            self.logger.debug(f"Market intelligence sizing for {symbol}: sentiment={symbol_sentiment:.3f}, multiplier={sentiment_multiplier:.3f}")
        
        return adjusted_quantity

    def _check_circuit_breakers(self) -> Tuple[bool, Optional[str]]:
        """
        Check if any circuit breaker conditions are met
        
        Returns:
            Tuple of (should_trip, reason)
        """
        if not self.circuit_breaker_enabled:
            return False, None
            
        # Check consecutive losses
        if self.circuit_breaker_state['consecutive_losses'] >= self.circuit_breaker_thresholds['consecutive_losses']:
            return True, f"Consecutive losses limit reached: {self.circuit_breaker_state['consecutive_losses']}"
        
        # Check daily loss limit
        if self.circuit_breaker_state['daily_pnl'] <= -self.circuit_breaker_thresholds['daily_loss_limit']:
            return True, f"Daily loss limit exceeded: {self.circuit_breaker_state['daily_pnl']:.2%}"
        
        # Check drawdown limit
        if self.circuit_breaker_state['peak_equity'] > 0:
            drawdown = (self.circuit_breaker_state['peak_equity'] - self.circuit_breaker_state['current_equity']) / self.circuit_breaker_state['peak_equity']
            if drawdown >= self.circuit_breaker_thresholds['drawdown_limit']:
                return True, f"Drawdown limit exceeded: {drawdown:.2%}"
        
        # Check volatility spike (simplified - would need more sophisticated volatility measure)
        # For now, we'll skip this check as it requires additional data
        
        return False, None

    def _update_circuit_breaker_state(self, trade_result: Dict[str, Any]):
        """
        Update circuit breaker state based on trade result
        
        Args:
            trade_result: Dictionary containing trade outcome information
        """
        # Update P&L
        trade_pnl = trade_result.get('pnl', 0.0)
        self.circuit_breaker_state['daily_pnl'] += trade_pnl
        self.circuit_breaker_state['current_equity'] += trade_pnl
        
        # Update peak equity
        if self.circuit_breaker_state['current_equity'] > self.circuit_breaker_state['peak_equity']:
            self.circuit_breaker_state['peak_equity'] = self.circuit_breaker_state['current_equity']
        
        # Update consecutive losses
        if trade_pnl < 0:
            self.circuit_breaker_state['consecutive_losses'] += 1
        else:
            self.circuit_breaker_state['consecutive_losses'] = 0  # Reset on winning trade
        
        # Check if we should trip the circuit breaker
        should_trip, reason = self._check_circuit_breakers()
        if should_trip and not self.circuit_breaker_state['is_tripped']:
            self.circuit_breaker_state['is_tripped'] = True
            self.circuit_breaker_state['trip_reason'] = reason
            self.circuit_breaker_state['trip_time'] = time.time()
            self.logger.warning(f"CIRCUIT BREAKER TRIPPED: {reason}")
    
    def _reset_circuit_breaker(self):
        """Reset circuit breaker state (typically called daily or manually)"""
        self.circuit_breaker_state['is_tripped'] = False
        self.circuit_breaker_state['trip_reason'] = None
        self.circuit_breaker_state['trip_time'] = None
        self.circuit_breaker_state['consecutive_losses'] = 0
        self.circuit_breaker_state['daily_pnl'] = 0.0
        # Note: We don't reset equity values as they represent actual account state
        self.logger.info("Circuit breaker reset")

    def _is_trading_allowed(self) -> bool:
        """
        Check if trading is currently allowed based on circuit breaker state
        
        Returns:
            True if trading is allowed, False if circuit breaker is tripped
        """
        if self.circuit_breaker_state['is_tripped']:
            self.logger.debug(f"Trading blocked by circuit breaker: {self.circuit_breaker_state['trip_reason']}")
            return False
        return True
