import pandas as pd
import numpy as np
import json
import os
import yaml
import logging
import sys
from datetime import datetime, timedelta

# Absolute path to the trading agent directory
AGENT_DIR = "/home/yahwehatwork/human-ai/agents/trading-agent"
sys.path.insert(0, AGENT_DIR)

from strategies.master_strategy import MasterStrategy
from risk.manager import RiskManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TradeJournaler")

class TradeJournaler:
    def __init__(self, config_path='/home/yahwehatwork/human-ai/agents/trading-agent/config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.risk_config = self.config.get('risk', {})
        self.initial_equity = 1.0  # Starting with $1.00 as requested
        self.leverage = self.config.get('execution', {}).get('leverage', 1)

    def load_data(self, symbol, timeframe, start_date, end_date):
        import ccxt
        try:
            exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
            since = int(start_date.timestamp() * 1000)
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df[(df.index >= start_date) & (df.index <= end_date)]
        except Exception as e:
            logger.error(f"Error loading {symbol}: {e}")
            return None

    def run_journal(self, symbol, timeframe, start_date, end_date):
        data = self.load_data(symbol, timeframe, start_date, end_date)
        if data is None or len(data) < 60: return None, 0

        strat = MasterStrategy()
        risk_manager = RiskManager(self.risk_config)
        equity = self.initial_equity
        trades = []
        open_position = None

        # EXACT SAME LOOP AS GAUNTLET TESTER
        for i in range(50, len(data)):
            current_price = data['Close'].iloc[i]
            
            if open_position:
                exit_sig = risk_manager.check_exit_conditions(symbol, current_price)
                if exit_sig != 0:
                    raw_pnl = (current_price - open_position['entry_price']) * open_position['qty'] if open_position['sig'] == 1 else (open_position['entry_price'] - current_price) * open_position['qty']
                    pnl = raw_pnl * self.leverage
                    equity += pnl
                    trades.append({
                        'entry_time': open_position['entry_time'],
                        'exit_time': data.index[i],
                        'pnl': pnl,
                        'equity': equity
                    })
                    open_position = None
            else:
                # Ensure a clean slice is passed to the strategy
                current_slice = data.iloc[:i+1].copy()
                sig = strat.generate_signal(current_slice)
                
                if sig != 0:
                    stop = current_price * (1 - risk_manager.stop_loss_percent/100) if sig == 1 else current_price * (1 + risk_manager.stop_loss_percent/100)
                    qty = risk_manager.calculate_position_size(symbol, current_price, stop)
                    if qty > 0:
                        open_position = {'sig': sig, 'entry_price': current_price, 'qty': qty, 'entry_time': data.index[i]}

        # Force close at end of window
        if open_position:
            final_price = data['Close'].iloc[-1]
            raw_pnl = (final_price - open_position['entry_price']) * open_position['qty'] if open_position['sig'] == 1 else (open_position['entry_price'] - final_price) * open_position['qty']
            pnl = raw_pnl * self.leverage
            equity += pnl
            trades.append({
                'entry_time': open_position['entry_time'],
                'exit_time': data.index[-1],
                'pnl': pnl,
                'equity': equity
            })

        return trades, equity

def main():
    # Testing the absolute best performer from Gauntlet: WLD/USDT 1h
    symbol = 'WLD/USDT'
    timeframe = '1h'
    end = datetime.utcnow()
    start = end - timedelta(days=30)
    
    journaler = TradeJournaler()
    trades, final_equity = journaler.run_journal(symbol, timeframe, start, end)
    
    if trades:
        daily_revenue = {}
        for t in trades:
            date = t['exit_time'].strftime('%Y-%m-%d')
            daily_revenue[date] = daily_revenue.get(date, 0) + t['pnl']
            
        sorted_dates = sorted(daily_revenue.keys())
        print(f"--- Daily Revenue Report for {symbol} {timeframe} ---")
        print(f"Starting Balance: $1.00")
        for date in sorted_dates:
            print(f"{date}: ${daily_revenue[date]:.4f}")
        print(f"Total Final Equity: ${final_equity:.4f}")
    else:
        print("No trades found for this scenario. Check if the strategy is too restrictive for the current date window.")

if __name__ == "__main__":
    main()
