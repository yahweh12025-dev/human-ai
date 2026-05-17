#!/usr/bin/env python3
"""
openclaw_manager.py — OpenClaw: Master orchestrator for all automode scripts.

OpenClaw manages and monitors:
  - autobinance.py  (Binance trading automation)
  - autoea.py       (EA MetaTrader 5 automation)
  - autosocial.py   (Video/social media automation)
  - autosync.py     (Backup/sync automation)
  - liveea.py       (EA trading agent)
  - live_trading_binance.py (Binance trading agent)

OpenClaw is the single source of truth for swarm health.
Run: python3 core/orchestration/openclaw_manager.py
"""
import json, os, signal, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR      = _PROJECT_ROOT / "data" / "logs"
_LOG_FILE     = _LOG_DIR / "openclaw_manager.log"
_PID_FILE     = _LOG_DIR / "openclaw_manager.pid"
_STATUS_FILE  = _LOG_DIR / "openclaw_status.json"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Managed processes
MANAGED_SCRIPTS = {
    "liveea":    {"script": "liveea.py",                  "match": "liveea.py",
                  "log": "data/logs/liveea.log",          "critical": True},
    "binance":   {"script": "startbinance.py",             "match": "live_trading_binance.py",
                  "log": "data/logs/live_trading_binance.log", "critical": True},
    "autobinance": {"script": "scripts/autobinance.py",    "match": "autobinance.py",
                    "log": "data/logs/autobinance.log",    "critical": False},
    "autoea":    {"script": "scripts/autoea.py",           "match": "autoea.py",
                  "log": "data/logs/autoea.log",           "critical": False},
    "autosocial": {"script": "scripts/autosocial.py",      "match": "autosocial.py",
                   "log": "data/logs/autosocial.log",      "critical": False},
    "autosync":  {"script": "scripts/autosync.py",         "match": "autosync.py",
                  "log": "data/logs/autosync.log",         "critical": False},
}

def _log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] [OPENCLAW] {msg}"
    print(line)
    with open(_LOG_FILE, "a") as f:
        f.write(line + "\n")

def _is_running(match: str) -> bool:
    try:
        r = subprocess.run(["pgrep", "-f", match], capture_output=True, text=True, timeout=5)
        return bool(r.stdout.strip())
    except Exception:
        return False

def _start(name: str, cfg: dict) -> bool:
    script = _PROJECT_ROOT / cfg["script"]
    if not script.exists():
        _log(f"[WARN] {name}: script not found: {script}")
        return False
    log_path = _PROJECT_ROOT / cfg["log"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    python = _PROJECT_ROOT / ".venv/bin/python3"
    if not python.exists():
        python = Path(sys.executable)
    with open(log_path, "a") as lf:
        subprocess.Popen(
            [str(python), "-u", str(script)],
            stdout=lf, stderr=lf,
            cwd=str(_PROJECT_ROOT),
            start_new_session=True,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
    _log(f"[START] {name}: {script.name}")
    return True

def _write_status(statuses: dict):
    status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "managed": statuses,
        "healthy": all(v["running"] for k, v in statuses.items() if MANAGED_SCRIPTS.get(k, {}).get("critical")),
    }
    _STATUS_FILE.write_text(json.dumps(status, indent=2))
    # Also write to vault
    try:
        from core.integrations.vault_logger import vault_log
        vault_log("openclaw", "HEALTH", "Swarm status check",
                  data={"healthy": status["healthy"], "agents": {k: v["running"] for k,v in statuses.items()}})
    except Exception:
        pass

def run():
    _log("OpenClaw Manager starting — managing all automode scripts")
    _PID_FILE.write_text(str(os.getpid()))
    
    running = True
    def _stop(*_):
        nonlocal running
        _log("OpenClaw stopping...")
        running = False
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    check_interval = 60  # seconds
    
    while running:
        statuses = {}
        for name, cfg in MANAGED_SCRIPTS.items():
            is_up = _is_running(cfg["match"])
            statuses[name] = {"running": is_up, "script": cfg["script"]}
            
            if not is_up:
                _log(f"[DOWN] {name} is not running")
                if _start(name, cfg):
                    _log(f"[RESTARTED] {name}")
                    statuses[name]["running"] = True
                    statuses[name]["restarted"] = True
                    time.sleep(5)  # give it time to start
        
        _write_status(statuses)
        
        # Print health summary
        health = " | ".join(f"{k}:{'✓' if v['running'] else '✗'}" for k,v in statuses.items())
        _log(f"[HEALTH] {health}")
        
        for _ in range(check_interval):
            if not running:
                break
            time.sleep(1)
    
    _log("OpenClaw Manager stopped")
    try: _PID_FILE.unlink()
    except: pass

def main():
    run()

if __name__ == "__main__":
    main()
