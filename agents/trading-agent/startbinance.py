#!/usr/bin/env python3
"""startbinance.py — start the Binance scalper via nohup (mirrors liveea.py pattern)"""
import subprocess, sys, os, time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
BINANCE_SCRIPT = PROJECT_ROOT / "live_trading_binance.py"
LOG_FILE       = PROJECT_ROOT.parent / "data/logs/live_trading_binance.log"
PID_FILE       = PROJECT_ROOT / "trades/binance/binance_trader.pid"

def main():
    # Kill any stale instance
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            os.kill(old_pid, 0)
            print(f"[BINANCE] Already running (PID {old_pid}). Use stopbinance.py to stop first.")
            sys.exit(0)
        except (ProcessLookupError, ValueError):
            PID_FILE.unlink(missing_ok=True)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(LOG_FILE, "a")

    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    p = subprocess.Popen(
        [sys.executable, "-u", str(BINANCE_SCRIPT)],
        stdout=log_fh, stderr=log_fh,
        start_new_session=True,
        env=env,
        cwd=str(PROJECT_ROOT)
    )

    # Write launcher PID
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(p.pid))

    print(f"[BINANCE] Scalper started — PID {p.pid}")
    print(f"[BINANCE] Log: {LOG_FILE}")
    print("[BINANCE] Use stopbinance.py to stop gracefully")

    # Show first few lines to confirm startup
    time.sleep(5)
    import subprocess as sp
    last_lines = sp.run(["tail", "-8", str(LOG_FILE)], capture_output=True, text=True).stdout
    print(last_lines)

if __name__ == "__main__":
    main()
