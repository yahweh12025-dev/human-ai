#!/usr/bin/env python3
"""
MT5 Socket Bridge
Sends trade signals to MetaTrader 5 via TCP socket.
MT5 terminal must be running with the SocketSignalReceiver EA loaded.
Falls back to local file-based signals if socket unavailable.
"""

import json
import os
import socket
import time
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SIGNALS_DIR  = PROJECT_ROOT / "data" / "mt5_signals"
SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

MT5_HOST = "localhost"
MT5_PORT = 9999   # Port the MT5 EA listens on
MT5_TIMEOUT = 5


def send_signal(symbol: str, action: str, lot: float, sl: float = 0, tp: float = 0, comment: str = "PythonBridge") -> dict:
    """
    Send trade signal to MT5 via socket or file fallback.
    action: "BUY", "SELL", "CLOSE"
    """
    signal = {
        "action": action,
        "symbol": symbol,
        "lot": lot,
        "sl": sl,
        "tp": tp,
        "comment": comment,
        "timestamp": datetime.now().isoformat(),
    }

    # Try socket first
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(MT5_TIMEOUT)
            s.connect((MT5_HOST, MT5_PORT))
            msg = json.dumps(signal) + "\n"
            s.sendall(msg.encode())
            resp = s.recv(1024).decode().strip()
            logger.info(f"MT5 socket response: {resp}")
            return {"status": "sent_socket", "response": resp, "signal": signal}
    except (ConnectionRefusedError, socket.timeout, OSError):
        pass  # Fall through to file method

    # File-based signal (MT5 EA polls this file)
    sig_file = SIGNALS_DIR / f"signal_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    sig_file.write_text(json.dumps(signal, indent=2))

    # Also write to "pending" file MT5 EA reads
    pending = SIGNALS_DIR / "pending_signal.json"
    pending.write_text(json.dumps(signal, indent=2))

    logger.info(f"MT5 signal written to file: {sig_file.name}")
    return {"status": "sent_file", "file": str(sig_file), "signal": signal}


def check_mt5_running() -> bool:
    """Check if MT5 terminal is running under Wine"""
    try:
        import subprocess
        r = subprocess.run(["pgrep", "-f", "terminal64.exe"], capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False


def start_mt5_terminal() -> dict:
    """Launch MT5 terminal via Wine"""
    mt5_exe = Path.home() / ".wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"
    if not mt5_exe.exists():
        return {"status": "error", "error": "MT5 not found at expected path"}

    if check_mt5_running():
        return {"status": "already_running"}

    try:
        import subprocess
        p = subprocess.Popen(
            ["wine", str(mt5_exe)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(3)  # Give MT5 time to start
        return {"status": "started", "pid": p.pid}
    except Exception as e:
        return {"status": "error", "error": str(e)}
