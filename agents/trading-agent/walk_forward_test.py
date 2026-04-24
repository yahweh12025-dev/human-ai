import os
import json
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading_agent import TradingAgent
from strategies.sma_crossover import SMACrossover
from risk.manager import RiskManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AdvancedBacktester")

class AdvancedBacktester:
    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r') as f:
            self.config = json.load(f) # Simplified load
        
        self.strategy = SMACrossover(self.config['futures'])
        self.risk_manager = RiskManager(self.config['risk'])
        self.initial_equity = 10000.0
        self.equity = self.initial_equity

    def load_data(self, symbol, timeframe, days):
        import ccxt
        exchange = ccxt.binance({'enableRateLimit': True})
        since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df

    def run_walk_forward(self, symbol, timeframe, total_days=60):
        """
        Walk Forward Analysis: Train on X days, Test on Y days, Slide window.
        """
        train_days = 30
        test_days = 15
        
        # Fetch total data
        data = self.load_data(symbol, timeframe, total_days)
        all_test_results = []
        
        # Window sliding
        for start_idx in range(0, len(data) - (train_days*24) - (test_days*24), 24*7): # Slide weekly
            train_end = start_idx + (train_days * 24)
            test_end = train_end + (test_days * 24)
            
            train_set = data.iloc[start_idx:train_end]
            test_set = data.iloc[train_end:test_end]
            
            # We evaluate the current strategy on the test set
            res = self.simulate_trading(test_set, symbol, timeframe)
            all_test_results.append(res)
            
        return all_test_results

    def simulate_trading(self, data, symbol, timeframe):
        # Simplified version of TradingAgent.run() logic
        equity = self.initial_equity
        trades = []
        open_pos = None
        
        for i in range(30, len(data)):
            current_slice = data.iloc[:i+1]
            price = current_slice['Close'].iloc[-1]
            
            # Get 4h trend data for filtering
            # In real walk-forward, we'd fetch 4h data corresponding to this timestamp
            # Here we assume trend is calculated if trend_data provided
            signal = self.strategy.generate_signal(current_slice, timeframe_mins=60) 
            
            if open_pos:
                if self.strategy.generate_signal(current_slice, timeframe_mins=60) != open_pos['signal']:
                    pnl = (price - open_pos['entry']) * open_pos['qty'] if open_pos['signal'] == 1 else (open_pos['entry'] - price) * open_pos['qty']
                    equity += pnl
                    trades.append({'pnl': pnl, 'equity': equity})
                    open_pos = None
            elif signal != 0:
                qty = self.risk_manager.calculate_position_size(symbol, price, price * 0.95)
                open_pos = {'signal': signal, 'entry': price, 'qty': qty}
        
        return {'final_equity': equity, 'trades': trades}

if __name__ == "__main__":
    # This is a skeleton for the walk-forward script.
    # I will implement the full a-b comparison in the final report.
    print("Walk Forward Analysis Framework Initialized")
