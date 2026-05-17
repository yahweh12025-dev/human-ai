#!/usr/bin/env python3
"""
stopea.py — Stop the EA and close all MT5 positions
====================================================
Run from anywhere:
    python3 ~/human-ai/stopea.py

Does everything in one command:
  1. Sends SIGTERM to liveea.py process (EA closes positions itself on exit)
  2. Waits up to 30s for clean exit
  3. Force-kills if needed, then sends CLOSE signals to MT5 as fallback
  4. Sends CLOSE_ALL to MT5 as final belt-and-suspenders

Use this to stop trading and flatten all open positions.
"""
import json, os, sys, time, signal as _signal
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

PID_FILE    = PROJECT_ROOT / "agents" / "trading-agent" / "trades" / "mt5" / "ea_trader.pid"
STATE_FILE  = PROJECT_ROOT / "agents" / "trading-agent" / "trades" / "mt5" / "state.json"
MT5_FILES   = Path.home() / ".wine/drive_c/Program Files/MetaTrader 5/MQL5/Files"
SIGNAL_FILE = MT5_FILES / "python_signal.json"
RESULT_FILE = MT5_FILES / "python_result.json"


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ── MT5 position closing ──────────────────────────────────────

def _write_signal(action: str, symbol: str = "ALL") -> str:
    sig_id = f"{action}_{symbol}_{datetime.now().strftime('%H%M%S_%f')[:12]}"
    sig = {"id": sig_id, "action": action, "symbol": symbol,
           "lot": 0, "sl": 0, "tp": 0, "timestamp": datetime.now().isoformat()}
    SIGNAL_FILE.write_text(json.dumps(sig, separators=(",", ":")))
    return sig_id


def _wait_result(sig_id: str, timeout: float = 6.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if RESULT_FILE.exists():
            try:
                r = json.loads(RESULT_FILE.read_text())
                if r.get("sig_id") == sig_id:
                    return r
            except: pass
        time.sleep(0.4)
    return None


def close_mt5_positions():
    """Send CLOSE per symbol + CLOSE_ALL fallback to MT5."""
    if not MT5_FILES.exists():
        log("MT5 Files directory not found — skipping MT5 close signals")
        return

    # Check how many positions are open
    open_count = 0
    if STATE_FILE.exists():
        try:
            s = json.loads(STATE_FILE.read_text())
            open_count = s.get("open_positions", 0)
            if open_count:
                log(f"State file reports {open_count} open position(s)")
        except: pass

    # Send CLOSE per symbol
    for sym in ["XAUUSD", "XAGUSD"]:
        sig_id = _write_signal("CLOSE", sym)
        result = _wait_result(sig_id, timeout=6)
        status = "✓" if (result and result.get("success")) else "✗ (no response)"
        log(f"  CLOSE {sym}: {status}")
        time.sleep(1.2)

    # CLOSE_ALL fallback — catches anything per-symbol missed
    sig_id = _write_signal("CLOSE_ALL", "ALL")
    result = _wait_result(sig_id, timeout=8)
    log(f"  CLOSE_ALL: {'✓' if (result and result.get('success')) else '✗ (no response)'}")


# ── Process management ────────────────────────────────────────

def stop_ea_process() -> bool:
    """
    Send SIGTERM to liveea.py. The EA's _stop() handler sets running=False;
    _shutdown() then closes all MT5 positions before exiting.
    Returns True if process stopped cleanly.
    """
    if not PID_FILE.exists():
        log("No PID file — EA may not be running")
        return False

    try:
        pid = int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        log("Invalid PID file")
        PID_FILE.unlink(missing_ok=True)
        return False

    try:
        os.kill(pid, 0)   # check process exists
    except ProcessLookupError:
        log(f"PID {pid} not running (stale PID file)")
        PID_FILE.unlink(missing_ok=True)
        return False

    log(f"Sending SIGTERM to EA (PID {pid}) — will close positions then exit...")
    os.kill(pid, _signal.SIGTERM)

    # Wait up to 30s for clean exit
    for i in range(1, 31):
        time.sleep(1)
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            log(f"EA stopped cleanly after {i}s ✓")
            PID_FILE.unlink(missing_ok=True)
            return True
        if i % 5 == 0:
            log(f"  waiting... {i}s")

    # Force kill after 30s
    log(f"Force killing PID {pid}...")
    try:
        os.kill(pid, _signal.SIGKILL)
        time.sleep(1)
    except ProcessLookupError:
        pass
    PID_FILE.unlink(missing_ok=True)
    return False


# ── Main ─────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("STOP EA — Stop trading and close all positions")
    print("=" * 60)

    # Step 1: stop the Python process (it will close positions itself)
    clean = stop_ea_process()

    # Step 2: always send MT5 close signals as fallback
    # (even if process closed cleanly, belt-and-suspenders)
    log("Sending MT5 close signals as fallback...")
    close_mt5_positions()

    print("=" * 60)
    print("Done. EA stopped, all close signals sent.")
    print("Check MT5 terminal to confirm 0 open positions.")
    print("=" * 60)


if __name__ == "__main__":
    main()
