"""Minimal RiskManager stub — imported by trading_agent.py."""


class RiskManager:
    def __init__(self, config=None):
        self.config = config or {}
        self.stop_loss_percent = self.config.get("stop_loss_percent", 2.0)
        self.open_positions = {}

    def update_portfolio(self, data, symbol):
        return None

    def check_exit_conditions(self, symbol, current_price, current_signal=None, hold_time=None):
        return 0

    def can_trade(self, symbol):
        return True

    def calculate_position_size(self, symbol, entry_price, stop_loss_price):
        return 0

    def update_position(self, order):
        return None

    def close_position(self, symbol, filled_price):
        self.open_positions.pop(symbol, None)
