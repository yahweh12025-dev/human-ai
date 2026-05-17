#!/usr/bin/env python3
"""
autoea.py — Focused automode for EA MetaTrader 5 agent.

Manages:
  - Monitor liveea.py process, auto-restart if dead
  - HERMES-TRADE-REVIEW tasks specific to EA (reads liveea.log)
  - MT5 status.json freshness check — alerts if stale (>10 min)
  - EA daily P&L vs prop-firm limits (3% daily / 5% max drawdown)

Loop interval: 30 seconds
Log: data/logs/autoea.log
PID: data/logs/autoea.pid
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
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
    pass

# ── Import shared helpers from automode ───────────────────────
try:
    from automode import (
        _agent_log,
        query_deepseek,
        pidev_greedy_search,
        inject_idle_tasks,
        prune_completed,
        cleanup_queue,
        _LOG_DIR,
        _LOW_WATERMARK,
    )
    _AUTOMODE_AVAILABLE = True
except Exception:
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

    _LOW_WATERMARK = 5


# ── Constants ─────────────────────────────────────────────────
_LOG_FILE   = _LOG_DIR / "autoea.log"
_PID_FILE   = _LOG_DIR / "autoea.pid"
_TASKS_FILE = _PROJECT_ROOT / "unified_tasks.json"
_TRADE_LOOP = _PROJECT_ROOT / "core" / "orchestration" / "trading_improvement_loop.py"

_EA_SCRIPT      = _PROJECT_ROOT / "scripts" / "ea" / "liveea.py"
_EA_LOG         = _LOG_DIR / "liveea.log"
_MT5_STATUS     = _PROJECT_ROOT / "agents" / "trading-agent" / "trades" / "mt5" / "state.json"
_EA_TRADES_FEED = _PROJECT_ROOT / "data" / "feeds" / "ea_live_trades.jsonl"

_LOOP_INTERVAL       = 30   # seconds
_MT5_STALE_THRESHOLD = 10 * 60   # 10 minutes in seconds

# Prop-firm safety limits
_EA_DAILY_LOSS_PCT  = -3.0   # percent of equity
_EA_MAX_DD_PCT      = -5.0   # percent of equity

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
    _agent_log("autoea", msg)


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


# ── EA process monitor ────────────────────────────────────────

def _is_ea_running() -> bool:
    try:
        out = subprocess.check_output(["pgrep", "-f", "liveea.py"], text=True)
        return bool(out.strip())
    except subprocess.CalledProcessError:
        return False


def _restart_ea() -> None:
    if not _EA_SCRIPT.exists():
        _log(f"[MONITOR] EA script not found: {_EA_SCRIPT}")
        return
    _log("[MONITOR] Restarting liveea.py ...")
    _EA_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        fh = open(str(_EA_LOG), "a")
        subprocess.Popen(
            ["nohup", sys.executable, "-u", str(_EA_SCRIPT)],
            stdout=fh, stderr=subprocess.STDOUT,
            cwd=str(_PROJECT_ROOT),
            start_new_session=True,
        )
        _log("[MONITOR] EA agent restarted OK")
        _append_obs_health("EA", "RESTARTED")
    except Exception as exc:
        _log(f"[MONITOR] Failed to restart EA: {exc}")


def _monitor_ea_process() -> None:
    if _is_ea_running():
        _log("[MONITOR] EA (liveea.py): RUNNING")
    else:
        _log("[MONITOR] EA (liveea.py): DOWN — restarting")
        _restart_ea()


# ── Obsidian health log ───────────────────────────────────────

def _append_obs_health(agent_name: str, status: str) -> None:
    obs = _PROJECT_ROOT / "data" / "obsidian" / "System_State" / "agent_health.md"
    try:
        obs.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        with open(obs, "a") as f:
            f.write(f"\n## autoea monitor — {ts}\n")
            f.write(f"- {agent_name}: **{status}**\n---\n")
    except Exception:
        pass


# ── MT5 status.json freshness ─────────────────────────────────

def _check_mt5_status() -> None:
    if not _MT5_STATUS.exists():
        _log(f"[MT5] state.json not found at {_MT5_STATUS} — EA may not have written yet")
        return

    age_s = time.time() - _MT5_STATUS.stat().st_mtime
    age_min = age_s / 60.0
    if age_s > _MT5_STALE_THRESHOLD:
        _log(f"[MT5] WARNING: state.json is stale ({age_min:.1f} min old — threshold {_MT5_STALE_THRESHOLD//60} min)")
        _agent_log("autoea", f"[MT5-STALE] state.json age={age_min:.1f}min")
    else:
        _log(f"[MT5] state.json OK — {age_min:.1f} min old")

    # Also read and surface key fields
    try:
        state = json.loads(_MT5_STATUS.read_text())
        pnl_today = state.get("pnl_today", "N/A")
        last_trade = state.get("last_trade", "N/A")
        _log(f"[MT5] pnl_today={pnl_today}  last_trade={last_trade}")
    except Exception as exc:
        _log(f"[MT5] Could not parse state.json: {exc}")


# ── EA P&L / prop-firm limit check ───────────────────────────

def _check_ea_pnl() -> None:
    if not _EA_TRADES_FEED.exists():
        return
    today = datetime.now().strftime("%Y-%m-%d")
    total_pnl_pct = 0.0
    try:
        with open(_EA_TRADES_FEED) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("date", "").startswith(today):
                        total_pnl_pct += float(rec.get("pnl_pct", 0.0))
                except Exception:
                    continue
    except Exception:
        return

    _log(f"[PNL] EA daily P&L: {total_pnl_pct:.2f}%  (daily limit {_EA_DAILY_LOSS_PCT}%)")

    if total_pnl_pct <= _EA_DAILY_LOSS_PCT:
        _log(f"[PNL] ALERT: daily loss {total_pnl_pct:.2f}% breached {_EA_DAILY_LOSS_PCT}% limit!")
        _write_ea_alert("DAILY_LOSS_LIMIT", total_pnl_pct, _EA_DAILY_LOSS_PCT)

    if total_pnl_pct <= _EA_MAX_DD_PCT:
        _log(f"[PNL] CRITICAL: max drawdown {total_pnl_pct:.2f}% breached {_EA_MAX_DD_PCT}% limit!")
        _write_ea_alert("MAX_DRAWDOWN_LIMIT", total_pnl_pct, _EA_MAX_DD_PCT)


def _write_ea_alert(alert_type: str, current_pct: float, limit_pct: float) -> None:
    sig_path = _PROJECT_ROOT / "data" / "signals" / "ea_alert.json"
    sig_path.parent.mkdir(parents=True, exist_ok=True)
    sig_path.write_text(json.dumps({
        "alert_type": alert_type,
        "triggered_by": "autoea",
        "current_pnl_pct": current_pct,
        "limit_pct": limit_pct,
        "timestamp": datetime.now().isoformat(),
    }, indent=2))
    _agent_log("autoea", f"[ALERT] {alert_type} pnl={current_pct:.2f}%")


# ── HERMES-TRADE-REVIEW log check ─────────────────────────────

def _run_hermes_trade_review() -> None:
    """Read recent liveea.log and check for REVERSE / anomalies."""
    if not _EA_LOG.exists():
        _log("[HERMES-REVIEW] liveea.log not found — skipping")
        return

    try:
        lines = _EA_LOG.read_text(errors="replace").splitlines()
        recent = lines[-500:]
    except Exception as exc:
        _log(f"[HERMES-REVIEW] Could not read liveea.log: {exc}")
        return

    # Count REVERSE signals
    reverse_count = sum(1 for l in recent if "[REVERSE]" in l)
    error_lines = [l for l in recent if any(kw in l for kw in ("ERROR", "EXCEPTION", "Traceback", "FAILED"))]

    _log(f"[HERMES-REVIEW] liveea.log: last 500 lines — REVERSE={reverse_count}  errors={len(error_lines)}")

    if reverse_count > 5:
        _log(f"[HERMES-REVIEW] WARNING: {reverse_count} REVERSE signals in last 500 lines — consider reducing RANGE min_score")
        _agent_log("autoea", f"[REVERSE-ALERT] {reverse_count} REVERSE signals in last 500 log lines")

    if error_lines:
        _log(f"[HERMES-REVIEW] Recent errors (last 3):")
        for err in error_lines[-3:]:
            _log(f"  {err[:150]}")

    # Write POW
    pow_dir = _PROJECT_ROOT / "data" / "logs" / "pow"
    pow_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pow_file = pow_dir / f"ea_trade_review_{ts}.md"
    try:
        pow_file.write_text(
            f"# EA Trade Review — {ts}\n\n"
            f"**Source:** autoea.py HERMES-TRADE-REVIEW\n"
            f"**Date:** {datetime.now().isoformat()}\n\n"
            f"## Summary\n\n"
            f"- REVERSE signals (last 500 lines): {reverse_count}\n"
            f"- Error lines found: {len(error_lines)}\n\n"
            f"## Recent Errors\n\n"
            + "\n".join(f"- `{e[:200]}`" for e in error_lines[-10:])
            + "\n"
        )
        _log(f"[HERMES-REVIEW] POW written: {pow_file.name}")
    except Exception as exc:
        _log(f"[HERMES-REVIEW] Could not write POW: {exc}")


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


# ── Task injection for EA agents ──────────────────────────────

def _inject_ea_tasks() -> None:
    if not _TASKS_FILE.exists():
        return
    try:
        for agent in ("hermes_trade", "pidev_monitor"):
            injected = inject_idle_tasks(_TASKS_FILE, agent, _LOW_WATERMARK)
            if injected:
                _log(f"[INJECT] {injected} task(s) injected for agent '{agent}'")
    except Exception as exc:
        _log(f"[INJECT] Error: {exc}")


# ── Main loop ─────────────────────────────────────────────────

def main() -> None:
    global _running

    print("=" * 70)
    print("  autoea.py — EA MetaTrader 5 Automode")
    print(f"  Project root  : {_PROJECT_ROOT}")
    print(f"  Log           : {_LOG_FILE}")
    print(f"  PID           : {_PID_FILE}")
    print(f"  Loop interval : {_LOOP_INTERVAL}s")
    print(f"  MT5 stale thr : {_MT5_STALE_THRESHOLD//60} min")
    print(f"  Daily limit   : {_EA_DAILY_LOSS_PCT}%  Max DD: {_EA_MAX_DD_PCT}%")
    print(f"  automode      : {'available' if _AUTOMODE_AVAILABLE else 'UNAVAILABLE (standalone mode)'}")
    print("=" * 70)

    _write_pid()
    _log(f"[START] autoea started (PID={os.getpid()})")

    _loop_count = 0
    _review_every  = 20    # run HERMES-TRADE-REVIEW every ~10 min (20 * 30s)
    _trade_loop_every = 480  # run trading loop every ~4h (480 * 30s)

    try:
        while _running:
            _loop_count += 1
            _log(f"[LOOP #{_loop_count}] ---- autoea cycle ----")

            # 1. Monitor EA process — restart if dead
            _monitor_ea_process()

            # 2. MT5 status.json freshness check
            _check_mt5_status()

            # 3. Daily P&L / prop-firm limit check
            _check_ea_pnl()

            # 4. HERMES-TRADE-REVIEW log analysis every ~10 min
            if _loop_count % _review_every == 0:
                _run_hermes_trade_review()

            # 5. Inject EA-relevant tasks when queue is low
            if _loop_count % 5 == 0:
                _inject_ea_tasks()

            # 6. Trading improvement loop every ~4h
            if _loop_count % _trade_loop_every == 0:
                _run_trading_improvement_loop()

            # 7. Periodic queue cleanup
            if _loop_count % 20 == 0 and _TASKS_FILE.exists():
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
        _log("[STOP] autoea stopped cleanly")


if __name__ == "__main__":
    main()
