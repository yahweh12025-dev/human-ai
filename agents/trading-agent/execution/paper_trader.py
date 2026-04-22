"""
Paper Trader Module

Simulates order execution for paper trading.
Can also execute real orders via CCXT when broker is set to 'binance'.
"""
import logging
from datetime import datetime
import ccxt

class PaperTrader:
    def __init__(self, config):
        """
        Initialize the paper trader.
        :param config: Dictionary containing execution configuration.
        """
        self.broker = config.get('broker', 'paper')
        self.order_size_percent = config.get('order_size_percent', 10)  # % of equity per trade
        self.slippage_tolerance = config.get('slippage_tolerance', 0.001)
        self.logger = logging.getLogger(__name__)
        
        # Initialize real exchange if needed
        if self.broker == 'binance':
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # Use futures market
                }
            })
        # In a more complete implementation, we would track positions and equity here.
        # For now, we just log the orders.

    def create_order(self, symbol, signal, data):
        """
        Create an order based on signal and current data.
        :param symbol: Trading symbol.
        :param signal: 1 for buy, -1 for sell.
        :param data: DataFrame with latest market data.
        :return: Dictionary representing the order or None if cannot create.
        """
        if signal == 0:
            return None

        # Get the latest close price
        latest_close = data['Close'].iloc[-1]
        # Apply slippage: for buy, we assume we pay a bit more; for sell, we get a bit less.
        if signal == 1:  # buy
            price = latest_close * (1 + self.slippage_tolerance)
        else:  # sell
            price = latest_close * (1 - self.slippage_tolerance)

        order = {
            'symbol': symbol,
            'signal': signal,  # 1 for buy, -1 for sell
            'price': price,
            'quantity': 0,  # To be set by risk manager
            'timestamp': datetime.now(),
            'order_type': 'market',
            'status': 'created'
        }
        return order

    def execute_order(self, order):
        """
        Execute an order - either simulate (paper) or send to exchange (binance).
        :param order: Order dictionary.
        """
        if order is None:
            return

        if self.broker == 'paper':
            # In a paper trader, we simulate the fill and update our internal records.
            # For now, we just log the execution.
            self.logger.info(f"Executing paper order: {order}")
            # Update order status
            order['status'] = 'filled'
            order['filled_price'] = order['price']
            order['filled_timestamp'] = datetime.now()
            # In a more complete system, we would update a position tracker here.
        elif self.broker == 'binance':
            # Execute real order on Binance futures
            try:
                # Convert symbol to CCXT format
                ccxt_symbol = order['symbol'].replace('-', '/')
                if '/' not in ccxt_symbol and 'USDT' not in ccxt_symbol:
                    if ccxt_symbol.endswith('USD'):
                        ccxt_symbol = ccxt_symbol[:-3] + '/USDT'
                    elif len(ccxt_symbol) >= 3:
                        ccxt_symbol = ccxt_symbol + '/USDT'
                
                # Determine order side
                side = 'buy' if order['signal'] == 1 else 'sell'
                
                # Create market order
                params = {}
                # For Binance futures, we might need to specify reduceOnly etc. for closing positions
                # But for now, we'll keep it simple
                
                order_result = self.exchange.create_market_order(
                    symbol=ccxt_symbol,
                    type='market',
                    side=side,
                    amount=order['quantity'],
                    params=params
                )
                
                self.logger.info(f"Executed real order on Binance: {order_result}")
                # Update order with exchange result
                order.update({
                    'status': 'filled',
                    'filled_price': order_result.get('average', order['price']),
                    'filled_timestamp': datetime.fromtimestamp(order_result.get('timestamp', datetime.now().timestamp()) / 1000),
                    'exchange_id': order_result.get('id'),
                    'exchange_info': order_result
                })
            except Exception as e:
                self.logger.exception(f"Error executing order on Binance: {e}")
                order['status'] = 'failed'
                order['error'] = str(e)
        else:
            self.logger.warning(f"Unknown broker type: {self.broker}")
