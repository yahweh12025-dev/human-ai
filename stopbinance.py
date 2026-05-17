#!/usr/bin/env python3
"""stopbinance.py — gracefully stop the Binance scalper (mirrors stopea.py pattern)"""
import os, sys, signal, time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
PID_FILE     = PROJECT_ROOT / "agents/trading-agent/trades/binance/binance_trader.pid"

def main():
    if not PID_FILE.exists():
        print("[BINANCE] No PID file found — Binance scalper may not be running.")
        sys.exit(0)

    try:
        pid = int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        print("[BINANCE] PID file unreadable.")
        sys.exit(1)

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        print(f"[BINANCE] Process {pid} not running — cleaning up.")
        PID_FILE.unlink(missing_ok=True)
        sys.exit(0)

    print(f"[BINANCE] Sending SIGTERM to PID {pid}...")
    os.kill(pid, signal.SIGTERM)

    # Wait up to 10s for graceful shutdown
    for i in range(10):
        time.sleep(1)
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            print(f"[BINANCE] Stopped gracefully (after {i+1}s)")
            PID_FILE.unlink(missing_ok=True)
            sys.exit(0)

    # Force kill if still alive
    print(f"[BINANCE] Still running after 10s — force killing...")
    os.kill(pid, signal.SIGKILL)
    PID_FILE.unlink(missing_ok=True)
    print("[BINANCE] Force stopped.")

if __name__ == "__main__":
    main()
