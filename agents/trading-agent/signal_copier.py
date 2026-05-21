from telethon import TelegramClient, events
import MetaTrader5 as mt5
import re
import logging
import os

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# --- CONFIG ---
# Loaded from environment for security
API_ID = 36643708
API_HASH = '223d3a77efe7d5649866d104321328ff'
CHANNEL_ID = 'gold_signalsr' # Using username/link as Telethon can resolve it
SYMBOL = 'XAUUSD'
VOLUME = 0.01 

# --- MT5 INIT ---
def init_mt5():
    if not mt5.initialize():
        log.error(f"MT5 init failed: {mt5.last_error()}")
        return False
    log.info("MT5 connected")
    return True

# --- SIGNAL PARSER ---
def parse_signal(text):
    text = text.upper()
    signal = {}

    # Direction
    if re.search(r'\bBUY\b|\bLONG\b', text):
        signal['type'] = mt5.ORDER_TYPE_BUY
    elif re.search(r'\bSELL\b|\bSHORT\b', text):
        signal['type'] = mt5.ORDER_TYPE_SELL
    else:
        return None # not a trade signal

    # Gold filter
    if not re.search(r'GOLD|XAU', text):
        return None

    # Entry price
    # Matches "NOW (4692-4695)" or "ENTRY: 4692"
    entry_match = re.search(r'(?:NOW\s*\(|ENTRY[:\s]*|@)(\d+\.?\d*)', text)
    signal['entry'] = float(entry_match.group(1)) if entry_match else None

    # Stop loss
    sl_match = re.search(r'STOP LOSS[:\s]*(\d+\.?\d*)', text)
    signal['sl'] = float(sl_match.group(1)) if sl_match else 0.0

    # Take profit (TP1)
    tp_match = re.search(r'TP1[:\s]*(\d+\.?\d*)', text)
    signal['tp'] = float(tp_match.group(1)) if tp_match else 0.0

    return signal

# --- TRADE EXECUTOR ---
def execute_trade(signal):
    if not mt5.terminal_info():
        if not init_mt5():
            return

    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        log.error(f"Can't get tick for {SYMBOL}")
        return

    price = tick.ask if signal['type'] == mt5.ORDER_TYPE_BUY else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": VOLUME,
        "type": signal['type'],
        "price": price,
        "sl": signal['sl'],
        "tp": signal['tp'],
        "deviation": 20,
        "magic": 123456,
        "comment": "tg_signal",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        log.error(f"Trade failed: {result.retcode} — {result.comment}")
    else:
        log.info(f"Trade opened: {signal['type']} {SYMBOL} @ {price} | ticket {result.order}")

# --- TELEGRAM LISTENER ---
client = TelegramClient('gold_session', API_ID, API_HASH)

@client.on(events.NewMessage(chats=CHANNEL_ID))
async def handle_signal(event):
    text = event.message.text
    log.info(f"New message: {text[:80]}")

    signal = parse_signal(text)
    if signal:
        log.info(f"Signal detected: {signal}")
        execute_trade(signal)
    else:
        log.info("Message ignored — not a trade signal")

# --- MAIN ---
if __name__ == '__main__':
    init_mt5()
    log.info("Listening for signals from @gold_signalsr...")
    client.start()
    client.run_until_disconnected()
