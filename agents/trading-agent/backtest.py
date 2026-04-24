import pandas as pd
import numpy as np
import json
import os
import yaml
import logging
import sys
from datetime import datetime, timedelta

# Ensure we can import from the agent directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading_agent import TradingAgent
from strategies.grid import GridStrategy
from risk.manager import RiskManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Backtester")

class TradingBacktester:
    def __init__(self, config_path='config.yaml'):
        if not os.path.isabs(config_path):
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_path)
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.strategy = GridStrategy(self.config['strategy']['grid'])
        self.risk_config = self.config.get('risk', {})
        self.initial_equity = self.risk_config.get('starting_equity', 10000.0)
        self.equity = self.initial_equity
        self.trades = []
        self.logger = logger

    def load_historical_data(self, symbol, start_date, end_date, timeframe='1h'):
        import ccxt

        try:
            exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
            ohlcv = exchange.fetch_ohlcv(
                symbol, 
                timeframe=timeframe,
                since=int(start_date.timestamp() * 1000),
                limit=1000
            )

            if not ohlcv: 
                return None

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            return df

        except Exception as e:
            self.logger.warning(f"Error loading {symbol}: {e}")
            return None

    def run_backtest(self, symbol, start_date, end_date, timeframe='1h'):
        data = self.load_historical_data(symbol, start_date, end_date, timeframe)
        if data is None or len(data) < 50: 
            return None

        risk_manager = RiskManager(self.risk_config)
        risk_manager.current_equity = self.initial_equity
        risk_manager.starting_equity = self.initial_equity
        
        equity_curve = []
        open_position = None

        for i in range(30, len(data)):
            current_slice = data.iloc[:i+1]
            current_price = current_slice['Close'].iloc[-1]
            
            if open_position:
                exit_signal = risk_manager.check_exit_conditions(symbol, current_price)
                if exit_signal != 0:
                    pnl = (current_price - open_position['entry_price']) * open_position['quantity'] if open_position['signal'] == 1 else (open_position['entry_price'] - current_price) * open_position['quantity']
                    self.equity += pnl
                    self.trades.append({
                        'entry_time': open_position['entry_time'],
                        'exit_time': current_slice.index[-1],
                        'symbol': symbol,
            'timeframe': timeframe,
                        'signal': open_position['signal'],
                        'entry_price': open_position['entry_price'],
                        'exit_price': current_price,
                        'quantity': open_position['quantity'],
                        'pnl': pnl,
                        'equity': self.equity,
                        'duration_mins': (current_slice.index[-1] - open_position['entry_time']).total_seconds() / 60
                    })
                    open_position = None
            else:
                signal = self.strategy.generate_signal(current_slice)
                if signal != 0 and risk_manager.can_trade(symbol):
                    stop_loss_price = current_price * (1 - risk_manager.stop_loss_percent / 100) if signal == 1 else current_price * (1 + risk_manager.stop_loss_percent / 100)
                    quantity = risk_manager.calculate_position_size(symbol, current_price, stop_loss_price)
                    if quantity > 0:
                        open_position = {
                            'signal': signal, 
                            'entry_price': current_price, 
                            'quantity': quantity,
                            'entry_time': current_slice.index[-1], 
                            'stop_loss': stop_loss_price
                        }

            equity_curve.append({'timestamp': current_slice.index[-1], 'equity': self.equity})

        if open_position:
            final_p = data['Close'].iloc[-1]
            pnl = (final_p - open_position['entry_price']) * open_position['quantity'] if open_position['signal'] == 1 else (open_position['entry_price'] - final_p) * open_position['quantity']
            self.equity += pnl
            self.trades.append({
                'entry_time': open_position['entry_time'],
                'exit_time': data.index[-1],
                'symbol': symbol,
                'signal': open_position['signal'],
                'entry_price': open_position['entry_price'],
                'exit_price': final_p,
                'quantity': open_position['quantity'],
                'pnl': pnl,
                'equity': self.equity,
                'duration_mins': (data.index[-1] - open_position['entry_time']).total_seconds() / 60
            })

        return self._calculate_metrics(symbol, start_date, end_date, equity_curve, timeframe)

    def _calculate_metrics(self, symbol, start, end, curve, timeframe):
        if not self.trades: return None
        df_equity = pd.DataFrame(curve).set_index('timestamp')
        returns = df_equity['equity'].pct_change().dropna()
        rolling_max = df_equity['equity'].cummax()
        drawdowns = (df_equity['equity'] - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()
        sharpe = (returns.mean() / returns.std() * np.sqrt(252 * 24)) if len(returns) > 1 and returns.std() != 0 else 0
        trades_df = pd.DataFrame(self.trades)
        wins = trades_df[trades_df['pnl'] > 0]
        losses = trades_df[trades_df['pnl'] <= 0]
        return {
            'symbol': symbol, 
            'start_date': str(start), 
            'end_date': str(end),
            'initial_equity': self.initial_equity, 
            'final_equity': self.equity,
            'total_return_pct': (self.equity - self.initial_equity) / self.initial_equity * 100,
            'max_drawdown_pct': max_drawdown * 100, 
            'sharpe_ratio': sharpe,
            'win_rate': (len(wins) / len(trades_df) * 100) if len(trades_df) > 0 else 0,
            'num_trades': len(trades_df), 
            'avg_win': wins['pnl'].mean() if not wins.empty else 0,
            'avg_loss': losses['pnl'].mean() if not losses.empty else 0,
            'profit_factor': abs(wins['pnl'].sum() / losses['pnl'].sum()) if not losses.empty and losses['pnl'].sum() != 0 else float('inf'),
            'trades': self.trades
        }

    def generate_report(self, results):
        print(f"Backtest report for {results['symbol']}:")
        print(f"  Total Return: {results['total_return_pct']:.2f}%")
        print(f"  Number of trades: {results['num_trades']}")

def main():
    config_path = 'config.yaml'
    backtester = TradingBacktester(config_path)
    scenarios = [
        # 5m timeframe for very short-term scalping
        {'symbol': 'DOGE/USDT', 'timeframe': '5m', 'days': 3},
        {'symbol': 'XRP/USDT', 'timeframe': '5m', 'days': 3},
        {'symbol': 'ADA/USDT', 'timeframe': '5m', 'days': 3},
        {'symbol': 'SOL/USDT', 'timeframe': '5m', 'days': 3},
        {'symbol': 'DOT/USDT', 'timeframe': '5m', 'days': 3},
        # 15m timeframe for short-term scalping
        {'symbol': 'DOGE/USDT', 'timeframe': '15m', 'days': 7},
        {'symbol': 'XRP/USDT', 'timeframe': '15m', 'days': 7},
        {'symbol': 'ADA/USDT', 'timeframe': '15m', 'days': 7},
        {'symbol': 'SOL/USDT', 'timeframe': '15m', 'days': 7},
        {'symbol': 'DOT/USDT', 'timeframe': '15m', 'days': 7},
        # 1h timeframe for intraday scalping
        {'symbol': 'DOGE/USDT', 'timeframe': '1h', 'days': 14},
        {'symbol': 'XRP/USDT', 'timeframe': '1h', 'days': 14},
        {'symbol': 'ADA/USDT', 'timeframe': '1h', 'days': 14},
        {'symbol': 'SOL/USDT', 'timeframe': '1h', 'days': 14},
        {'symbol': 'DOT/USDT', 'timeframe': '1h', 'days': 14},
        # 4h timeframe for swing scalping (holdings for a few hours)
        {'symbol': 'BTC/USDT', 'timeframe': '4h', 'days': 30},
        {'symbol': 'ETH/USDT', 'timeframe': '4h', 'days': 30},
        # Also include some majors on 1h for comparison
        {'symbol': 'BTC/USDT', 'timeframe': '1h', 'days': 14},
        {'symbol': 'ETH/USDT', 'timeframe': '1h', 'days': 14},
    ]
    all_results = []
    end = datetime.utcnow()
    for sc in scenarios:
        start = end - timedelta(days=sc['days'])
        logger.info(f"Running: {sc['symbol']} | {sc['timeframe']} | {sc['days']} days")
        res = backtester.run_backtest(sc['symbol'], start, end, sc['timeframe'])
        if res:
            all_results.append(res)
            print(f'Result: Return {res["total_return_pct"]:.2f}%, Max DD {res["max_drawdown_pct"]:.2f}%')
    if all_results:
        output_dir = 'backtest_logs'
        os.makedirs(output_dir, exist_ok=True)
        filename = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(os.path.join(output_dir, filename), 'w') as f:
            json.dump(all_results, f, default=str, indent=2)
        print(f"All results logged to {output_dir}/{filename}")

if __name__ == "__main__":
    main()
