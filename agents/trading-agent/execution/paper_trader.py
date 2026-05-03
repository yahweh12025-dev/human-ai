"""
Paper Trader Module

Simulates order execution for paper trading.
Can also execute real orders via CCXT when broker is set to 'binance'.
"""
import logging
from datetime import datetime
import ccxt
import os

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
        if self.broker == 'alpaca':
            try:
                import alpaca_trade_api as tradeapi
                from dotenv import load_dotenv
                load_dotenv('/home/yahwehatwork/human-ai/human-ai.env')
                
                api_key = os.getenv('ALPACA_API_KEY')
                api_secret = os.getenv('ALPACA_SECRET_KEY')
                base_url = os.getenv('ALPACA_ENDPOINT', 'https://paper-api.alpaca.markets').replace('/v2', '')
                
                self.exchange = tradeapi.REST(api_key, api_secret, base_url=base_url)
                self.logger.info("Alpaca Paper Trading mode enabled.")
            except Exception as e:
                self.logger.error(f"Failed to initialize Alpaca: {e}")
        
        
        # Initialize real exchange if needed
        if self.broker == 'binance':
            try:
                self.exchange = ccxt.binance({
                    'apiKey': config.get('api_key', ''),
                    'secret': config.get('api_secret', ''),
                    'sandbox': config.get('testnet', True),  # Use testnet by default
                    'enableRateLimit': True,
                })
                if self.exchange.sandbox:
                    self.logger.info("Binance testnet mode enabled.")
                else:
                    self.logger.info("Binance live mode enabled.")
            except Exception as e:
                self.logger.error(f"Failed to initialize Binance: {e}")
# Track paper trade equity
        self.equity = 10000.0  # Default starting equity
        self.paper_trading = config.get("paper_trading", False)
        self.positions = {}  # Track open positions

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
            'order_type': 'MARKET',
            'status': 'created'
        }
        return order
    
    def execute_order(self, order):
        """Execute an order - either simulate (paper) or send to exchange (binance or alpaca).
        
        :param order: Order dictionary.
        """
        if self.broker == 'paper':
            # Simulate the fill and update our internal records.
            # For now, we just log the execution.
            self.logger.info(f"Executing paper order: {order}")
            # Record fill
            order['status'] = 'filled'
            order['filled_price'] = order['price']
            order['filled_timestamp'] = datetime.now()

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

                # For futures, we need to specify the position side or use reduceOnly for closing
                params = {}
                # If closing a position, set reduceOnly to true
                if order.get('closing', False):
                    params['reduceOnly'] = True

                # Execute the order
                order_result = self.exchange.create_order(
                    symbol=ccxt_symbol,
                    type='MARKET',
                    side=side,
                    amount=order['quantity'],
                    params=params
                )

                # Update order and position tracking
                self.positions[ccxt_symbol] = {
                    'entry_price': order_result.get('average', order['price']),
                    'quantity': order_result.get('amount', '0'),
                    'timestamp': datetime.fromtimestamp(order_result['timestamp'] / 1000) if 'timestamp' in order_result else datetime.now()
                }

                self.logger.info(f"Executed real Binance order: {order_result}")
                # Update order info
                order.update({
                    'status': 'filled',
                    'filled_price': order_result.get('average', order['price']),
                    'filled_timestamp': datetime.fromtimestamp(order_result.get('timestamp', datetime.now().timestamp()) / 1000),
                    'exchange_id': order_result.get('id'),
                    'exchange_info': order_result
                })
            except Exception as e:
                self.logger.exception(f"Error executing Binance order: {e}")
                order['status'] = 'failed'
                order['error'] = str(e)

        elif self.broker == 'alpaca':
            # Execute real order on Alpaca
            # Execute real order on Alpaca (or simulate if paper_trading is True)
            try:
                # Alpaca expects symbols like BTC/USD
                alpaca_symbol = order['symbol'].replace('USDT', 'USD')
                
                # Determine order side
                side = 'buy' if order['signal'] == 1 else 'sell'
                
                # Calculate quantity in base currency (not USDT)
                # For crypto, Alpaca wants quantity in BTC/ETH/SOL etc.
                # Our quantity is already in base currency from risk manager
                qty = order['quantity']
                
                # If paper trading is enabled, simulate the fill
                if getattr(self, 'paper_trading', False):
                    # Simulate the fill and update our internal records.
                    self.logger.info(f"Executing paper order (Alpaca simulator): {order}")
                    # Record fill
                    order['status'] = 'filled'
                    order['filled_price'] = order['price']
                    order['filled_timestamp'] = datetime.now()
                else:
                    # Submit order to Alpaca
                    order_result = self.exchange.submit_order(
                        symbol=alpaca_symbol,
                        qty=qty,
                        side=side,
                        type="market",
                        time_in_force="gtc"
                    )
                    
                    # Update order info
                    order.update({
                        "status": "filled",
                        "filled_price": float(order_result.filled_avg_price) if order_result.filled_avg_price else order["price"],
                        "filled_timestamp": order_result.filled_at,
                        "exchange_id": order_result.id,
                        "exchange_info": order_result._raw
                    })
                    
                    self.logger.info(f"Executed real Alpaca order: {order_result}")
            except Exception as e:
                self.logger.exception(f"Error executing Alpaca order: {e}")
                order['status'] = 'failed'
                order['error'] = str(e)
