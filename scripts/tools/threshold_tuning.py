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
logger = logging.getLogger("TuningSweep")

class TuningSweep:
    def __init__(self, config_path='/home/yahwehatwork/human-ai/agents/trading-agent/config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.risk_config = self.config.get('risk', {})
        self.initial_equity = self.risk_config.get('starting_equity', 10000.0)
        self.leverage = self.config.get('execution', {}).get('leverage', 1)

    def load_data(self, symbol, timeframe, limit=2500):
        import ccxt
        try:
            exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error loading {symbol} {timeframe}: {e}")
            return None

    def run_test(self, symbol, timeframe, threshold, data):
        equity = self.initial_equity
        trades = []
        open_position = None
        risk_manager = RiskManager(self.risk_config)
        
        # Inject the threshold into the strategy
        strat = MasterStrategy()
        strat.entry_threshold = threshold
        
        opens = data['Open'].values
        closes = data['Close'].values
        highs = data['High'].values
        lows = data['Low'].values

        for i in range(50, len(data)):
            current_price = closes[i]
            if open_position:
                exit_sig = risk_manager.check_exit_conditions(symbol, current_price)
                if exit_sig != 0:
                    pnl = ((current_price - open_position['entry_price']) * open_position['qty'] if open_position['sig'] == 1 else (open_position['entry_price'] - current_price) * open_position['qty']) * self.leverage
                    equity += pnl
                    trades.append({'pnl': pnl})
                    open_position = None
            else:
                sig = strat.generate_signal(data.iloc[:i+1])
                if sig != 0:
                    stop = current_price * (1 - risk_manager.stop_loss_percent/100) if sig == 1 else current_price * (1 + risk_manager.stop_loss_percent/100)
                    qty = risk_manager.calculate_position_size(symbol, current_price, stop)
                    if qty > 0:
                        open_position = {'sig': sig, 'entry_price': current_price, 'qty': qty}

        return {'trades_count': len(trades), 'return': (equity-self.initial_equity)/self.initial_equity*100}

def main():
    sweep = TuningSweep()
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT']
    timeframes = ['5m', '15m', '1h']
    thresholds = [2, 3, 4, 5]
    
    final_results = {}
    
    for t in thresholds:
        logger.info(f"Testing Threshold: {t}")
        t_results = []
        for s in symbols:
            for tf in timeframes:
                data = sweep.load_data(s, tf)
                if data is not None:
                    res = sweep.run_test(s, tf, t, data)
                    t_results.append(res)
        
        avg_trades = np.mean([r['trades_count'] for r in t_results])
        avg_ret = np.mean([r['return'] for r in t_results])
        final_results[str(t)] = {'avg_trades': avg_trades, 'avg_return': avg_ret}
        print(f"Threshold {t} -> Avg Trades: {avg_trades:.2f}, Avg Return: {avg_ret:.2f}%")

    os.makedirs('/home/yahwehatwork/human-ai/agents/trading-agent/master_logs', exist_ok=True)
    with open('/home/yahwehatwork/human-ai/agents/trading-agent/master_logs/threshold_tuning.json', 'w') as f:
        json.dump(final_results, f, indent=2)

if __name__ == "__main__":
    main()
