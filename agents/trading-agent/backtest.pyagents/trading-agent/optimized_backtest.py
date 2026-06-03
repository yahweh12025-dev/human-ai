import pandas as pd
import numpy as np
import logging
from datetime import datetime
import os
import json

# Set up logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import our strategy
from trading_strategy import TradingStrategy

class OptimizedBacktest:
    def __init__(self, data_path, starting_equity=5.0):
        self.data_path = data_path
        self.starting_equity = starting_equity
        self.current_equity = starting_equity
        self.strategy = TradingStrategy()
        
        # Trading parameters
        self.stop_loss_pct = 2.0
        self.take_profit_pct = 5.0
        self.max_risk_per_trade = 2.0
        self.fee_rate = 0.001  # 0.1% fee per trade
        self.slippage = 0.0005  # 0.05% slippage
        
        # Backtest results
        self.trades = []
        self.equity_curve = [starting_equity]
        self.position = None
        
    def load_data_sample(self, sample_size=5000):
        """Load a sample of data for fast backtesting"""
        logger.info(f"Loading data sample from {self.data_path}")
        df = pd.read_csv(self.data_path)
        
        # Ensure we have the required columns
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            # Try common alternatives
            if 'Timestamp' in df.columns:
                df = df.rename(columns={'Timestamp': 'timestamp'})
            if 'Open' in df.columns:
                df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Take a sample for fast testing
        if len(df) > sample_size:
            # Take recent data
            df = df.tail(sample_size)
        
        logger.info(f"Using {len(df)} candles for backtest")
        return df
    
    def calculate_position_size(self, entry_price, stop_loss_price, score):
        """Calculate position size based on risk"""
        if entry_price == stop_loss_price:
            return 0
            
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share == 0:
            return 0
            
        risk_amount = self.current_equity * (self.max_risk_per_trade / 100)
        risk_multiplier = {3: 1.0, 4: 1.5, 5: 2.0}.get(abs(score), 0.0)
        if risk_multiplier == 0.0:
            return 0
            
        adjusted_risk = risk_amount * risk_multiplier
        position_size = adjusted_risk / risk_per_share
        return position_size
    
    def run_backtest(self):
        """Run the optimized backtest with AI suggestions"""
        df = self.load_data_sample(5000)  # Small sample for speed
        
        # Calculate strategy signals for the whole dataframe at once (vectorization)
        logger.info("Calculating strategy signals...")
        df = self.calculate_all_signals(df)
        
        # Simulate trades
        logger.info("Simulating trades...")
        for idx, row in df.iterrows():
            current_price = row['close']
            high_price = row['high']
            low_price = row['low']
            
            # --- EXIT LOGIC ---
            if self.position is not None:
                exit_price = None
                exit_reason = None
                
                # Check Intracandle Stop Loss and Take Profit using High/Low
                if self.position['signal'] == 1:  # Long
                    if low_price <= self.position['stop_loss']:
                        exit_price = self.position['stop_loss'] * (1 - self.slippage)
                        exit_reason = 'stop_loss'
                    elif high_price >= self.position['take_profit']:
                        exit_price = self.position['take_profit']  # TP is limit order
                        exit_reason = 'take_profit'
                else:  # Short
                    if high_price >= self.position['stop_loss']:
                        exit_price = self.position['stop_loss'] * (1 + self.slippage)
                        exit_reason = 'stop_loss'
                    elif low_price <= self.position['take_profit']:
                        exit_price = self.position['take_profit']
                        exit_reason = 'take_profit'
                
                # Check Signal Reversal (using next candle's open approximated by current close)
                if not exit_price and row['signal'] * self.position['signal'] <= 0:
                    exit_price = current_price * (1 - self.slippage if self.position['signal']==1 else 1 + self.slippage)
                    exit_reason = 'signal_reversal'
                
                # Process Exit
                if exit_price:
                    # Calculate PnL and deduct fees
                    if self.position['signal'] == 1:
                        gross_pnl = (exit_price - self.position['entry_price']) * self.position['size']
                    else:
                        gross_pnl = (self.position['entry_price'] - exit_price) * self.position['size']
                    
                    exit_value = exit_price * self.position['size']
                    fees = exit_value * self.fee_rate
                    net_pnl = gross_pnl - fees
                    
                    self.current_equity += net_pnl
                    
                    self.trades.append({
                        'entry_time': self.position['entry_time'],
                        'exit_time': idx,
                        'entry_price': self.position['entry_price'],
                        'exit_price': exit_price,
                        'size': self.position['size'],
                        'signal': self.position['signal'],
                        'net_pnl': net_pnl,
                        'exit_reason': exit_reason
                    })
                    self.equity_curve.append(self.current_equity)
                    self.position = None
            
            # --- ENTRY LOGIC ---
            # Enter on signal (using current price with slippage for realism)
            if self.position is None and abs(row['signal']) >= 3:
                # Apply slippage to entry price
                entry_price = current_price * (1 + self.slippage if row['signal'] == 1 else 1 - self.slippage)
                
                if row['signal'] == 1:
                    stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
                    take_profit = entry_price * (1 + self.take_profit_pct / 100)
                else:
                    stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
                    take_profit = entry_price * (1 - self.take_profit_pct / 100)
                
                size = self.calculate_position_size(entry_price, stop_loss, row['signal'])
                
                # Deduct entry fees
                entry_value = entry_price * size
                entry_fee = entry_value * self.fee_rate
                
                # Only enter if we have enough equity for fees
                if size > 0 and self.current_equity > entry_fee:
                    self.current_equity -= entry_fee  # pay fee
                    
                    self.position = {
                        'entry_time': idx,
                        'entry_price': entry_price,
                        'size': size,
                        'signal': row['signal'],
                        'stop_loss': stop_loss,
                        'take_profit': take_profit
                    }
        
        # If we still have a position at the end, close it
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
                'exit_reason': 'end_of_data'
            }
            self.trades.append(trade)
        
        # Calculate statistics
        self.calculate_statistics()
    
    def calculate_all_signals(self, df):
        """Calculate all strategy signals at once for performance"""
        # We'll calculate signals in a vectorized way where possible
        signals = []
        
        for i in range(len(df)):
            # Need enough data for indicators
            if i < max(self.strategy.pivot_period, self.strategy.ema_slow, self.strategy.keltner_period) + 10:
                signals.append(0)
                continue
            
            # Get data up to current point
            current_data = df.iloc[:i+1].copy()
            signal = self.strategy.generate_signal(current_data)
            signals.append(signal)
        
        df['signal'] = signals
        return df
    
    def calculate_statistics(self):
        """Calculate backtest statistics"""
        if not self.trades:
            logger.warning("No trades recorded")
            return
        
        trades_df = pd.DataFrame(self.trades)
        profits = trades_df[trades_df['net_pnl'] > 0]['net_pnl']
        losses = trades_df[trades_df['net_pnl'] < 0]['net_pnl']
        
        total_trades = len(trades_df)
        winning_trades = len(profits)
        losing_trades = len(losses)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_profit = trades_df['net_pnl'].sum()
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
        
        logger.info(f"Results saved to {output_dir}")

def run_backtest_iteration(data_path, iteration_num, starting_equity=5.0):
    """Run a single backtest iteration"""
    logger.info(f"=== Starting Backtest Iteration {iteration_num} ===")
    
    backtest = OptimizedBacktest(data_path, starting_equity=starting_equity)
    backtest.run_backtest()
    
    output_dir = f"./backtest_results_iter_{iteration_num}"
    backtest.save_results(output_dir)
    
    return backtest.stats

def main():
    # Use the same data but different samples for each iteration
    data_path = "./data/btc_5m_ohlcv.csv"
    
    # Run two iterations with different data samples
    all_results = []
    
    for i in [1, 2]:
        # Use different parts of the data for each iteration
        if i == 1:
            # First iteration: use middle section
            temp_path = "./data/btc_5m_ohlcv_middle.csv"
            df = pd.read_csv(data_path)
            # Take middle 20000 rows
            start_idx = len(df) // 4
            end_idx = start_idx + 20000
            df_sample = df.iloc[start_idx:end_idx]
            df_sample.to_csv(temp_path, index=False)
            data_to_use = temp_path
        else:
            # Second iteration: use recent section
            temp_path = "./data/btc_5m_ohlcv_recent.csv"
            df = pd.read_csv(data_path)
            # Take last 20000 rows
            df_sample = df.tail(20000)
            df_sample.to_csv(temp_path, index=False)
            data_to_use = temp_path
        
        stats = run_backtest_iteration(data_to_use, i, starting_equity=5.0)
        all_results.append((i, stats))
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    # Now ask AI for improvements based on both runs
    ask_ai_for_improvements(all_results)

def ask_ai_for_improvements(results):
    """Ask the AI for improvements based on backtest results"""
    import requests
    import json
    
    url = "http://0.0.0.0:4000/v1/chat/completions"
    headers = {
        "Authorization": "Bearer sk-1234",
        "Content-Type": "application/json"
    }
    
    # Format results for AI
    results_text = ""
    for i, stats in results:
        results_text += f"\nIteration {i}:\n"
        for key, value in stats.items():
            results_text += f"  {key}: {value}\n"
    
    prompt = f"""Based on these two backtest iterations of an optimized trading strategy, please suggest specific improvements:

{results_text}

Please focus on:
1. Strategy parameter optimization based on observed performance
2. Risk management adjustments
3. Signal generation improvements
4. Any patterns you see in the wins/losses
5. Specific changes to make to the trading strategy or backtest framework

Provide actionable recommendations."""

    data = {
        "model": "gemini-3.1-pro-preview",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()
        ai_response = result['choices'][0]['message']['content']
        
        print("\n" + "="*60)
        print("AI IMPROVEMENT SUGGESTIONS")
        print("="*60)
        print(ai_response)
        print("="*60)
        
        # Save AI suggestions
        with open("./human-ai/agents/trading-agent/ai_improvements.txt", "w") as f:
            f.write("Backtest Results:\n")
            for i, stats in results:
                f.write(f"\nIteration {i}:\n")
                for key, value in stats.items():
                    f.write(f"  {key}: {value}\n")
            f.write("\n\nAI Improvement Suggestions:\n")
            f.write(ai_response)
        
    except Exception as e:
        logger.error(f"Failed to get AI improvements: {e}")

if __name__ == "__main__":
    main()