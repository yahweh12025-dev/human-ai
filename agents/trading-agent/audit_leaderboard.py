import os
import json
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import ccxt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LeaderboardGenerator")

class ProfitabilityAudit:
    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r') as f:
            import yaml
            self.config = yaml.safe_load(f)
        
        # Symbols to audit
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'DOT/USDT']
        self.timeframes = ['15m', '1h', '4h']
        self.initial_equity = self.config.get('risk', {}).get('starting_equity', 10000.0)
        self.exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})

    def run_symbol_audit(self, symbol, timeframe):
        """Run a quick backtest to get performance metrics."""
        try:
            # Fetch 30 days of data
            since = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since)
            if not ohlcv: return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Import our actual strategy and risk manager
            from strategies.sma_crossover import SMACrossover
            from risk.manager import RiskManager
            
            strategy = SMACrossover(self.config['futures'])
            risk = RiskManager(self.config['risk'])
            risk.current_equity = self.initial_equity
            
            equity = self.initial_equity
            trades = []
            open_pos = None
            
            # Simplified simulation
            for i in range(30, len(df)):
                curr_slice = df.iloc[:i+1]
                price = curr_slice['Close'].iloc[-1]
                
                if open_pos:
                    # Basic exit if opposite signal or stop loss
                    sig = strategy.generate_signal(curr_slice)
                    if sig != 0 and sig != open_pos['signal']:
                        pnl = (price - open_pos['entry']) * open_pos['qty'] if open_pos['signal'] == 1 else (open_pos['entry'] - price) * open_pos['qty']
                        equity += pnl
                        trades.append({'pnl': pnl, 'duration': (curr_slice.index[-1] - open_pos['time']).total_seconds()})
                        open_pos = None
                else:
                    sig = strategy.generate_signal(curr_slice)
                    if sig != 0:
                        # Fixed small quantity for audit
                        qty = 0.1 if 'BTC' in symbol else 1.0
                        open_pos = {'signal': sig, 'entry': price, 'qty': qty, 'time': curr_slice.index[-1]}
            
            # Close open position
            if open_pos:
                price = df['Close'].iloc[-1]
                pnl = (price - open_pos['entry']) * open_pos['qty'] if open_pos['signal'] == 1 else (open_pos['entry'] - price) * open_pos['qty']
                equity += pnl
                trades.append({'pnl': pnl, 'duration': (df.index[-1] - open_pos['time']).total_seconds()})

            total_pnl = equity - self.initial_equity
            wins = [t for t in trades if t['pnl'] > 0]
            losses = [t for t in trades if t['pnl'] <= 0]
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'profit': total_pnl,
                'losses': sum([t['pnl'] for t in losses]),
                'trades': len(trades),
                'win_rate': (len(wins)/len(trades)*100) if trades else 0,
                'avg_duration_hrs': (sum([t['duration'] for t in trades])/3600/len(trades)) if trades else 0,
                'final_equity': equity
            }
        except Exception as e:
            logger.error(f"Audit failed for {symbol} {timeframe}: {e}")
            return None

    def generate_leaderboard(self):
        results = []
        for symbol in self.symbols:
            for tf in self.timeframes:
                logger.info(f"Auditing {symbol} on {tf}...")
                res = self.run_symbol_audit(symbol, tf)
                if res: results.append(res)
        
        # Sort by profit
        leaderboard = sorted(results, key=lambda x: x['profit'], reverse=True)
        
        # Save to log directory
        os.makedirs('backtest_logs', exist_ok=True)
        filename = 'profitability_leaderboard.json'
        with open(os.path.join('backtest_logs', filename), 'w') as f:
            json.dump({
                'last_updated': datetime.now().isoformat(),
                'leaderboard': leaderboard
            }, f, indent=2)
        
        return leaderboard

if __name__ == "__main__":
    audit = ProfitabilityAudit()
    board = audit.generate_leaderboard()
    print(json.dumps(board, indent=2))
