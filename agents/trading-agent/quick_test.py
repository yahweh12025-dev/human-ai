#!/usr/bin/env python3
"""
Quick test script to compare GridStrategy vs SMACrossover for scalping.
Runs a small subset of symbols/timeframes for fast iteration.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading_agent import TradingAgent
from strategies.grid import GridStrategy
from strategies.sma_crossover import SMACrossover
from risk.manager import RiskManager
import ccxt
import pandas as pd
import numpy as np
import yaml
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("QuickTest")

def load_historical_data(symbol, timeframe='5m', days=1):
    """Load historical data for backtesting."""
    try:
        exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
        ohlcv = exchange.fetch_ohlcv(
            symbol, 
            timeframe=timeframe,
            since=int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000),
            limit=500
        )
        
        if not ohlcv: 
            return None
            
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        logger.warning(f"Error loading {symbol}: {e}")
        return None

def run_strategy_backtest(strategy_name, strategy, symbol, timeframe='5m', days=1):
    """Run backtest for a given strategy."""
    data = load_historical_data(symbol, timeframe, days)
    if data is None or len(data) < 30:
        logger.warning(f"Insufficient data for {symbol} {timeframe}")
        return None
        
    # Initialize risk manager
    risk_config = {
        'starting_equity': 10000.0,
        'max_risk_per_trade': 2.0,
        'stop_loss_percent': 5.0,
        'take_profit_percent': 15.0,
        'max_open_positions': 5,
        'max_daily_loss_percent': 10.0,
        'leverage': 3
    }
    risk_manager = RiskManager(risk_config)
    risk_manager.current_equity = risk_config['starting_equity']
    risk_manager.starting_equity = risk_config['starting_equity']
    
    equity = risk_config['starting_equity']
    trades = []
    open_position = None
    
    # Run backtest
    for i in range(30, len(data)):
        current_slice = data.iloc[:i+1]
        current_price = current_slice['Close'].iloc[-1]
        
        # Check exit conditions
        if open_position:
            exit_signal = risk_manager.check_exit_conditions(symbol, current_price)
            if exit_signal != 0:
                pnl = (current_price - open_position['entry_price']) * open_position['quantity'] if open_position['signal'] == 1 else (open_position['entry_price'] - current_price) * open_position['quantity']
                equity += pnl
                trades.append({
                    'entry_time': open_position['entry_time'],
                    'exit_time': current_slice.index[-1],
                    'symbol': symbol,
                    'signal': open_position['signal'],
                    'entry_price': open_position['entry_price'],
                    'exit_price': current_price,
                    'quantity': open_position['quantity'],
                    'pnl': pnl,
                    'equity': equity,
                    'duration_mins': (current_slice.index[-1] - open_position['entry_time']).total_seconds() / 60
                })
                open_position = None
        else:
            # Generate signal
            signal = strategy.generate_signal(current_slice)
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
    
    # Close any open position at the end
    if open_position:
        final_price = data['Close'].iloc[-1]
        pnl = (final_price - open_position['entry_price']) * open_position['quantity'] if open_position['signal'] == 1 else (open_position['entry_price'] - final_price) * open_position['quantity']
        equity += pnl
        trades.append({
            'entry_time': open_position['entry_time'],
            'exit_time': data.index[-1],
            'symbol': symbol,
            'signal': open_position['signal'],
            'entry_price': open_position['entry_price'],
            'exit_price': final_price,
            'quantity': open_position['quantity'],
            'pnl': pnl,
            'equity': equity,
            'duration_mins': (data.index[-1] - open_position['entry_time']).total_seconds() / 60
        })
    
    # Calculate metrics
    if not trades:
        return None
        
    returns = pd.Series([t['pnl'] for t in trades])
    wins = returns[returns > 0]
    losses = returns[returns <= 0]
    
    total_return_pct = (equity - risk_config['starting_equity']) / risk_config['starting_equity'] * 100
    win_rate = (len(wins) / len(trades) * 100) if len(trades) > 0 else 0
    avg_win = wins.mean() if not wins.empty else 0
    avg_loss = losses.mean() if not losses.empty else 0
    profit_factor = abs(wins.sum() / losses.sum()) if not losses.empty and losses.sum() != 0 else float('inf')
    
    return {
        'strategy': strategy_name,
        'symbol': symbol,
        'timeframe': timeframe,
        'total_return_pct': total_return_pct,
        'win_rate': win_rate,
        'num_trades': len(trades),
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'final_equity': equity
    }

def main():
    logger.info("Starting quick strategy comparison for scalping")
    
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Test symbols and timeframes
    test_cases = [
        {'symbol': 'DOGE/USDT', 'timeframe': '5m', 'days': 1},
        {'symbol': 'XRP/USDT', 'timeframe': '5m', 'days': 1},
        {'symbol': 'ADA/USDT', 'timeframe': '5m', 'days': 1},
    ]
    
    # Initialize strategies
    grid_strategy = GridStrategy(config['strategy']['grid'])
    smac_strategy = SMACrossover(config['futures']['sma_crossover'])
    
    results = []
    
    for case in test_cases:
        symbol = case['symbol']
        timeframe = case['timeframe']
        days = case['days']
        
        logger.info(f"Testing {symbol} {timeframe} for {days} day(s)")
        
        # Test Grid Strategy
        grid_result = run_strategy_backtest("Grid", grid_strategy, symbol, timeframe, days)
        if grid_result:
            results.append(grid_result)
            logger.info(f"  Grid Strategy: Return={grid_result['total_return_pct']:.2f}%, Trades={grid_result['num_trades']}, Win Rate={grid_result['win_rate']:.1f}%")
        
        # Test SMACrossover Strategy
        smac_result = run_strategy_backtest("SMACrossover", smac_strategy, symbol, timeframe, days)
        if smac_result:
            results.append(smac_result)
            logger.info(f"  SMACrossover: Return={smac_result['total_return_pct']:.2f}%, Trades={smac_result['num_trades']}, Win Rate={smac_result['win_rate']:.1f}%")
    
    # Summary
    logger.info("\n=== SUMMARY ===")
    for result in results:
        logger.info(f"{result['strategy']} {result['symbol']} {result['timeframe']}: "
                   f"Return={result['total_return_pct']:.2f}%, "
                   f"Trades={result['num_trades']}, "
                   f"Win Rate={result['win_rate']:.1f}%, "
                   f"Profit Factor={result['profit_factor']:.2f}")

if __name__ == "__main__":
    main()