import time
import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/home/yahwehatwork/human-ai/.env')

FREQTRADE_URL = 'http://localhost:8080'
FREQTRADE_USER = 'freqtrade'
FREQTRADE_PASS = os.getenv('FREQTRADE_API_PASS', 'your-password')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT = os.getenv('TELEGRAM_CHAT_ID', '')
HEARTBEAT_FILE = '/tmp/hyperscalper_heartbeat'
TIMEOUT_SECONDS = 90

def send_telegram(msg):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT:
        try:
            requests.post(
                f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
                json={'chat_id': TELEGRAM_CHAT, 'text': msg},
                timeout=10
            )
        except:
            pass

def close_all_positions():
    try:
        session = requests.Session()
        session.auth = (FREQTRADE_USER, FREQTRADE_PASS)

        r = session.post(f'{FREQTRADE_URL}/api/v1/token/login')
        token = r.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}'}

        trades = session.get(f'{FREQTRADE_URL}/api/v1/trades', headers=headers).json()

        for trade in trades.get('trades', []):
            session.post(
                f'{FREQTRADE_URL}/api/v1/forceexit',
                json={'tradeid': trade['trade_id'], 'ordertype': 'market'},
                headers=headers
            )

        send_telegram('DEAD MAN SWITCH ACTIVATED: All positions closed. Bot heartbeat lost.')
        return True
    except Exception as e:
        send_telegram(f'DEAD MAN SWITCH FAILED: {str(e)} - Manual intervention required immediately.')
        return False

def update_heartbeat():
    with open(HEARTBEAT_FILE, 'w') as f:
        f.write(str(time.time()))

def check_heartbeat():
    try:
        with open(HEARTBEAT_FILE) as f:
            last_beat = float(f.read().strip())
        return time.time() - last_beat < TIMEOUT_SECONDS
    except:
        return False

def run_monitor():
    send_telegram('Dead Man Switch monitoring started')
    while True:
        time.sleep(30)
        if not check_heartbeat():
            send_telegram('WARNING: Heartbeat lost. Attempting to close positions in 30s...')
            time.sleep(30)
            if not check_heartbeat():
                close_all_positions()
                time.sleep(300)

if __name__ == '__main__':
    run_monitor()
