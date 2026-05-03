import pandas as pd
import numpy as np
import os
import datetime
from collections import deque
# CHANGED: Relative import for the engine script location
from trading_strategy import TradingStrategy

# ==========================================
# GLOBAL CONFIGURATION
# ==========================================
STARTING_BALANCE = 5.0
MAX_LEVERAGE = 20
MAKER_FEE = -0.0002 
TAKER_FEE = 0.0004
MIN_NOTIONAL = 5.0
VAULT_TIERS = {10: 0.20, 100: 0.30, float('inf'): 0.40}
CIRCUIT_BREAKER = 0.50
ADX_HARVESTER = 28 

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def calculate_adx(df, period=14):
    df = df.copy()
    plus_dm = df['high'].diff()
    minus_dm = df['low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    tr = np.maximum(df['high'] - df['low'], 
                    np.maximum(abs(df['high'] - df['close'].shift(1)), 
                               abs(df['low'] - df['close'].shift(1))))
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    return adx, atr

def get_vault_pct(balance):
    for threshold, pct in VAULT_TIERS.items():
        if balance < threshold: return pct
    return 0.40

def is_funding_blackout(timestamp):
    hour, minute = timestamp.hour, timestamp.minute
    for r in [0, 8, 16]:
        if hour == r and minute >= 50: return True
        if hour == r and minute <= 5: return True
    return False

# ==========================================
# BACKTESTER ENGINE (Surgical Bridge to Strategy Class)
# ==========================================
def run_backtest(df_input, cycle_id, config_overrides=None):
    # Merge default config with overrides
    base_config = {
        'stop_loss_percent': 2.0,
        'take_profit_percent': 5.0,
        'max_risk_per_trade': 2.0,
        'vol_window': 100,
        'sma_fast': 10,
        'sma_slow': 30
    }
    if config_overrides:
        base_config.update(config_overrides)
    
    strategy = TradingStrategy(config=base_config)
    
    print(f"🚀 Initializing Cycle {cycle_id} | Config: {base_config}")
    
    df = df_input.copy()
    df['adx'], df['atr'] = calculate_adx(df)
    df['atr_pct'] = df['atr'].rolling(window=500).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1])
    df['funding_rate'] = np.random.uniform(-0.0001, 0.0003, len(df))
    
    active_balance = STARTING_BALANCE
    vault_balance = 0.0
    session_start_balance = STARTING_BALANCE
    
    trades = []
    equity_curve = []
    pending_orders = [] 
    current_positions = [] 
    
    for i in range(len(df)):
        row = df.iloc[i]
        ts, open_p, high, low, close, atr, atr_pct = row['timestamp'], row['open'], row['high'], row['low'], row['close'], row['atr'], row['atr_pct']
        
        if i % 288 == 0:
            session_start_balance = active_balance
            vault_balance *= 1.0002 
            
        if active_balance < session_start_balance * (1 - CIRCUIT_BREAKER):
            continue

        # Limit Order Fill Simulation
        still_pending = []
        if len(pending_orders) > 50: pending_orders = pending_orders[-50:]
        for order in pending_orders:
            dir, limit = order['direction'], order['limit_price']
            filled = (dir == 1 and low <= limit) or (dir == -1 and high >= limit)
            if filled:
                current_positions.append({
                    'direction': dir, 'entry_price': limit, 
                    'stop_loss': limit - (1.0*atr if dir==1 else -1.0*atr), 
                    'peak_price': limit, 'notional': order['notional']
                })
            else:
                still_pending.append(order)
        pending_orders = still_pending

        # Position Management using strategy.check_exit
        still_active = []
        for pos in current_positions:
            dir, entry, notional = pos['direction'], pos['entry_price'], pos['notional']
            peak_price = pos['peak_price']
            if dir == 1: peak_price = max(peak_price, high)
            else: peak_price = min(peak_price, low)
            
            # Calculate current score for the exit check
            data_slice = df.iloc[max(0, i-100):i+1]
            current_score = strategy.generate_signal(data_slice)
            
            # CALL STRATEGY CLASS FOR EXIT
            should_exit = strategy.check_exit(
                symbol="BTC", 
                current_price=close, 
                entry_price=entry, 
                signal=dir, 
                data=data_slice, 
                current_score=current_score, 
                hold_time=0, 
                current_equity=active_balance, 
                starting_equity=STARTING_BALANCE
            )
            
            if should_exit:
                exit_price = close 
                pnl_pct = ((exit_price - entry) / entry) if dir == 1 else ((entry - exit_price) / entry)
                net_pnl = pnl_pct * notional - (notional * TAKER_FEE)
                
                if net_pnl > 0:
                    v_pct = get_vault_pct(active_balance)
                    vault_amount = net_pnl * v_pct
                    vault_balance += vault_amount
                    active_balance += (net_pnl - vault_amount)
                else:
                    active_balance += net_pnl
                
                trades.append({
                    'timestamp': ts, 'direction': dir, 'entry_price': entry, 
                    'exit_price': exit_price, 'net_pnl': net_pnl, 'active_balance': active_balance
                })
            else:
                pos['peak_price'] = peak_price
                still_active.append(pos)
        
        current_positions = still_active

        # Entry Logic using strategy.generate_signal
        if not current_positions and not is_funding_blackout(ts):
            if active_balance * MAX_LEVERAGE < MIN_NOTIONAL: continue
            
            data_slice = df.iloc[max(0, i-100):i+1]
            score = strategy.generate_signal(data_slice)
            
            if abs(score) >= 3:
                dir = 1 if score > 0 else -1
                qty = strategy.calculate_position_size(
                    "BTC", close, 
                    close - (1.0*atr if dir==1 else -1.0*atr), 
                    active_balance, STARTING_BALANCE, score
                )
                notional = qty * close
                current_positions.append({'direction': dir, 'entry_price': close, 'stop_loss': close - (1.0*atr if dir==1 else -1.0*atr), 'peak_price': close, 'notional': notional})
        
        equity_curve.append([ts, active_balance, vault_balance])

    trades_df = pd.DataFrame(trades)
    equity_df = pd.DataFrame(equity_curve, columns=['timestamp', 'active_balance', 'vault_balance'])
    
    res_dir = f'results/cycle_{cycle_id}'
    os.makedirs(res_dir, exist_ok=True)
    trades_df.to_csv(f'{res_dir}/trades.csv', index=False)
    equity_df.to_csv(f'{res_dir}/equity_curve.csv', index=False)
    
    print(f"Cycle {cycle_id} Complete. Balance: ${active_balance:.2f}, Vault: ${vault_balance:.2f}")
    return trades_df, equity_df

if __name__ == "__main__":
    ohlcv = pd.read_csv('/home/yahwehatwork/human-ai/agents/trading-agent/data/btc_5m_ohlcv.csv')
    ohlcv['timestamp'] = pd.to_datetime(ohlcv['timestamp'])
    
    split_idx = int(len(ohlcv) * 0.8)
    is_data = ohlcv.iloc[:split_idx]
    oos_data = ohlcv.iloc[split_idx:]
    
    # RUN CYCLE 6: Volatility-Indexed Exit
    run_backtest(is_data, cycle_id="cycle_6_is")
    run_backtest(oos_data, cycle_id="cycle_6_oos")
