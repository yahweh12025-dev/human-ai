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

from trading_strategy import TradingStrategy
from risk.manager import RiskManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SurgicalResume")

class SurgicalResume:
    def __init__(self, config_path='/home/yahwehatwork/human-ai/agents/trading-agent/config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.risk_config = self.config.get('risk', {})
        self.initial_equity = 10000.0 

    def load_data(self, symbol, timeframe, days=60):
        import ccxt
        try:
            exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
            since = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1500)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error loading {symbol} {timeframe}: {e}")
            return None

    def run_test(self, symbol, timeframe, data, leverage, stop_loss, take_profit):
        strat = TradingStrategy()
        run_risk_config = self.risk_config.copy()
        run_risk_config['stop_loss_percent'] = stop_loss
        run_risk_config['take_profit_percent'] = take_profit
        
        risk_manager = RiskManager(run_risk_config)
        equity = self.initial_equity
        trades_count = 0
        open_position = None

        for i in range(60, len(data)):
            current_price = data['Close'].iloc[i]
            if open_position:
                current_slice = data.iloc[:i+1]
                current_sig = strat.generate_signal(current_slice)
                hold_time = i - open_position['entry_index']
                exit_sig = risk_manager.check_exit_conditions(symbol, current_price, current_signal=current_sig, hold_time=hold_time)
                if exit_sig != 0:
                    raw_pnl = (current_price - open_position['entry_price']) * open_position['qty'] if open_position['sig'] == 1 else (open_position['entry_price'] - current_price) * open_position['qty']
                    equity += (raw_pnl * leverage)
                    trades_count += 1
                    open_position = None
            else:
                current_slice = data.iloc[:i+1]
                sig = strat.generate_signal(current_slice)
                if sig != 0:
                    stop = current_price * (1 - stop_loss/100) if sig == 1 else current_price * (1 + stop_loss/100)
                    qty = risk_manager.calculate_position_size(symbol, current_price, stop)
                    if qty > 0:
                        open_position = {'sig': sig, 'entry_price': current_price, 'qty': qty, 'entry_index': i}
        
        if open_position:
            final_price = data['Close'].iloc[-1]
            raw_pnl = (final_price - open_position['entry_price']) * open_position['qty'] if open_position['sig'] == 1 else (open_position['entry_price'] - final_price) * open_position['qty']
            equity += (raw_pnl * leverage)
            trades_count += 1

        return {'return': (equity-self.initial_equity)/self.initial_equity*100, 'trades': trades_count}

def main():
    gauntlet = SurgicalResume()
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'DOT/USDT', 'WLD/USDT', 'BCH/USDT', 'LDO/USDT']
    timeframes = ['5m', '15m', '1h', '4h']
    leverages = [1, 2, 5, 10]
    sl_range = [1.0, 2.0, 3.0]
    tp_range = [3.0, 5.0, 10.0]
    
    results_file = '/home/yahwehatwork/human-ai/agents/trading-agent/master_logs/universal_gauntlet.json'
    
    # Load existing results to find where we left off
    try:
        with open(results_file, 'r') as f:
            existing_results = json.load(f)
        processed_symbols = set([r['symbol'] for r in existing_results])
    except:
        existing_results = []
        processed_symbols = set()

    remaining_symbols = [s for s in symbols if s not in processed_symbols]
    logger.info(f"Resuming from {len(processed_symbols)} completed symbols. Remaining: {remaining_symbols}")

    for s in remaining_symbols:
        coin_results = []
        for tf in timeframes:
            data = gauntlet.load_data(s, tf)
            if data is None: continue
            logger.info(f"Resuming {s} {tf}...")
            for lev in leverages:
                for sl in sl_range:
                    for tp in tp_range:
                        res = gauntlet.run_test(s, tf, data, lev, sl, tp)
                        coin_results.append({
                            'symbol': s, 'tf': tf, 'leverage': lev, 'sl': sl, 'tp': tp,
                            'return': res['return'], 'trades': res['trades']
                        })
        
        # Append results for this coin immediately
        with open(results_file, 'r+') as f:
            current_data = json.load(f)
            current_data.extend(coin_results)
            f.seek(0)
            json.dump(current_data, f, indent=2)
            f.truncate()
        logger.info(f"Saved la-layered (ta-layered) la-results for {s}")

    logger.info("Surgical Resume Completed.")

if __name__ == "__main__":
    main()
