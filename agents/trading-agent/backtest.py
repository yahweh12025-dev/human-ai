import pandas as pd
import numpy as np
import logging
from datetime import datetime
import os
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import our strategy
from trading_strategy import TradingStrategy

class SimpleBacktest:
    def __init__(self, data_path, starting_equity=10000.0):
        self.data_path = data_path
        self.starting_equity = starting_equity
        self.current_equity = starting_equity
        self.strategy = TradingStrategy()
        
        # Trading parameters (should match strategy config)
        self.stop_loss_pct = 2.0
        self.take_profit_pct = 5.0
        self.max_risk_per_trade = 2.0
        
        # Backtest results
        self.trades = []
        self.equity_curve = [starting_equity]
        self.drawdowns = []
        self.position = None  # None or dict with entry_price, size, signal, entry_time
        
    def load_data(self):
        """Load OHLCV data from CSV"""
        logger.info(f"Loading data from {self.data_path}")
        df = pd.read_csv(self.data_path)
        # Ensure we have the required columns
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            # Try common alternatives
            if 'Timestamp' in df.columns:
                df = df.rename(columns={'Timestamp': 'timestamp'})
            if 'Open' in df.columns:
                df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
        
        # Convert timestamp to datetime if needed
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        
        logger.info(f"Loaded {len(df)} candles")
        return df
    
    def calculate_position_size(self, entry_price, stop_loss_price, score):
        """Calculate position size based on risk"""
        if entry_price == stop_loss_price:
            return 0
            
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share == 0:
            return 0
            
        # Use the strategy's position sizing logic
        # We'll use a simplified version: risk max_risk_per_trade% of equity
        risk_amount = self.current_equity * (self.max_risk_per_trade / 100)
        # Adjust by score (as in the strategy)
        risk_multiplier = {3: 1.0, 4: 1.5, 5: 2.0}.get(abs(score), 0.0)
        if risk_multiplier == 0.0:
            return 0
            
        adjusted_risk = risk_amount * risk_multiplier
        position_size = adjusted_risk / risk_per_share
        return position_size
    
    def run_backtest(self):
        """Run the backtest"""
        df = self.load_data()
        
        # We need enough data for indicators to warm up
        warmup_period = max(
            self.strategy.pivot_period,
            self.strategy.ema_slow,
            self.strategy.keltner_period,
            self.strategy.vol_window
        ) + 10
        
        logger.info(f"Warmup period: {warmup_period} candles")
        
        for i in range(warmup_period, len(df)):
            # Get data up to current candle
            current_data = df.iloc[:i+1].copy()
            current_candle = df.iloc[i]
            current_price = current_candle['close']
            current_time = current_data.index[i] if hasattr(current_data.index, 'i') else i
            
            # Generate signal
            signal = self.strategy.generate_signal(current_data)
            
            # If we have a position, check for exit
            if self.position is not None:
                # Calculate P&L
                if self.position['signal'] == 1:  # Long
                    pnl_pct = (current_price - self.position['entry_price']) / self.position['entry_price'] * 100
                else:  # Short
                    pnl_pct = (self.position['entry_price'] - current_price) / self.position['entry_price'] * 100
                
                # Check stop loss
                if self.position['signal'] == 1 and current_price <= self.position['stop_loss']:
                    exit_price = self.position['stop_loss']
                    exit_reason = 'stop_loss'
                elif self.position['signal'] == -1 and current_price >= self.position['stop_loss']:
                    exit_price = self.position['stop_loss']
                    exit_reason = 'stop_loss'
                # Check take profit
                elif self.position['signal'] == 1 and current_price >= self.position['take_profit']:
                    exit_price = self.position['take_profit']
                    exit_reason = 'take_profit'
                elif self.position['signal'] == -1 and current_price <= self.position['take_profit']:
                    exit_price = self.position['take_profit']
                    exit_reason = 'take_profit'
                # Check signal reversal (if signal goes opposite or neutral)
                elif signal * self.position['signal'] <= 0:
                    exit_price = current_price
                    exit_reason = 'signal_reversal'
                else:
                    # Continue holding
                    continue
                
                # Calculate P&L in currency
                if self.position['signal'] == 1:
                    pnl = (exit_price - self.position['entry_price']) * self.position['size']
                else:
                    pnl = (self.position['entry_price'] - exit_price) * self.position['size']
                
                # Update equity
                self.current_equity += pnl
                
                # Record trade
                trade = {
                    'entry_time': self.position['entry_time'],
                    'exit_time': current_data.index[i] if hasattr(current_data.index, 'i') else i,
                    'entry_price': self.position['entry_price'],
                    'exit_price': exit_price,
                    'size': self.position['size'],
                    'signal': self.position['signal'],
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason
                }
                self.trades.append(trade)
                self.equity_curve.append(self.current_equity)
                
                logger.info(f"Closed {exit_reason} trade: PnL={pnl:.2f}, Equity={self.current_equity:.2f}")
                
                # Reset position
                self.position = None
            
            # If no position and signal is strong enough, enter
            if self.position is None and abs(signal) >= 3:
                # Calculate stop loss and take profit based on ATR or fixed percentage
                # For simplicity, we'll use fixed percentage from entry price
                entry_price = current_price
                if signal == 1:  # Long
                    stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
                    take_profit = entry_price * (1 + self.take_profit_pct / 100)
                else:  # Short
                    stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
                    take_profit = entry_price * (1 - self.take_profit_pct / 100)
                
                # Calculate position size
                size = self.calculate_position_size(entry_price, stop_loss, signal)
                if size <= 0:
                    continue
                
                # Open position
                self.position = {
                    'entry_time': current_data.index[i] if hasattr(current_data.index, 'i') else i,
                    'entry_price': entry_price,
                    'size': size,
                    'signal': signal,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }
                
                logger.info(f"Opened {'Long' if signal==1 else 'Short'} at {entry_price:.2f}, size={size:.4f}")
        
        # If we still have a position at the end, close it at the last price
        if self.position is not None:
            last_price = df.iloc[-1]['close']
            last_time = df.index[-1]
            
            if self.position['signal'] == 1:
                pnl = (last_price - self.position['entry_price']) * self.position['size']
            else:
                pnl = (self.position['entry_price'] - last_price) * self.position['size']
            
            self.current_equity += pnl
            self.equity_curve.append(self.current_equity)
            
            trade = {
                'entry_time': self.position['entry_time'],
                'exit_time': last_time,
                'entry_price': self.position['entry_price'],
                'exit_price': last_price,
                'size': self.position['size'],
                'signal': self.position['signal'],
                'pnl': pnl,
                'pnl_pct': pnl / self.position['entry_price'] * 100,
                'exit_reason': 'end_of_data'
            }
            self.trades.append(trade)
            logger.info(f"Closed end_of_data trade: PnL={pnl:.2f}, Equity={self.current_equity:.2f}")
        
        # Calculate statistics
        self.calculate_statistics()
    
    def calculate_statistics(self):
        """Calculate backtest statistics"""
        if not self.trades:
            logger.warning("No trades recorded")
            return
        
        trades_df = pd.DataFrame(self.trades)
        profits = trades_df[trades_df['pnl'] > 0]['pnl']
        losses = trades_df[trades_df['pnl'] < 0]['pnl']
        
        total_trades = len(trades_df)
        winning_trades = len(profits)
        losing_trades = len(losses)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_profit = trades_df['pnl'].sum()
        avg_profit = profits.mean() if len(profits) > 0 else 0
        avg_loss = losses.mean() if len(losses) > 0 else 0
        profit_factor = abs(profits.sum() / losses.sum()) if losses.sum() != 0 else float('inf')
        
        # Max drawdown
        equity_series = pd.Series(self.equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100
        
        self.stats = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'starting_equity': self.starting_equity,
            'ending_equity': self.current_equity,
            'return_pct': (self.current_equity - self.starting_equity) / self.starting_equity * 100
        }
        
        logger.info("Backtest Statistics:")
        for key, value in self.stats.items():
            logger.info(f"  {key}: {value}")
    
    def save_results(self, output_dir):
        """Save backtest results to files"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save trades
        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            trades_df.to_csv(os.path.join(output_dir, 'trades.csv'), index=False)
        
        # Save equity curve
        equity_df = pd.DataFrame({'equity': self.equity_curve})
        equity_df.to_csv(os.path.join(output_dir, 'equity_curve.csv'), index=False)
        
        # Save statistics
        with open(os.path.join(output_dir, 'statistics.json'), 'w') as f:
            json.dump(self.stats, f, indent=4)
        
        # Save summary
        with open(os.path.join(output_dir, 'summary.txt'), 'w') as f:
            f.write("Backtest Summary\n")
            f.write("="*50 + "\n")
            for key, value in self.stats.items():
                f.write(f"{key}: {value}\n")
        
        logger.info(f"Results saved to {output_dir}")

def main():
    # Path to data
    data_path = "./data/btc_5m_ohlcv.csv"
    output_dir = "./backtest_results"
    
    # Run backtest with $5 starting equity as requested
    backtest = SimpleBacktest(data_path, starting_equity=5.0)
    backtest.run_backtest()
    backtest.save_results(output_dir)
    
    print(f"Backtest completed. Results saved to {output_dir}")

if __name__ == "__main__":
    main()