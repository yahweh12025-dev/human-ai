#!/usr/bin/env python3
"""
autobinance.py — Focused automode for Binance/crypto trading agents.

Manages:
  - hermes_trade, opencode_trade, pidev_monitor task banks
  - openclaw trading health tasks
  - Auto-restart of live_trading_binance.py if dead
  - Trading improvement loop (HERMES-TRADE-REVIEW, OPENCODE-TRADE-IMPLEMENT,
    PIDEV-AGENT-MONITOR)

Loop interval: 60 seconds
Log: data/logs/autobinance.log
PID: data/logs/autobinance.pid
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# ── Bootstrap project root ────────────────────────────────────
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = _HERE.parents[1]   # scripts/ → human-ai/
sys.path.insert(0, str(_PROJECT_ROOT))
os.chdir(str(_PROJECT_ROOT))

# ── Load .env ─────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(_PROJECT_ROOT / ".env")
except ImportError:
    pass  # dotenv optional — .env may be pre-loaded by shell

# ── Import shared helpers from automode ───────────────────────
try:
    from automode import (
        _agent_log,
        query_deepseek,
        pidev_greedy_search,
        inject_idle_tasks,
        prune_completed,
        cleanup_queue,
        _AGENT_TASK_BANK,
        _LOG_DIR,
        _LOW_WATERMARK,
    )
    _AUTOMODE_AVAILABLE = True
except Exception as _e:
    _AUTOMODE_AVAILABLE = False
    _LOG_DIR = _PROJECT_ROOT / "data" / "logs"

    def _agent_log(agent: str, msg: str) -> None:  # type: ignore[misc]
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        name = agent.lower().replace(".", "").replace(" ", "_")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(_LOG_DIR / f"{name}.log", "a") as f:
                f.write(f"[{ts}] {msg}\n")
        except Exception:
            pass

    def query_deepseek(prompt: str, **_kw) -> str:  # type: ignore[misc]
        return "[DeepSeek unavailable]"

    def pidev_greedy_search(pattern: str, **_kw) -> str:  # type: ignore[misc]
        return "[greedy search unavailable]"

    def inject_idle_tasks(*_a, **_kw) -> int:  # type: ignore[misc]
        return 0

    def prune_completed(*_a, **_kw) -> int:  # type: ignore[misc]
        return 0

    def cleanup_queue(*_a, **_kw) -> int:  # type: ignore[misc]
        return 0

    _AGENT_TASK_BANK: dict = {}  # type: ignore[misc]
    _LOW_WATERMARK = 5


# ── Constants ─────────────────────────────────────────────────
_LOG_FILE   = _LOG_DIR / "autobinance.log"
_PID_FILE   = _LOG_DIR / "autobinance.pid"
_TASKS_FILE = _PROJECT_ROOT / "unified_tasks.json"
_TRADE_LOOP = _PROJECT_ROOT / "core" / "orchestration" / "trading_improvement_loop.py"

_BINANCE_SCRIPT = _PROJECT_ROOT / "agents" / "trading-agent" / "live_trading_binance.py"
_BINANCE_LOG    = _LOG_DIR / "live_trading_binance.log"

_LOOP_INTERVAL  = 60   # seconds
_MONITOR_AGENTS = ["hermes_trade", "opencode_trade", "pidev_monitor", "openclaw"]

# Prop-firm / daily-loss limits
_BINANCE_DAILY_LOSS_LIMIT = -300.0  # USD

_running = True


# ── Logging ───────────────────────────────────────────────────

def _log(msg: str) -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(_LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass
    _agent_log("autobinance", msg)


# ── PID management ────────────────────────────────────────────

def _write_pid() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    _PID_FILE.write_text(str(os.getpid()))


def _remove_pid() -> None:
    try:
        _PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# ── Signal handling ───────────────────────────────────────────

def _handle_signal(signum: int, _frame: object) -> None:
    global _running
    _log(f"[SIGNAL] Received {signum} — shutting down")
    _running = False


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# ── Binance process monitor ───────────────────────────────────

def _is_binance_running() -> bool:
    try:
        out = subprocess.check_output(
            ["pgrep", "-f", "live_trading_binance.py"], text=True
        )
        return bool(out.strip())
    except subprocess.CalledProcessError:
        return False


def _restart_binance() -> None:
    if not _BINANCE_SCRIPT.exists():
        _log(f"[MONITOR] Binance script not found: {_BINANCE_SCRIPT}")
        return
    _log("[MONITOR] Restarting live_trading_binance.py ...")
    _BINANCE_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        fh = open(str(_BINANCE_LOG), "a")
        subprocess.Popen(
            ["nohup", sys.executable, "-u", str(_BINANCE_SCRIPT)],
            stdout=fh, stderr=subprocess.STDOUT,
            cwd=str(_PROJECT_ROOT),
            start_new_session=True,
        )
        _log("[MONITOR] Binance agent restarted OK")
        _append_obs_health("Binance", "RESTARTED")
    except Exception as exc:
        _log(f"[MONITOR] Failed to restart Binance: {exc}")


def _monitor_binance() -> None:
    if _is_binance_running():
        _log("[MONITOR] Binance: RUNNING")
    else:
        _log("[MONITOR] Binance: DOWN — restarting")
        _restart_binance()


# ── Obsidian health log ───────────────────────────────────────

def _append_obs_health(agent_name: str, status: str) -> None:
    obs = _PROJECT_ROOT / "data" / "obsidian" / "System_State" / "agent_health.md"
    try:
        obs.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        with open(obs, "a") as f:
            f.write(f"\n## autobinance monitor — {ts}\n")
            f.write(f"- {agent_name}: **{status}**\n---\n")
    except Exception:
        pass


# ── Daily P&L circuit breaker check ──────────────────────────

def _check_binance_pnl() -> None:
    feeds = _PROJECT_ROOT / "data" / "feeds" / "binance_live_trades.jsonl"
    if not feeds.exists():
        return
    today = datetime.now().strftime("%Y-%m-%d")
    total_pnl = 0.0
    try:
        with open(feeds) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("date", "").startswith(today):
                        total_pnl += float(rec.get("pnl", 0.0))
                except Exception:
                    continue
    except Exception:
        return

    if total_pnl <= _BINANCE_DAILY_LOSS_LIMIT:
        _log(f"[PNL-CHECK] WARNING: daily P&L {total_pnl:.2f} <= limit {_BINANCE_DAILY_LOSS_LIMIT}")
        sig_path = _PROJECT_ROOT / "data" / "signals" / "circuit_breaker.json"
        sig_path.parent.mkdir(parents=True, exist_ok=True)
        sig_path.write_text(json.dumps({
            "triggered_by": "autobinance",
            "agent": "binance",
            "daily_pnl": total_pnl,
            "limit": _BINANCE_DAILY_LOSS_LIMIT,
            "timestamp": datetime.now().isoformat(),
            "action": "HALT",
        }, indent=2))
        _agent_log("autobinance", f"[CIRCUIT-BREAKER] Binance daily loss {total_pnl:.2f} — HALT written")
    else:
        _log(f"[PNL-CHECK] Binance daily P&L: {total_pnl:.2f} (limit {_BINANCE_DAILY_LOSS_LIMIT})")


# ── Trading improvement loop ──────────────────────────────────

def _run_trading_improvement_loop() -> None:
    if not _TRADE_LOOP.exists():
        _log(f"[TRADE-LOOP] Script not found: {_TRADE_LOOP}")
        return
    _log("[TRADE-LOOP] Running trading_improvement_loop.py ...")
    try:
        result = subprocess.run(
            [sys.executable, str(_TRADE_LOOP)],
            capture_output=True, text=True, timeout=120,
            cwd=str(_PROJECT_ROOT),
        )
        out = (result.stdout + result.stderr).strip()
        _log(f"[TRADE-LOOP] exit={result.returncode} — {out[:200]}")
    except subprocess.TimeoutExpired:
        _log("[TRADE-LOOP] Timeout after 120s")
    except Exception as exc:
        _log(f"[TRADE-LOOP] Exception: {exc}")


# ── Task injection for Binance-relevant agents ────────────────

def _inject_binance_tasks() -> None:
    if not _TASKS_FILE.exists():
        return
    try:
        for agent in _MONITOR_AGENTS:
            injected = inject_idle_tasks(_TASKS_FILE, agent, _LOW_WATERMARK)
            if injected:
                _log(f"[INJECT] {injected} task(s) injected for agent '{agent}'")
    except Exception as exc:
        _log(f"[INJECT] Error: {exc}")


# ── Main loop ─────────────────────────────────────────────────

def main() -> None:
    global _running

    print("=" * 70)
    print("  autobinance.py — Binance Trading Automode")
    print(f"  Project root : {_PROJECT_ROOT}")
    print(f"  Log          : {_LOG_FILE}")
    print(f"  PID          : {_PID_FILE}")
    print(f"  Loop interval: {_LOOP_INTERVAL}s")
    print(f"  automode     : {'available' if _AUTOMODE_AVAILABLE else 'UNAVAILABLE (standalone mode)'}")
    print("=" * 70)

    _write_pid()
    _log(f"[START] autobinance started (PID={os.getpid()})")

    # Counters for scheduled sub-tasks
    _loop_count = 0
    _trade_loop_every = 240  # run trading improvement loop every ~4h (240 * 60s)

    try:
        while _running:
            _loop_count += 1
            _log(f"[LOOP #{_loop_count}] ---- autobinance cycle ----")

            # 1. Monitor Binance process
            _monitor_binance()

            # 2. Check daily P&L circuit breaker
            _check_binance_pnl()

            # 3. Inject tasks for Binance agents when queue is low
            _inject_binance_tasks()

            # 4. Run trading improvement loop every ~4h
            if _loop_count % _trade_loop_every == 0:
                _run_trading_improvement_loop()

            # 5. Prune / cleanup task queue periodically
            if _loop_count % 10 == 0 and _TASKS_FILE.exists():
                try:
                    cleanup_queue(_TASKS_FILE)
                    prune_completed(_TASKS_FILE)
                except Exception as exc:
                    _log(f"[CLEANUP] Error: {exc}")

            _log(f"[LOOP #{_loop_count}] Sleeping {_LOOP_INTERVAL}s ...")
            time.sleep(_LOOP_INTERVAL)

    except KeyboardInterrupt:
        _log("[STOP] KeyboardInterrupt — shutting down")
    finally:
        _running = False
        _remove_pid()
        _log("[STOP] autobinance stopped cleanly")


if __name__ == "__main__":
    main()
