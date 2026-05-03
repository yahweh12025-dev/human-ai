import json
import os
import requests
from collections import deque
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('/home/yahwehatwork/human-ai/.env')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT = os.getenv('TELEGRAM_CHAT_ID', '')
MONITOR_FILE = '/home/yahwehatwork/human-ai/agents/trading-agent/data/edge_state.json'
BASELINE_FILE = '/home/yahwehatwork/human-ai/agents/trading-agent/data/baseline_stats.json'

def send_telegram(msg):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT:
        try:
            requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
                json={'chat_id': TELEGRAM_CHAT, 'text': f'[EDGE MONITOR] {msg}'}, timeout=10)
        except:
            pass

def load_baseline():
    try:
        with open(BASELINE_FILE) as f:
            return json.load(f)
    except:
        return {'win_rate': 0.54, 'profit_factor': 1.3, 'sample_size': 0}

def load_monitor():
    try:
        with open(MONITOR_FILE) as f:
            data = json.load(f)
            data['trades'] = deque(data['trades'], maxlen=500)
            return data
    except:
        return {'trades': deque(maxlen=500), 'alert_level': 'GREEN', 'position_multiplier': 1.0, 'halted': False}

def save_monitor(state):
    save_state = dict(state)
    save_state['trades'] = list(state['trades'])
    Path(MONITOR_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(MONITOR_FILE, 'w') as f:
        json.dump(save_state, f, indent=2)

def record_trade(win: bool, pnl: float):
    state = load_monitor()
    baseline = load_baseline()
    state['trades'].append({'win': win, 'pnl': pnl})

    if len(state['trades']) < 50:
        save_monitor(state)
        return state

    wins = sum(1 for t in state['trades'] if t['win'])
    rolling_wr = wins / len(state['trades'])
    baseline_wr = baseline['win_rate']
    drop = baseline_wr - rolling_wr

    prev_alert = state['alert_level']
    if drop >= 0.08:
        state['alert_level'] = 'RED'
        state['position_multiplier'] = 0.0
        state['halted'] = True
        if prev_alert != 'RED':
            send_telegram(f'RED ALERT: Win rate dropped {drop*100:.1f}% below baseline ({rolling_wr*100:.1f}% vs {baseline_wr*100:.1f}%). Trading HALTED for 24h.')
    elif drop >= 0.05:
        state['alert_level'] = 'YELLOW'
        state['position_multiplier'] = 0.5
        state['halted'] = False
        if prev_alert not in ['YELLOW', 'RED']:
            send_telegram(f'YELLOW ALERT: Win rate dropped {drop*100:.1f}% below baseline. Position size reduced 50%.')
    else:
        state['alert_level'] = 'GREEN'
        state['position_multiplier'] = 1.0
        state['halted'] = False

    save_monitor(state)
    return state

def get_edge_status():
    state = load_monitor()
    baseline = load_baseline()
    wins = sum(1 for t in state['trades'] if t['win'])
    total = len(state['trades'])
    rolling_wr = wins / total if total > 0 else 0
    return {
        'alert_level': state['alert_level'],
        'rolling_win_rate': round(rolling_wr, 4),
        'baseline_win_rate': baseline['win_rate'],
        'sample_size': total,
        'position_multiplier': state['position_multiplier'],
        'halted': state['halted']
    }
