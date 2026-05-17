import json
import os
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('/home/yahwehatwork/human-ai/.env')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
VAULT_FILE = '/home/yahwehatwork/human-ai/agents/trading-agent/data/vault_state.json'
FREQTRADE_URL = 'http://localhost:8080'

def load_vault():
    try:
        with open(VAULT_FILE) as f:
            return json.load(f)
    except:
        return {'active_balance': 5.0, 'vault_balance': 0.0, 'total_deposited': 5.0, 'trades_today': 0, 'session_start_balance': 5.0, 'peak_balance': 5.0, 'circuit_breaker_active': False, 'circuit_breaker_until': None, 'daily_returns': [], 'vault_earn_rate': 0.0002}

def save_vault(state):
    Path(VAULT_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(VAULT_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def get_vault_pct(active_balance):
    if active_balance < 10:
        return 0.20
    elif active_balance < 100:
        return 0.30
    else:
        return 0.40

def process_trade_result(net_pnl: float):
    state = load_vault()

    if state.get('circuit_breaker_active'):
        return {'action': 'BLOCKED', 'reason': 'Circuit breaker active'}

    if net_pnl > 0:
        vault_pct = get_vault_pct(state['active_balance'])
        vault_contribution = net_pnl * vault_pct
        active_contribution = net_pnl * (1 - vault_pct)

        state['active_balance'] += active_contribution
        state['vault_balance'] += vault_contribution
        state['peak_balance'] = max(state['peak_balance'], state['active_balance'])
        state['vault_balance'] *= (1 + state['vault_earn_rate'])
        action = 'WIN_PROCESSED'
    else:
        state['active_balance'] += net_pnl
        drawdown = (state['session_start_balance'] - state['active_balance']) / state['session_start_balance']
        if drawdown >= 0.50:
            state['circuit_breaker_active'] = True
            state['circuit_breaker_until'] = (datetime.utcnow() + timedelta(hours=24)).isoformat()
            action = 'CIRCUIT_BREAKER_TRIGGERED'
        else:
            action = 'LOSS_PROCESSED'

    if SUPABASE_URL and SUPABASE_KEY:
        try:
            sb = create_client(SUPABASE_URL, SUPABASE_KEY)
            sb.table('trade_log').insert({
                'event': action,
                'active_balance': state['active_balance'],
                'vault_balance': state['vault_balance'],
                'timestamp': datetime.utcnow().isoformat()
            }).execute()
        except:
            pass

    state['trades_today'] += 1
    save_vault(state)
    return {'action': action, 'active_balance': state['active_balance'], 'vault_balance': state['vault_balance']}

def get_portfolio_summary():
    state = load_vault()
    total = state['active_balance'] + state['vault_balance']
    total_return_pct = ((total - state['total_deposited']) / state['total_deposited']) * 100
    return {
        'active_balance': round(state['active_balance'], 4),
        'vault_balance': round(state['vault_balance'], 4),
        'total_value': round(total, 4),
        'total_return_pct': round(total_return_pct, 2),
        'circuit_breaker_active': state.get('circuit_breaker_active', False)
    }
