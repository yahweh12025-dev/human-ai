#!/usr/bin/env python3
"""
Multi-Timeframe Live Test for Trading Agent
Tests strategy across 1min, 5min, 15min, 30min, 1h, 2h, 4h timeframes
"""
import sys
import os
import yaml
import pandas as pd
import numpy as np
import logging
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading_agent import TradingAgent
from strategies.sma_crossover import SMACrossover
from risk.manager import RiskManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MultiTFTester")

def test_timeframe(symbol, timeframe, days=7):
    """Test strategy on specific timeframe"""
    logger.info(f"Testing {symbol} on {timeframe} timeframe for {days} days")
    
    try:
        import ccxt
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        # Fetch historical data
        since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
        
        if not ohlcv or len(ohlcv) < 50:
            logger.warning(f"Insufficient data for {symbol} {timeframe}")
            return None
            
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Initialize components
        config_path = 'config.yaml'
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        strategy = SMACrossover(config['futures']['sma_crossover'])
        risk_config = config.get('risk', {})
        risk_manager = RiskManager(risk_config)
        risk_manager.current_equity = 10000.0
        risk_manager.starting_equity = 10000.0
        
        equity = 10000.0
        trades = []
        open_position = None
        
        # Process data
        for i in range(30, len(df)):
            current_slice = df.iloc[:i+1]
            current_price = current_slice["Close"].iloc[-1]
            
            # Calculate signal for entry check
            signal = strategy.generate_signal(current_slice)
            
            # Check exits if in position
            if open_position:
                exit_signal = risk_manager.check_exit_conditions(symbol, current_price)
                if exit_signal != 0:
                    pnl = (current_price - open_position["entry_price"]) * open_position["quantity"] if open_position["signal"] == 1 else (open_position["entry_price"] - current_price) * open_position["quantity"]
                    equity += pnl
                    trades.append({
                        "entry_time": open_position["entry_time"],
                        "exit_time": current_slice.index[-1],
                        "symbol": symbol,
                        "signal": open_position["signal"],
                        "entry_price": open_position["entry_price"],
                        "exit_price": current_price,
                        "quantity": open_position["quantity"],
                        "pnl": pnl,
                        "equity": equity,
                        "timeframe": timeframe
                    })
                    open_position = None
            
            # Check entries if not in position
            if open_position is None and signal != 0 and risk_manager.can_trade(symbol):
                if signal == 1:
                    stop_loss = current_price * (1 - risk_manager.stop_loss_percent / 100)
                else:
                    stop_loss = current_price * (1 + risk_manager.stop_loss_percent / 100)
                
                quantity = risk_manager.calculate_position_size(symbol, current_price, stop_loss)
                if quantity > 0:
                    open_position = {
                        "signal": signal,
                        "entry_price": current_price,
                        "quantity": quantity,
                        "entry_time": current_slice.index[-1],
                        "stop_loss": stop_loss
                    }
                    logger.info(f"Opened {timeframe} position: {symbol} @ {current_price}")
        
        # Close any remaining position
        if open_position:
            final_price = df['Close'].iloc[-1]
            pnl = (final_price - open_position['entry_price']) * open_position['quantity'] if open_position['signal'] == 1 else (open_position['entry_price'] - final_price) * open_position['quantity']
            equity += pnl
            trades.append({
                'entry_time': open_position['entry_time'],
                'exit_time': df.index[-1],
                'symbol': symbol,
                'signal': open_position['signal'],
                'entry_price': open_position['entry_price'],
                'exit_price': final_price,
                'quantity': open_position['quantity'],
                'pnl': pnl,
                'equity': equity,
                'timeframe': timeframe
            })
        
        total_return = (equity - 10000.0) / 10000.0 * 100
        win_rate = len([t for t in trades if t['pnl'] > 0]) / len(trades) * 100 if trades else 0
        
        logger.info(f"{timeframe} Results: Return {total_return:.2f}%, Trades {len(trades)}, Win Rate {win_rate:.1f}%")
        
        return {
            'timeframe': timeframe,
            'symbol': symbol,
            'days': days,
            'initial_equity': 10000.0,
            'final_equity': equity,
            'total_return_pct': total_return,
            'num_trades': len(trades),
            'win_rate': win_rate,
            'trades': trades
        }
        
    except Exception as e:
        logger.error(f"Error testing {symbol} {timeframe}: {e}")
        return None

def main():
    logger.info("="*60)
    logger.info("MULTI-TIMEFRAME LIVE TEST START")
    logger.info("="*60)
    
    timeframes = ['1m', '5m', '15m', '30m', '1h', '2h', '4h']
    results = []
    
    for tf in timeframes:
        # Test BTC/USDT
        result = test_timeframe('BTC/USDT', tf, days=2 if tf in ['1m', '5m'] else 7)
        if result:
            results.append(result)
        
        # Test ETH/USDT for shorter timeframes
        if tf in ['1m', '5m', '15m', '30m']:
            result = test_timeframe('ETH/USDT', tf, days=1 if tf == '1m' else 3)
            if result:
                results.append(result)
        
        time.sleep(1)  # Rate limiting
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("MULTI-TIMEFRAME TEST SUMMARY")
    logger.info("="*60)
    
    for res in results:
        logger.info(f"{res['symbol']} {res['timeframe']:>3} | Return: {res['total_return_pct']:>6.2f}% | "
                   f"Trades: {res['num_trades']:>2} | Win Rate: {res['win_rate']:>5.1f}%")
    
    # Save results
    import json
    os.makedirs('multi_tf_results', exist_ok=True)
    filename = f"multi_tf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(os.path.join('multi_tf_results', filename), 'w') as f:
        json.dump(results, f, default=str, indent=2)
    
    logger.info(f"\nResults saved to multi_tf_results/{filename}")
    logger.info("="*60)

if __name__ == "__main__":
    main()