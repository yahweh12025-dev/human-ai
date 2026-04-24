"""
Risk Manager Module

Handles risk management: position sizing, stop-loss, portfolio limits, etc.
"""
import logging
import numpy as np

class RiskManager:
    def __init__(self, config):
        """
        Initialize the risk manager with high leverage defaults and trend filters.
        :param config: Dictionary containing risk configuration.
        """
        self.max_risk_per_trade = config.get('max_risk_per_trade', 2.0)  # % of equity
        self.max_open_positions = config.get('max_open_positions', 5)
        self.stop_loss_percent = config.get('stop_loss_percent', 5.0)  # % of entry price
        self.take_profit_percent = config.get('take_profit_percent', 15.0)  # % of entry price
        self.max_daily_loss_percent = config.get('max_daily_loss_percent', 10.0)
        
        # Dynamic Leverage & Margin
        self.base_leverage = config.get('leverage', 5)
        self.current_leverage = self.base_leverage
        self.margin_call_threshold = config.get('margin_call_threshold', 60.0)  # % loss before auto-liquidation
        
        self.logger = logging.getLogger(__name__)

        # --- GROWTH ENGINE STATE ---
        self.open_positions = {}
        self.daily_pnl = 0.0
        self.starting_equity = config.get('starting_equity', 1.0)  # Start with $1
        self.current_equity = self.starting_equity
        self.atr_values = []  # Store ATR for volatility calculation
        
        self.logger.info(f"GROWTH ENGINE STARTED: ${self.starting_equity} → Goal: Maximum Compound Growth")
        
    def calculate_dynamic_leverage(self, current_atr, historical_atr_mean):
        """
        Adjust leverage based on volatility to avoid liquidation.
        High Volatility -> Lower Leverage (2x)
        Low Volatility -> Higher Leverage (5x)
        """
        if historical_atr_mean == 0:
            return self.base_leverage
            
        vol_ratio = current_atr / historical_atr_mean
        
        # If current volatility is 2x the historical average, drop leverage to 2x
        if vol_ratio > 2.0:
            self.current_leverage = 2.0
        elif vol_ratio > 1.5:
            self.current_leverage = 3.0
        else:
            self.current_leverage = self.base_leverage
            
        self.logger.info(f"Volatility Ratio: {vol_ratio:.2f} -> Setting Leverage to {self.current_leverage}x")
        return self.current_leverage
        
    def calculate_atr(self, high, low, close, period=14):
        """
        Calculate Average True Range for dynamic grid sizing.
        """
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        return atr

    def update_portfolio(self, data, symbol):
        """
        Update portfolio value based on latest market data.
        :param data: DataFrame with latest market data.
        :param symbol: Symbol to update (for position valuation).
        """
        # In a more complete system, we would calculate the current value of all positions.
        # For now, we just note that we have new data.
        # We could update the current equity based on position PnL.
        # This is a placeholder.
        pass

    def can_trade(self, symbol):
        """
        Check if we can open a new position in the given symbol based on risk limits.
        :param symbol: Trading symbol.
        :return: Boolean indicating if trading is allowed.
        """
        # Check if we already have an open position in this symbol
        if symbol in self.open_positions:
            self.logger.debug(f"Already have an open position in {symbol}")
            return False

        # Check if we have reached the maximum number of open positions
        if len(self.open_positions) >= self.max_open_positions:
            self.logger.debug(f"Maximum open positions ({self.max_open_positions}) reached")
            return False

        # Check daily loss limit
        if self.daily_pnl <= -self.starting_equity * (self.max_daily_loss_percent / 100):
            self.logger.debug(f"Daily loss limit reached: {self.daily_pnl}")
            return False

        return True

    def calculate_position_size(self, symbol, entry_price, stop_loss_price):
        """
        Calculate the position size based on risk per trade and stop loss.
        :param symbol: Trading symbol.
        :param entry_price: Entry price for the trade.
        :param stop_loss_price: Stop loss price for the trade.
        :return: Quantity to trade.
        """
        # Risk per trade in monetary terms
        risk_amount = self.current_equity * (self.max_risk_per_trade / 100)
        # Risk per share (absolute difference between entry and stop loss)
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share == 0:
            self.logger.warning("Risk per share is zero, cannot calculate position size")
            return 0
        quantity = risk_amount / risk_per_share
        return quantity

    def update_position(self, order):
        """
        Update the risk manager with a new position after an order is filled.
        :param order: Filled order dictionary.
        """
        symbol = order['symbol']
        signal = order['signal']  # 1 for buy, -1 for sell
        entry_price = order['filled_price']
        quantity = order['quantity']  # This should be set by the risk manager before execution

        # For simplicity, we assume the order quantity is already set correctly.
        # In a real flow, the risk manager would calculate the quantity and the executor would use it.

        # Calculate stop loss and take profit levels
        if signal == 1:  # long position
            stop_loss = entry_price * (1 - self.stop_loss_percent / 100)
            take_profit = entry_price * (1 + self.take_profit_percent / 100)
        else:  # short position
            stop_loss = entry_price * (1 + self.stop_loss_percent / 100)
            take_profit = entry_price * (1 - self.take_profit_percent / 100)

        self.open_positions[symbol] = {
            'entry_price': entry_price,
            'quantity': quantity,
            'signal': signal,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': order['filled_timestamp']
        }
        self.logger.info(f"Opened position for {symbol}: {self.open_positions[symbol]}")

    def check_exit_conditions(self, symbol, current_price):
        """
        Check if we should exit a position based on stop loss or take profit.
        :param symbol: Trading symbol.
        :param current_price: Current market price.
        :return: Exit signal: 1 for close long, -1 for close short, 0 for no exit.
        """
        if symbol not in self.open_positions:
            return 0

        pos = self.open_positions[symbol]
        exit_signal = 0

        if pos['signal'] == 1:  # long position
            if current_price <= pos['stop_loss']:
                exit_signal = -1  # close long (sell)
                self.logger.info(f"Stop loss triggered for long {symbol} at {current_price}")
            elif current_price >= pos['take_profit']:
                exit_signal = -1  # close long (sell)
                self.logger.info(f"Take profit triggered for long {symbol} at {current_price}")
        else:  # short position
            if current_price >= pos['stop_loss']:
                exit_signal = 1  # close short (buy)
                self.logger.info(f"Stop loss triggered for short {symbol} at {current_price}")
            elif current_price <= pos['take_profit']:
                exit_signal = 1  # close short (buy)
                self.logger.info(f"Take profit triggered for short {symbol} at {current_price}")

        return exit_signal

    def check_margin_calls(self, data):
        """
        Check all open positions for margin call risk (60% loss threshold).
        Auto-liquidates if unrealized loss exceeds 60% of position value.
        :param data: DataFrame with latest market prices.
        """
        positions_to_close = []
        for symbol, pos in self.open_positions.items():
            current_price = data['Close'].iloc[-1]
            entry_price = pos['entry_price']
            quantity = pos['quantity']
            
            # Calculate unrealized loss percentage
            if pos['signal'] == 1:  # long
                loss_pct = (entry_price - current_price) / entry_price * 100
            else:  # short
                loss_pct = (current_price - entry_price) / entry_price * 100
            
            # Check against margin call threshold
            if loss_pct >= self.margin_call_threshold:
                self.logger.warning(f"MARGIN CALL: {symbol} loss {loss_pct:.2f}% exceeds threshold. Liquidating.")
                positions_to_close.append((symbol, current_price))
        
        # Close positions
        for symbol, price in positions_to_close:
            self.close_position(symbol, price)
        
        return len(positions_to_close) > 0        # Calculate PnL for the position
        if pos['signal'] == 1:  # long
            pnl = (exit_price - pos['entry_price']) * pos['quantity']
        else:  # short
            pnl = (pos['entry_price'] - exit_price) * pos['quantity']

        self.daily_pnl += pnl
        self.current_equity += pnl  # Simplistic: assume we can reinvest immediately
        del self.open_positions[symbol]
        self.logger.info(f"Closed position for {symbol} with PnL: {pnl:.2f}. Daily PnL: {self.daily_pnl:.2f}")
    def close_position(self, symbol, exit_price):
        """
        Close a position and update PnL.
        :param symbol: Trading symbol.
        :param exit_price: Price at which the position is closed.
        """
        if symbol not in self.open_positions:
            self.logger.warning(f"No open position for {symbol} to close.")
            return

        pos = self.open_positions[symbol]

        # Calculate PnL for the position
        if pos['signal'] == 1:  # long
            pnl = (exit_price - pos['entry_price']) * pos['quantity']
        else:  # short
            pnl = (pos['entry_price'] - exit_price) * pos['quantity']

        self.daily_pnl += pnl
        self.current_equity += pnl
        del self.open_positions[symbol]
        self.logger.info(f"Closed position for {symbol} at {exit_price:.2f} with PnL: {pnl:.2f}. Equity: {self.current_equity:.2f}. Daily PnL: {self.daily_pnl:.2f}")
