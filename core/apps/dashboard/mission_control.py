#!/usr/bin/env python3
"""Mission Control v2 — Real-time swarm monitoring dashboard.

Flask + SocketIO with auto-refresh every 5 seconds.
Serves on port 10000.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit

# ---------------------------------------------------------------------------
# Paths
# Paths
PROJECT_ROOT  = Path(__file__).resolve().parents[3]
DATA_LOGS     = PROJECT_ROOT / "data" / "logs"
DATA_FEEDS    = PROJECT_ROOT / "data" / "feeds"
MEDIA_OUTPUT  = PROJECT_ROOT / "data" / "media_output"
TRADES_BIN    = PROJECT_ROOT / "agents" / "trading-agent" / "trades" / "binance"
TRADES_MT5    = PROJECT_ROOT / "agents" / "trading-agent" / "trades" / "mt5"
SYNC_STATUS   = PROJECT_ROOT / "data" / "obsidian" / "system" / "state" / "sync_status.json"
PID_BIN       = TRADES_BIN / "binance_trader.pid"
PID_MT5       = TRADES_MT5 / "ea_trader.pid"
PID_OPENCLAW  = DATA_LOGS / "openclaw_manager.pid"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _read_pid(path: Path) -> int | None:
    try:
        pid = int(Path(path).read_text().strip())
        os.kill(pid, 0)
        return pid
    except Exception:
        return None


def _is_running(path: Path) -> bool:
    return _read_pid(path) is not None


def _tail(path: Path, n: int = 10) -> list[str]:
    """Return last n non-empty lines from a log file. Never raises."""
    try:
        text = Path(path).read_text(errors="replace")
        lines = [l for l in text.splitlines() if l.strip()]
        return lines[-n:]
    except Exception:
        return []


def _read_json(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {}


def _pnl_cls(v: float) -> str:
    if v > 0:
        return "text-success"
    if v < 0:
        return "text-danger"
    return "text-secondary"


# ---------------------------------------------------------------------------
# Data collectors
# ---------------------------------------------------------------------------

def get_ea_data() -> dict:
    """EA Trader v10.1 tile data."""
    state = _read_json(TRADES_MT5 / "state.json")
    logs  = _tail(DATA_LOGS / "liveea.log", 5)
    running = _is_running(PID_MT5)

    balance     = state.get("balance", 0.0)
    equity      = state.get("equity",  0.0)
    open_pos    = state.get("open_positions", 0)
    floating    = state.get("floating_pnl",  0.0)
    pnl_today   = state.get("pnl_today",     0.0)
    mt5_live    = state.get("mt5_live",      False)
    session_on  = state.get("session_active", False)
    daily_loss  = state.get("daily_loss_pct", 0.0)
    drawdown    = state.get("drawdown_pct",   0.0)
    trade_count = state.get("trade_count",    0)
    symbols     = state.get("symbols_active", [])
    last_update = state.get("last_update",    "")

    # Derive session label from last log line
    session_label = "UNKNOWN"
    if logs:
        last = logs[-1]
        for tok in ["ASIAN", "LONDON", "NY", "AFTER_NY", "CLOSED"]:
            if tok in last.upper():
                session_label = tok
                break

    if running:
        if session_on:
            status = "running"
        else:
            status = "market_closed"
    else:
        status = "stopped"

    return {
        "status":        status,
        "running":       running,
        "mt5_live":      mt5_live,
        "balance":       balance,
        "equity":        equity,
        "open_positions": open_pos,
        "floating_pnl":  floating,
        "pnl_today":     pnl_today,
        "session":       session_label,
        "session_active": session_on,
        "daily_loss_pct": daily_loss,
        "drawdown_pct":  drawdown,
        "trade_count":   trade_count,
        "symbols":       symbols,
        "last_update":   last_update,
        "logs":          logs,
    }


def get_binance_data() -> dict:
    """Binance Scalper v11.1 tile data."""
    state   = _read_json(TRADES_BIN / "state.json")
    logs    = _tail(DATA_LOGS / "live_trading_binance.log", 5)
    running = _is_running(PID_BIN)

    balance   = state.get("current_balance", 0.0)
    pnl_today = state.get("pnl_today",       0.0)
    total_pnl = state.get("total_pnl",       0.0)
    open_pos  = state.get("open_positions",  0)
    symbols   = state.get("symbols",         [])

    # Parse W/L from last log line: W:3 L:5 | WR:37%
    wins = losses = win_rate = 0
    for line in reversed(logs):
        import re
        m = re.search(r"W:(\d+)\s+L:(\d+).*?WR:(\d+)%", line)
        if m:
            wins, losses, win_rate = int(m.group(1)), int(m.group(2)), int(m.group(3))
            break

    # Session from last log line
    session_label = "UNKNOWN"
    if logs:
        last = logs[-1]
        for tok in ["after_ny", "asian", "london", "ny"]:
            if tok in last.lower():
                session_label = tok.upper()
                break

    if running:
        status = "running"
    else:
        status = "stopped"

    return {
        "status":    status,
        "running":   running,
        "balance":   balance,
        "pnl_today": pnl_today,
        "total_pnl": total_pnl,
        "open_positions": open_pos,
        "wins":      wins,
        "losses":    losses,
        "win_rate":  win_rate,
        "session":   session_label,
        "symbols":   symbols,
        "logs":      logs,
    }


def get_openclaw_data() -> dict:
    """OpenClaw Manager tile data."""
    logs    = _tail(DATA_LOGS / "openclaw_manager.log", 5)
    running = _is_running(PID_OPENCLAW)

    # Parse the latest HEALTH line
    processes = []
    for line in reversed(logs):
        if "[HEALTH]" in line:
            # e.g.  liveea:✓ | binance:✓ | autobinance:✓ | ...
            parts = line.split("[HEALTH]")[-1].strip().split("|")
            for part in parts:
                part = part.strip()
                if ":" in part:
                    name, mark = part.split(":", 1)
                    processes.append({
                        "name":   name.strip(),
                        "ok":     "✓" in mark or mark.strip() == "OK",
                    })
            break

    # Fallback: check PIDs directly
    if not processes:
        for name, pid_file in [
            ("liveea",      DATA_LOGS / "liveea.pid"),
            ("binance",     DATA_LOGS / "binance.pid"),
            ("autobinance", PID_AUTOBIN),
            ("autoea",      PID_AUTOEA),
            ("autosocial",  PID_AUTOSOC),
            ("autosync",    PID_AUTOSYNC),
        ]:
            processes.append({"name": name, "ok": _is_running(pid_file)})

    return {
        "running":   running,
        "processes": processes,
        "logs":      logs,
    }


def get_agent_log(name: str, log_file: str, pid_file: Path | None = None, lines: int = 3) -> dict:
    """Generic agent tile — last N log lines + running status."""
    logs    = _tail(DATA_LOGS / log_file, lines)
    running = _is_running(pid_file) if pid_file else False
    return {"name": name, "running": running, "logs": logs}


def get_autosocial_data() -> dict:
    data = get_agent_log("AutoSocial", "autosocial.log", PID_AUTOSOC, 3)
    # Count videos
    video_count = 0
    try:
        for p in MEDIA_OUTPUT.iterdir():
            if p.is_dir():
                video_count += sum(1 for f in p.rglob("*.mp4"))
    except Exception:
        pass
    data["video_count"] = video_count
    return data


def get_autosync_data() -> dict:
    """AutoSync tile with per-integration status."""
    state = _read_json(SYNC_STATUS)
    results = state.get("results", {})
    last_sync = state.get("last_sync", "")

    integrations = []
    key_map = {
        "obsidian_gdrive": "Obsidian",
        "supabase_backup": "Supabase",
        "firebase_backup": "Firebase",
        "dify_sync":       "Dify",
        "graphify_sync":   "Graphify",
        "env_backup":      "Env Backup",
        "git_status_check": "Git",
    }
    for key, label in key_map.items():
        val = results.get(key, "")
        ok = val.startswith("OK") if val else False
        integrations.append({"name": label, "ok": ok, "detail": str(val)[:40]})

    running = _is_running(PID_AUTOSYNC)
    return {
        "running":      running,
        "last_sync":    last_sync,
        "integrations": integrations,
    }


def get_gdrive_data() -> dict:
    """GDrive tile — video counts + backup status."""
    faith_count = 0
    christian_count = 0
    try:
        fp = MEDIA_OUTPUT / "faithnexus"
        if fp.exists():
            faith_count = sum(1 for f in fp.rglob("*.mp4"))
        cp = MEDIA_OUTPUT / "christian"
        if cp.exists():
            christian_count = sum(1 for f in cp.rglob("*.mp4"))
    except Exception:
        pass

    # Latest backup log
    backup_logs = _tail(DATA_LOGS / "cloud_backup.log", 3)
    firebase_ok = any("firebase" in l.lower() and ("ok" in l.lower() or "success" in l.lower()) for l in backup_logs)
    supabase_ok = any("supabase" in l.lower() and ("ok" in l.lower() or "success" in l.lower()) for l in backup_logs)

    return {
        "faith_videos":    faith_count,
        "christian_videos": christian_count,
        "firebase_ok":     firebase_ok,
        "supabase_ok":     supabase_ok,
        "backup_logs":     backup_logs,
    }


def get_system_data() -> dict:
    """System tile — disk, CPU, memory, uptime."""
    try:
        disk  = psutil.disk_usage("/")
        cpu   = psutil.cpu_percent(interval=0.1)
        mem   = psutil.virtual_memory()
        boot  = psutil.boot_time()
        up_s  = time.time() - boot
        up_h  = int(up_s // 3600)
        up_m  = int((up_s % 3600) // 60)
        return {
            "disk_used_gb":  round(disk.used  / 1e9, 1),
            "disk_total_gb": round(disk.total / 1e9, 1),
            "disk_pct":      disk.percent,
            "cpu_pct":       cpu,
            "mem_used_gb":   round(mem.used   / 1e9, 1),
            "mem_total_gb":  round(mem.total  / 1e9, 1),
            "mem_pct":       mem.percent,
            "uptime":        f"{up_h}h {up_m}m",
        }
    except Exception as e:
        return {"error": str(e)}


def get_ea_feed() -> list[str]:
    return _tail(DATA_LOGS / "liveea.log", 10)


def get_binance_feed() -> list[str]:
    return _tail(DATA_LOGS / "live_trading_binance.log", 10)


def get_task_data() -> dict:
    tf = PROJECT_ROOT / "unified_tasks.json"
    if not tf.exists():
        return {"pending": 0, "in_progress": 0, "completed": 0}
    d  = _read_json(tf)
    tq = d.get("task_queue", {})
    return {
        "pending":     len(tq.get("pending",     [])),
        "in_progress": len(tq.get("in_progress", [])),
        "completed":   len(tq.get("completed",   [])),
    }


# ---------------------------------------------------------------------------
# Master payload
# ---------------------------------------------------------------------------

def build_payload() -> dict:
    return {
        "ts":           datetime.now(timezone.utc).isoformat(),
        "ea":           get_ea_data(),
        "binance":      get_binance_data(),
        "openclaw":     get_openclaw_data(),
        "autobinance":  get_agent_log("AutoBinance",  "autobinance.log",  PID_AUTOBIN, 3),
        "autoea":       get_agent_log("AutoEA",        "autoea.log",       PID_AUTOEA,  3),
        "autosocial":   get_autosocial_data(),
        "autosync":     get_autosync_data(),
        "gdrive":       get_gdrive_data(),
        "system":       get_system_data(),
        "ea_feed":      get_ea_feed(),
        "binance_feed": get_binance_feed(),
        "tasks":        get_task_data(),
    }


# ---------------------------------------------------------------------------
# Control actions
# ---------------------------------------------------------------------------

def ctrl_action(trader: str, action: str) -> dict:
    scripts = {
        "ea":      PROJECT_ROOT / "liveea.py",
        "binance": PROJECT_ROOT / "startbinance.py",
    }
    stop_scripts = {
        "ea":      PROJECT_ROOT / "stopea.py",
        "binance": PROJECT_ROOT / "stopbinance.py",
    }
    if trader not in scripts:
        return {"status": "error", "msg": "unknown trader"}
    if action == "start":
        pid_file = PID_MT5 if trader == "ea" else PID_BIN
        if _is_running(pid_file):
            return {"status": "already_running"}
        try:
            p = subprocess.Popen(
                ["python3", str(scripts[trader])],
                cwd=str(PROJECT_ROOT),
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {"status": "started", "pid": p.pid}
        except Exception as e:
            return {"status": "error", "msg": str(e)}
    elif action == "stop":
        try:
            r = subprocess.run(
                ["python3", str(stop_scripts[trader])],
                cwd=str(PROJECT_ROOT),
                capture_output=True, text=True, timeout=15,
            )
            return {"status": "stopped" if r.returncode == 0 else "error", "out": r.stdout[:200]}
        except Exception as e:
            return {"status": "error", "msg": str(e)}
    return {"status": "error", "msg": "unknown action"}


def run_sync() -> dict:
    try:
        p = subprocess.Popen(
            ["python3", str(PROJECT_ROOT / "scripts" / "autosync.py")],
            cwd=str(PROJECT_ROOT), start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return {"status": "started", "pid": p.pid}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


def produce_video() -> dict:
    try:
        p = subprocess.Popen(
            ["python3", "scripts/produce_video.py", "--topic", "XAUUSD analysis",
             "--platform", "tiktok", "--duration", "30"],
            cwd=str(PROJECT_ROOT), start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return {"status": "started", "pid": p.pid}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


def restart_all() -> dict:
    results = {}
    for t in ("ea", "binance"):
        results[t] = ctrl_action(t, "stop")
    time.sleep(2)
    for t in ("ea", "binance"):
        results[t + "_start"] = ctrl_action(t, "start")
    return results


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "mc-v2-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


# ---------------------------------------------------------------------------
# Background broadcaster (every 5 s)
# ---------------------------------------------------------------------------
_broadcast_lock = threading.Lock()

def _broadcast_loop():
    while True:
        try:
            payload = build_payload()
            with _broadcast_lock:
                socketio.emit("update", payload)
        except Exception as exc:
            pass
        time.sleep(5)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template_string(TEMPLATE)


@app.route("/api/status")
def api_status():
    from flask import jsonify
    return jsonify(build_payload())


@app.route("/api/ctrl/<trader>/<action>", methods=["POST"])
def api_ctrl(trader, action):
    from flask import jsonify
    return jsonify(ctrl_action(trader, action))


@app.route("/api/sync", methods=["POST"])
def api_sync():
    from flask import jsonify
    return jsonify(run_sync())


@app.route("/api/video", methods=["POST"])
def api_video():
    from flask import jsonify
    return jsonify(produce_video())


@app.route("/api/restart", methods=["POST"])
def api_restart():
    from flask import jsonify
    return jsonify(restart_all())


# ---------------------------------------------------------------------------
# SocketIO events
# ---------------------------------------------------------------------------
@socketio.on("connect")
def on_connect():
    try:
        emit("update", build_payload())
    except Exception:
        pass


@socketio.on("request_update")
def on_request_update():
    try:
        emit("update", build_payload())
    except Exception:
        pass


# ---------------------------------------------------------------------------
# HTML Template
# ---------------------------------------------------------------------------
TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mission Control v2 — Human-AI Swarm</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<style>
:root {
  --mc-bg:      #0d1117;
  --mc-card:    #161b22;
  --mc-border:  #21262d;
  --mc-green:   #3fb950;
  --mc-amber:   #d29922;
  --mc-red:     #f85149;
  --mc-blue:    #58a6ff;
  --mc-cyan:    #39d3f1;
  --mc-purple:  #bc8cff;
  --mc-muted:   #8b949e;
  --mc-text:    #c9d1d9;
}

*, *::before, *::after { box-sizing: border-box; }

body {
  background: var(--mc-bg);
  color: var(--mc-text);
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 13px;
  min-height: 100vh;
}

/* ── Header ── */
.mc-header {
  background: linear-gradient(90deg, #0d1117 0%, #0f1923 50%, #0d1117 100%);
  border-bottom: 1px solid var(--mc-border);
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
}
.mc-header h1 {
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 3px;
  color: var(--mc-cyan);
  text-shadow: 0 0 18px rgba(57,211,241,.35);
  margin: 0;
}
.mc-header .meta {
  text-align: right;
  font-size: .72rem;
  color: var(--mc-muted);
  line-height: 1.5;
}
.mc-header .meta #utc-clock {
  color: var(--mc-cyan);
  font-weight: 600;
}

/* ── Cards ── */
.mc-card {
  background: var(--mc-card);
  border: 1px solid var(--mc-border);
  border-radius: 10px;
  padding: 14px 16px;
  height: 100%;
  position: relative;
  overflow: hidden;
}
.mc-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  border-radius: 10px 10px 0 0;
}
.mc-card.accent-green::before  { background: linear-gradient(90deg, var(--mc-green), var(--mc-cyan)); }
.mc-card.accent-amber::before  { background: linear-gradient(90deg, var(--mc-amber), var(--mc-red)); }
.mc-card.accent-blue::before   { background: linear-gradient(90deg, var(--mc-blue),  var(--mc-purple)); }
.mc-card.accent-purple::before { background: linear-gradient(90deg, var(--mc-purple),var(--mc-blue)); }
.mc-card.accent-cyan::before   { background: linear-gradient(90deg, var(--mc-cyan),  var(--mc-green)); }
.mc-card.accent-muted::before  { background: linear-gradient(90deg, var(--mc-muted), var(--mc-border)); }

.mc-card-title {
  font-size: .68rem;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--mc-blue);
  border-bottom: 1px solid var(--mc-border);
  padding-bottom: 8px;
  margin-bottom: 10px;
}

/* ── Status badges ── */
.badge-running {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 20px;
  font-size: .6rem;
  font-weight: 700;
  letter-spacing: .5px;
  background: rgba(63,185,80,.12);
  color: var(--mc-green);
  border: 1px solid rgba(63,185,80,.4);
}
.badge-closed {
  background: rgba(210,153,34,.12);
  color: var(--mc-amber);
  border: 1px solid rgba(210,153,34,.4);
}
.badge-stopped {
  background: rgba(248,81,73,.1);
  color: var(--mc-red);
  border: 1px solid rgba(248,81,73,.35);
}
.badge-ok {
  background: rgba(63,185,80,.1);
  color: var(--mc-green);
  border: 1px solid rgba(63,185,80,.3);
}
.badge-fail {
  background: rgba(248,81,73,.1);
  color: var(--mc-red);
  border: 1px solid rgba(248,81,73,.3);
}

/* ── Dots ── */
.dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 5px;
  flex-shrink: 0;
}
.dot-green  { background: var(--mc-green);  box-shadow: 0 0 6px var(--mc-green); }
.dot-amber  { background: var(--mc-amber);  box-shadow: 0 0 6px var(--mc-amber); }
.dot-red    { background: var(--mc-red); }
.dot-muted  { background: var(--mc-muted); }

/* ── Data rows ── */
.data-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  border-bottom: 1px solid rgba(33,38,45,.8);
  font-size: .75rem;
}
.data-row:last-child { border-bottom: none; }
.data-row .lbl { color: var(--mc-muted); }
.data-row .val { font-weight: 700; }

/* ── Big metric ── */
.big-metric {
  font-size: 1.7rem;
  font-weight: 700;
  color: var(--mc-cyan);
  text-shadow: 0 0 12px rgba(57,211,241,.25);
  margin: 6px 0 2px;
  line-height: 1;
}
.big-metric.text-success { color: var(--mc-green); text-shadow: 0 0 12px rgba(63,185,80,.25); }
.big-metric.text-danger  { color: var(--mc-red);   text-shadow: none; }

/* ── Stat pills ── */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin-top: 10px;
}
.stat-pill {
  background: rgba(22,27,34,.9);
  border: 1px solid var(--mc-border);
  border-radius: 6px;
  padding: 6px 4px;
  text-align: center;
}
.stat-pill .sv { font-size: .9rem; font-weight: 700; }
.stat-pill .sk { font-size: .58rem; color: var(--mc-muted); margin-top: 2px; }

/* ── Log area ── */
.log-area {
  background: rgba(13,17,23,.8);
  border: 1px solid var(--mc-border);
  border-radius: 6px;
  padding: 8px 10px;
  max-height: 180px;
  overflow-y: auto;
  font-size: .68rem;
  font-family: 'Courier New', monospace;
  margin-top: 8px;
}
.log-area .log-line {
  color: #8b949e;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}
.log-area .log-line:last-child { color: var(--mc-text); }

/* ── Integration rows ── */
.int-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 3px 0;
  border-bottom: 1px solid rgba(33,38,45,.7);
  font-size: .72rem;
}
.int-row:last-child { border-bottom: none; }
.int-row .int-name { display: flex; align-items: center; }

/* ── Progress bar ── */
.mc-progress {
  height: 5px;
  border-radius: 3px;
  background: var(--mc-border);
  overflow: hidden;
  margin-top: 3px;
}
.mc-progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width .4s ease;
}
.fill-green  { background: var(--mc-green); }
.fill-amber  { background: var(--mc-amber); }
.fill-red    { background: var(--mc-red); }
.fill-blue   { background: var(--mc-blue); }

/* ── Action buttons ── */
.mc-btn {
  padding: 5px 13px;
  border-radius: 6px;
  font-size: .68rem;
  font-family: inherit;
  font-weight: 600;
  letter-spacing: .3px;
  cursor: pointer;
  border: 1px solid;
  transition: all .15s ease;
}
.mc-btn-green  { background: rgba(63,185,80,.1);  border-color: rgba(63,185,80,.5);  color: var(--mc-green); }
.mc-btn-green:hover  { background: rgba(63,185,80,.25); }
.mc-btn-red    { background: rgba(248,81,73,.1);   border-color: rgba(248,81,73,.45); color: var(--mc-red); }
.mc-btn-red:hover    { background: rgba(248,81,73,.22); }
.mc-btn-blue   { background: rgba(88,166,255,.1);  border-color: rgba(88,166,255,.4); color: var(--mc-blue); }
.mc-btn-blue:hover   { background: rgba(88,166,255,.22); }
.mc-btn-amber  { background: rgba(210,153,34,.1);  border-color: rgba(210,153,34,.45);color: var(--mc-amber); }
.mc-btn-amber:hover  { background: rgba(210,153,34,.22); }
.mc-btn-muted  { background: rgba(139,148,158,.08);border-color: rgba(139,148,158,.3);color: var(--mc-muted); }
.mc-btn-muted:hover  { background: rgba(139,148,158,.18); }

.btn-row { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }

/* ── Color utilities ── */
.text-green  { color: var(--mc-green) !important; }
.text-amber  { color: var(--mc-amber) !important; }
.text-red    { color: var(--mc-red)   !important; }
.text-cyan   { color: var(--mc-cyan)  !important; }
.text-muted-mc { color: var(--mc-muted) !important; }

/* ── Feed tile ── */
.feed-area {
  background: rgba(13,17,23,.9);
  border: 1px solid var(--mc-border);
  border-radius: 6px;
  padding: 8px 10px;
  max-height: 220px;
  overflow-y: auto;
  font-size: .68rem;
  font-family: 'Courier New', monospace;
  margin-top: 8px;
}
.feed-area .feed-line {
  line-height: 1.65;
  border-bottom: 1px solid rgba(33,38,45,.5);
  padding: 1px 0;
  white-space: pre-wrap;
  word-break: break-all;
  color: #8b949e;
}
.feed-area .feed-line:last-child { color: var(--mc-text); border-bottom: none; }

/* ── Toast ── */
#toast-container {
  position: fixed;
  bottom: 20px; right: 20px;
  z-index: 9999;
  display: flex; flex-direction: column; gap: 6px;
}
.mc-toast {
  background: var(--mc-card);
  border: 1px solid var(--mc-border);
  border-radius: 8px;
  padding: 10px 16px;
  font-size: .75rem;
  color: var(--mc-text);
  box-shadow: 0 4px 20px rgba(0,0,0,.5);
  animation: slideIn .2s ease;
  max-width: 280px;
}
@keyframes slideIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }

/* ── Refresh pulse ── */
.pulse-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--mc-green);
  display: inline-block;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%,100% { opacity: 1; box-shadow: 0 0 0 0 rgba(63,185,80,.6); }
  50%      { opacity: .6; box-shadow: 0 0 0 5px rgba(63,185,80,0); }
}

/* ── Layout ── */
.mc-main { padding: 12px; }
.mc-row  { margin-bottom: 12px; }
</style>
</head>
<body>

<!-- ══════════════ HEADER ══════════════ -->
<header class="mc-header">
  <h1>&#x1F916; Human-AI Swarm &mdash; Mission Control</h1>
  <div class="meta">
    <div><span class="pulse-dot"></span>&nbsp;<span id="utc-clock">--:--:-- UTC</span></div>
    <div id="last-refresh" style="margin-top:2px;">Connecting...</div>
  </div>
</header>

<div class="mc-main">

<!-- ══════════════ ROW 1: TRADING STATUS ══════════════ -->
<div class="row mc-row g-3">

  <!-- EA Trader v10.1 -->
  <div class="col-md-4">
    <div class="mc-card accent-green">
      <div class="mc-card-title d-flex justify-content-between align-items-center">
        <span>EA Trader v10.1</span>
        <span id="ea-badge" class="badge-stopped">STOPPED</span>
      </div>
      <div id="ea-src" style="font-size:.6rem; color:var(--mc-muted); margin-bottom:4px;"></div>
      <div id="ea-balance" class="big-metric">$0.00</div>
      <div id="ea-sub" style="font-size:.7rem; color:var(--mc-muted); margin-bottom:6px;"></div>
      <div class="stat-grid" id="ea-stats">
        <div class="stat-pill"><div class="sv text-muted-mc">—</div><div class="sk">Open Pos</div></div>
        <div class="stat-pill"><div class="sv text-muted-mc">—</div><div class="sk">Today PnL</div></div>
        <div class="stat-pill"><div class="sv text-muted-mc">—</div><div class="sk">Session</div></div>
      </div>
      <div class="stat-grid" id="ea-risk" style="margin-top:6px;">
        <div class="stat-pill"><div class="sv text-muted-mc">—</div><div class="sk">Daily Loss</div></div>
        <div class="stat-pill"><div class="sv text-muted-mc">—</div><div class="sk">Drawdown</div></div>
        <div class="stat-pill"><div class="sv text-muted-mc">—</div><div class="sk">Trades</div></div>
      </div>
      <div class="log-area" id="ea-log"><div class="log-line">Waiting for data...</div></div>
      <div class="btn-row">
        <button class="mc-btn mc-btn-green" onclick="ctrlTrader('ea','start')">&#9654; Start</button>
        <button class="mc-btn mc-btn-red"   onclick="ctrlTrader('ea','stop')">&#9632; Stop</button>
      </div>
    </div>
  </div>

  <!-- Binance v11.1 -->
  <div class="col-md-4">
    <div class="mc-card accent-amber">
      <div class="mc-card-title d-flex justify-content-between align-items-center">
        <span>Binance v11.1</span>
        <span id="bin-badge" class="badge-stopped">STOPPED</span>
      </div>
      <div id="bin-balance" class="big-metric">$0.00</div>
      <div id="bin-sub" style="font-size:.7rem; color:var(--mc-muted); margin-bottom:6px;"></div>
      <div class="stat-grid" id="bin-stats">
        <div class="stat-pill"><div class="sv text-muted-mc">—</div><div class="sk">Today PnL</div></div>
        <div class="stat-pill"><div class="sv text-muted-mc">—</div><div class="sk">W/L Record</div></div>
        <div class="stat-pill"><div class="sv text-muted-mc">—</div><div class="sk">Win Rate</div></div>
      </div>
      <div class="stat-grid" id="bin-stats2" style="margin-top:6px;">
        <div class="stat-pill"><div class="sv text-muted-mc">—</div><div class="sk">Open Pos</div></div>
        <div class="stat-pill"><div class="sv text-muted-mc">—</div><div class="sk">Session</div></div>
        <div class="stat-pill"><div class="sv text-muted-mc">—</div><div class="sk">Total PnL</div></div>
      </div>
      <div class="log-area" id="bin-log"><div class="log-line">Waiting for data...</div></div>
      <div class="btn-row">
        <button class="mc-btn mc-btn-green" onclick="ctrlTrader('binance','start')">&#9654; Start</button>
        <button class="mc-btn mc-btn-red"   onclick="ctrlTrader('binance','stop')">&#9632; Stop</button>
      </div>
    </div>
  </div>

  <!-- OpenClaw Manager -->
  <div class="col-md-4">
    <div class="mc-card accent-purple">
      <div class="mc-card-title d-flex justify-content-between align-items-center">
        <span>OpenClaw Manager</span>
        <span id="oc-badge" class="badge-stopped">STOPPED</span>
      </div>
      <div id="oc-processes"></div>
      <div class="log-area" id="oc-log"><div class="log-line">Waiting for data...</div></div>
    </div>
  </div>

</div><!-- /row 1 -->

<!-- ══════════════ ROW 2: AGENT ACTIVITY ══════════════ -->
<div class="row mc-row g-3">

  <!-- AutoBinance -->
  <div class="col-md-4">
    <div class="mc-card accent-blue">
      <div class="mc-card-title d-flex justify-content-between align-items-center">
        <span>AutoBinance</span>
        <span id="autobin-badge" class="badge-stopped">STOPPED</span>
      </div>
      <div class="log-area" id="autobin-log"><div class="log-line">Waiting...</div></div>
    </div>
  </div>

  <!-- AutoEA -->
  <div class="col-md-4">
    <div class="mc-card accent-blue">
      <div class="mc-card-title d-flex justify-content-between align-items-center">
        <span>AutoEA</span>
        <span id="autoea-badge" class="badge-stopped">STOPPED</span>
      </div>
      <div class="log-area" id="autoea-log"><div class="log-line">Waiting...</div></div>
    </div>
  </div>

  <!-- AutoSocial -->
  <div class="col-md-4">
    <div class="mc-card accent-blue">
      <div class="mc-card-title d-flex justify-content-between align-items-center">
        <span>AutoSocial</span>
        <span id="autosoc-badge" class="badge-stopped">STOPPED</span>
      </div>
      <div class="data-row">
        <span class="lbl">Videos produced</span>
        <span class="val text-cyan" id="video-count">—</span>
      </div>
      <div class="log-area" id="autosoc-log"><div class="log-line">Waiting...</div></div>
      <div class="btn-row">
        <button class="mc-btn mc-btn-muted" onclick="doVideo()">&#9654; Produce Video</button>
      </div>
    </div>
  </div>

</div><!-- /row 2 -->

<!-- ══════════════ ROW 3: INTEGRATIONS ══════════════ -->
<div class="row mc-row g-3">

  <!-- AutoSync -->
  <div class="col-md-4">
    <div class="mc-card accent-cyan">
      <div class="mc-card-title d-flex justify-content-between align-items-center">
        <span>AutoSync</span>
        <span id="sync-badge" class="badge-stopped">STOPPED</span>
      </div>
      <div class="data-row">
        <span class="lbl">Last sync</span>
        <span class="val" id="sync-last" style="font-size:.68rem;">—</span>
      </div>
      <div id="sync-ints" style="margin-top:6px;"></div>
      <div class="btn-row">
        <button class="mc-btn mc-btn-blue" onclick="doSync()">&#8593; Run Sync Now</button>
      </div>
    </div>
  </div>

  <!-- GDrive -->
  <div class="col-md-4">
    <div class="mc-card accent-cyan">
      <div class="mc-card-title">GDrive / Media</div>
      <div class="data-row">
        <span class="lbl">FaithNexus videos</span>
        <span class="val text-cyan" id="gd-faith">—</span>
      </div>
      <div class="data-row">
        <span class="lbl">Christian videos</span>
        <span class="val text-cyan" id="gd-christian">—</span>
      </div>
      <div class="data-row">
        <span class="lbl">Firebase backup</span>
        <span id="gd-firebase">—</span>
      </div>
      <div class="data-row">
        <span class="lbl">Supabase backup</span>
        <span id="gd-supabase">—</span>
      </div>
      <div class="log-area" id="gd-log"><div class="log-line">Waiting...</div></div>
    </div>
  </div>

  <!-- System -->
  <div class="col-md-4">
    <div class="mc-card accent-muted">
      <div class="mc-card-title">System</div>
      <div class="data-row">
        <span class="lbl">CPU</span>
        <span class="val" id="sys-cpu">—</span>
      </div>
      <div style="margin-top:2px;" id="sys-cpu-bar">
        <div class="mc-progress"><div class="mc-progress-fill fill-blue" id="sys-cpu-fill" style="width:0%"></div></div>
      </div>
      <div class="data-row" style="margin-top:6px;">
        <span class="lbl">Memory</span>
        <span class="val" id="sys-mem">—</span>
      </div>
      <div style="margin-top:2px;">
        <div class="mc-progress"><div class="mc-progress-fill fill-green" id="sys-mem-fill" style="width:0%"></div></div>
      </div>
      <div class="data-row" style="margin-top:6px;">
        <span class="lbl">Disk</span>
        <span class="val" id="sys-disk">—</span>
      </div>
      <div style="margin-top:2px;">
        <div class="mc-progress"><div class="mc-progress-fill fill-amber" id="sys-disk-fill" style="width:0%"></div></div>
      </div>
      <div class="data-row" style="margin-top:6px;">
        <span class="lbl">Uptime</span>
        <span class="val text-cyan" id="sys-uptime">—</span>
      </div>
      <div class="data-row">
        <span class="lbl">Tasks (pending / in-progress / done)</span>
        <span class="val" id="sys-tasks">—</span>
      </div>
    </div>
  </div>

</div><!-- /row 3 -->

<!-- ══════════════ ROW 4: LIVE FEEDS ══════════════ -->
<div class="row mc-row g-3">

  <!-- EA Live Feed -->
  <div class="col-md-6">
    <div class="mc-card accent-green">
      <div class="mc-card-title">EA Live Feed &mdash; liveea.log</div>
      <div class="feed-area" id="feed-ea"><div class="feed-line">Waiting for data...</div></div>
    </div>
  </div>

  <!-- Binance Live Feed -->
  <div class="col-md-6">
    <div class="mc-card accent-amber">
      <div class="mc-card-title">Binance Live Feed &mdash; live_trading_binance.log</div>
      <div class="feed-area" id="feed-bin"><div class="feed-line">Waiting for data...</div></div>
    </div>
  </div>

</div><!-- /row 4 -->

<!-- ══════════════ ROW 5: QUICK ACTIONS ══════════════ -->
<div class="row mc-row g-3">
  <div class="col-12">
    <div class="mc-card accent-muted">
      <div class="mc-card-title">Quick Actions</div>
      <div class="btn-row" style="flex-wrap:wrap;">
        <button class="mc-btn mc-btn-green" onclick="ctrlTrader('ea','start')">&#9654; Start EA</button>
        <button class="mc-btn mc-btn-red"   onclick="ctrlTrader('ea','stop')">&#9632; Stop EA</button>
        <button class="mc-btn mc-btn-green" onclick="ctrlTrader('binance','start')">&#9654; Start Binance</button>
        <button class="mc-btn mc-btn-red"   onclick="ctrlTrader('binance','stop')">&#9632; Stop Binance</button>
        <button class="mc-btn mc-btn-amber" onclick="doRestart()">&#8635; Restart All</button>
        <button class="mc-btn mc-btn-blue"  onclick="doSync()">&#8593; Run Sync Now</button>
        <button class="mc-btn mc-btn-muted" onclick="doVideo()">&#127916; Produce Video</button>
      </div>
    </div>
  </div>
</div><!-- /row 5 -->

</div><!-- /mc-main -->

<!-- Toast container -->
<div id="toast-container"></div>

<!-- SocketIO client -->
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
<script>
'use strict';

// ── UTC clock ──────────────────────────────────────────────────────────────
function tickClock() {
  const now = new Date();
  const pad = n => String(n).padStart(2,'0');
  document.getElementById('utc-clock').textContent =
    pad(now.getUTCHours())+':'+pad(now.getUTCMinutes())+':'+pad(now.getUTCSeconds())+' UTC';
}
tickClock();
setInterval(tickClock, 1000);

// ── Toast ──────────────────────────────────────────────────────────────────
function toast(msg, color) {
  const el = document.createElement('div');
  el.className = 'mc-toast';
  el.style.borderLeftColor = color || 'var(--mc-blue)';
  el.style.borderLeftWidth = '3px';
  el.textContent = msg;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ── Helpers ────────────────────────────────────────────────────────────────
function pnlColor(v) {
  return v > 0 ? 'var(--mc-green)' : v < 0 ? 'var(--mc-red)' : 'var(--mc-muted)';
}
function pnlStr(v) {
  const sign = v >= 0 ? '+' : '';
  return sign + '$' + Math.abs(v).toFixed(2);
}
function fmt(v, decimals) {
  return '$' + Number(v).toLocaleString('en', {minimumFractionDigits: decimals||2, maximumFractionDigits: decimals||2});
}
function statusBadgeClass(status) {
  if (status === 'running')       return 'badge-running';
  if (status === 'market_closed') return 'badge-closed';
  return 'badge-stopped';
}
function statusBadgeText(status) {
  if (status === 'running')       return 'LIVE';
  if (status === 'market_closed') return 'MKT CLOSED';
  return 'STOPPED';
}
function dotClass(ok) {
  return ok ? 'dot dot-green' : 'dot dot-red';
}
function setEl(id, html)  { const e = document.getElementById(id); if(e) e.innerHTML = html; }
function setTxt(id, text) { const e = document.getElementById(id); if(e) e.textContent = text; }

function renderLogs(containerId, lines) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!lines || !lines.length) {
    el.innerHTML = '<div class="log-line" style="color:var(--mc-muted)">No data</div>';
    return;
  }
  el.innerHTML = lines.map(l =>
    `<div class="log-line">${escHtml(l)}</div>`
  ).join('');
  el.scrollTop = el.scrollHeight;
}

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;');
}

// ── Render EA ──────────────────────────────────────────────────────────────
function renderEA(d) {
  // Badge
  const badge = document.getElementById('ea-badge');
  if (badge) {
    badge.className = statusBadgeClass(d.status);
    badge.textContent = statusBadgeText(d.status);
  }
  // Source label
  setEl('ea-src',
    d.mt5_live
      ? '<span class="dot dot-green"></span> MT5 LIVE'
      : '<span class="dot dot-amber"></span> LOCAL ESTIMATE'
  );
  // Balance
  const balEl = document.getElementById('ea-balance');
  if (balEl) {
    balEl.textContent = fmt(d.balance || 0);
    balEl.className = 'big-metric ' + (d.running ? 'text-success' : 'text-muted-mc');
  }
  // Sub line
  const floatColor = d.floating_pnl >= 0 ? 'var(--mc-green)' : 'var(--mc-red)';
  setEl('ea-sub',
    `Equity: ${fmt(d.equity||0)} &nbsp;|&nbsp; ` +
    `Float: <span style="color:${floatColor}">${pnlStr(d.floating_pnl||0)}</span>`
  );
  // Stats row 1
  const sessionCls = d.session_active ? 'text-green' : 'text-amber';
  setEl('ea-stats',
    statPill(d.open_positions||0, 'Open Pos', 'text-cyan') +
    statPill(pnlStr(d.pnl_today||0), 'Today PnL', d.pnl_today>=0?'text-green':'text-red') +
    statPill(`<span class="${sessionCls}">${d.session}</span>`, 'Session', '')
  );
  // Stats row 2 (risk)
  const dlCls = (d.daily_loss_pct||0) > 2 ? 'text-red' : (d.daily_loss_pct||0) > 1 ? 'text-amber' : 'text-green';
  const ddCls = (d.drawdown_pct||0) > 4 ? 'text-red' : (d.drawdown_pct||0) > 2 ? 'text-amber' : 'text-green';
  setEl('ea-risk',
    statPill(`<span class="${dlCls}">${(d.daily_loss_pct||0).toFixed(1)}%/3%</span>`, 'Daily Loss', '') +
    statPill(`<span class="${ddCls}">${(d.drawdown_pct||0).toFixed(1)}%/5%</span>`, 'Drawdown', '') +
    statPill(d.trade_count||0, 'Trades', 'text-cyan')
  );
  renderLogs('ea-log', d.logs);
}

// ── Render Binance ─────────────────────────────────────────────────────────
function renderBinance(d) {
  const badge = document.getElementById('bin-badge');
  if (badge) {
    badge.className = statusBadgeClass(d.status);
    badge.textContent = statusBadgeText(d.status);
  }
  const balEl = document.getElementById('bin-balance');
  if (balEl) {
    balEl.textContent = fmt(d.balance || 0);
    balEl.className = 'big-metric ' + (d.running ? 'text-success' : 'text-muted-mc');
  }
  setEl('bin-sub',
    `Total PnL: <span style="color:${pnlColor(d.total_pnl||0)}">${pnlStr(d.total_pnl||0)}</span>`
  );
  setEl('bin-stats',
    statPill(pnlStr(d.pnl_today||0), 'Today PnL', d.pnl_today>=0?'text-green':'text-red') +
    statPill(`${d.wins||0}W / ${d.losses||0}L`, 'W/L Record', 'text-cyan') +
    statPill(`${d.win_rate||0}%`, 'Win Rate', d.win_rate>=50?'text-green':'text-amber')
  );
  setEl('bin-stats2',
    statPill(d.open_positions||0, 'Open Pos', 'text-cyan') +
    statPill(`<span class="text-muted-mc">${d.session||'—'}</span>`, 'Session', '') +
    statPill(pnlStr(d.total_pnl||0), 'Total PnL', d.total_pnl>=0?'text-green':'text-red')
  );
  renderLogs('bin-log', d.logs);
}

// ── Render OpenClaw ────────────────────────────────────────────────────────
function renderOpenClaw(d) {
  const badge = document.getElementById('oc-badge');
  if (badge) {
    badge.className = d.running ? 'badge-running' : 'badge-stopped';
    badge.textContent = d.running ? 'RUNNING' : 'STOPPED';
  }
  let html = '';
  (d.processes || []).forEach(p => {
    html += `<div class="int-row">
      <span class="int-name"><span class="dot ${p.ok?'dot-green':'dot-red'}"></span>${escHtml(p.name)}</span>
      <span class="${p.ok?'text-green':'text-red'}" style="font-size:.68rem;">${p.ok?'OK':'DOWN'}</span>
    </div>`;
  });
  setEl('oc-processes', html || '<div class="text-muted-mc" style="font-size:.72rem;">No process data</div>');
  renderLogs('oc-log', d.logs);
}

// ── Render agent (generic) ─────────────────────────────────────────────────
function renderAgent(badgeId, logId, d) {
  const badge = document.getElementById(badgeId);
  if (badge) {
    badge.className = d.running ? 'badge-running' : 'badge-stopped';
    badge.textContent = d.running ? 'RUNNING' : 'STOPPED';
  }
  renderLogs(logId, d.logs);
}

// ── Render AutoSocial ──────────────────────────────────────────────────────
function renderAutoSocial(d) {
  renderAgent('autosoc-badge', 'autosoc-log', d);
  setTxt('video-count', d.video_count != null ? d.video_count : '—');
}

// ── Render AutoSync ────────────────────────────────────────────────────────
function renderAutoSync(d) {
  const badge = document.getElementById('sync-badge');
  if (badge) {
    badge.className = d.running ? 'badge-running' : 'badge-stopped';
    badge.textContent = d.running ? 'RUNNING' : 'STOPPED';
  }
  let lastSync = d.last_sync || '—';
  if (lastSync && lastSync.length > 19) lastSync = lastSync.slice(0, 19).replace('T', ' ');
  setTxt('sync-last', lastSync);

  let html = '';
  (d.integrations || []).forEach(i => {
    html += `<div class="int-row">
      <span class="int-name"><span class="dot ${i.ok?'dot-green':'dot-red'}"></span>${escHtml(i.name)}</span>
      <span class="${i.ok?'text-green':'text-red'}" style="font-size:.63rem;" title="${escHtml(i.detail)}">${i.ok?'OK':'FAIL'}</span>
    </div>`;
  });
  setEl('sync-ints', html);
}

// ── Render GDrive ──────────────────────────────────────────────────────────
function renderGDrive(d) {
  setTxt('gd-faith', d.faith_videos || 0);
  setTxt('gd-christian', d.christian_videos || 0);
  setEl('gd-firebase',
    `<span class="${d.firebase_ok?'badge-ok':'badge-fail'}">${d.firebase_ok?'OK':'—'}</span>`
  );
  setEl('gd-supabase',
    `<span class="${d.supabase_ok?'badge-ok':'badge-fail'}">${d.supabase_ok?'OK':'—'}</span>`
  );
  renderLogs('gd-log', d.backup_logs);
}

// ── Render System ──────────────────────────────────────────────────────────
function renderSystem(d, tasks) {
  if (d.error) { setTxt('sys-cpu','Error'); return; }

  const cpuCls = d.cpu_pct > 80 ? 'text-red' : d.cpu_pct > 50 ? 'text-amber' : 'text-green';
  const memCls = d.mem_pct > 85 ? 'text-red' : d.mem_pct > 60 ? 'text-amber' : 'text-green';
  const dskCls = d.disk_pct > 90 ? 'text-red' : d.disk_pct > 70 ? 'text-amber' : 'text-green';

  setEl('sys-cpu',  `<span class="${cpuCls}">${d.cpu_pct}%</span>`);
  setEl('sys-mem',  `<span class="${memCls}">${d.mem_used_gb}GB / ${d.mem_total_gb}GB (${d.mem_pct}%)</span>`);
  setEl('sys-disk', `<span class="${dskCls}">${d.disk_used_gb}GB / ${d.disk_total_gb}GB (${d.disk_pct}%)</span>`);
  setTxt('sys-uptime', d.uptime || '—');

  const cpuFill = document.getElementById('sys-cpu-fill');
  const memFill = document.getElementById('sys-mem-fill');
  const dskFill = document.getElementById('sys-disk-fill');
  if (cpuFill) { cpuFill.style.width = d.cpu_pct + '%'; cpuFill.className = 'mc-progress-fill ' + (d.cpu_pct>80?'fill-red':d.cpu_pct>50?'fill-amber':'fill-blue'); }
  if (memFill) { memFill.style.width = d.mem_pct + '%'; memFill.className = 'mc-progress-fill ' + (d.mem_pct>85?'fill-red':d.mem_pct>60?'fill-amber':'fill-green'); }
  if (dskFill) { dskFill.style.width = d.disk_pct + '%'; dskFill.className = 'mc-progress-fill ' + (d.disk_pct>90?'fill-red':d.disk_pct>70?'fill-amber':'fill-amber'); }

  if (tasks) {
    setEl('sys-tasks',
      `<span class="text-amber">${tasks.pending}</span> / ` +
      `<span class="text-blue">${tasks.in_progress}</span> / ` +
      `<span class="text-green">${tasks.completed}</span>`
    );
  }
}

// ── Render live feeds ──────────────────────────────────────────────────────
function renderFeed(containerId, lines) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!lines || !lines.length) {
    el.innerHTML = '<div class="feed-line" style="color:var(--mc-muted)">No data</div>';
    return;
  }
  el.innerHTML = lines.map(l => `<div class="feed-line">${escHtml(l)}</div>`).join('');
  el.scrollTop = el.scrollHeight;
}

// ── Stat pill helper ───────────────────────────────────────────────────────
function statPill(value, label, cls) {
  return `<div class="stat-pill">
    <div class="sv ${cls}">${value}</div>
    <div class="sk">${label}</div>
  </div>`;
}

// ── Master render ──────────────────────────────────────────────────────────
function renderAll(data) {
  if (!data) return;
  try { renderEA(data.ea || {}); } catch(e) {}
  try { renderBinance(data.binance || {}); } catch(e) {}
  try { renderOpenClaw(data.openclaw || {}); } catch(e) {}
  try { renderAgent('autobin-badge', 'autobin-log', data.autobinance || {}); } catch(e) {}
  try { renderAgent('autoea-badge',  'autoea-log',  data.autoea     || {}); } catch(e) {}
  try { renderAutoSocial(data.autosocial || {}); } catch(e) {}
  try { renderAutoSync(data.autosync || {}); } catch(e) {}
  try { renderGDrive(data.gdrive || {}); } catch(e) {}
  try { renderSystem(data.system || {}, data.tasks); } catch(e) {}
  try { renderFeed('feed-ea',  data.ea_feed     || []); } catch(e) {}
  try { renderFeed('feed-bin', data.binance_feed|| []); } catch(e) {}

  // Refresh timestamp
  const ts = data.ts ? data.ts.replace('T',' ').slice(0,19) + ' UTC' : '—';
  setTxt('last-refresh', 'Updated: ' + ts);
}

// ── SocketIO ───────────────────────────────────────────────────────────────
const socket = io({ transports: ['websocket','polling'] });

socket.on('connect', () => {
  toast('Connected to Mission Control', 'var(--mc-green)');
  socket.emit('request_update');
});
socket.on('disconnect', () => {
  toast('Disconnected — reconnecting...', 'var(--mc-red)');
  setTxt('last-refresh', 'Disconnected');
});
socket.on('update', data => {
  renderAll(data);
});

// Fallback polling every 5s in case WS drops
setInterval(() => {
  if (!socket.connected) {
    fetch('/api/status').then(r => r.json()).then(renderAll).catch(() => {});
  }
}, 5000);

// ── Control actions ────────────────────────────────────────────────────────
async function ctrlTrader(trader, action) {
  if (action === 'stop' && !confirm('Stop ' + trader.toUpperCase() + '?')) return;
  try {
    const r = await fetch('/api/ctrl/' + trader + '/' + action, { method: 'POST' });
    const d = await r.json();
    toast(trader.toUpperCase() + ' ' + action + ': ' + d.status,
      d.status === 'started' || d.status === 'stopped' ? 'var(--mc-green)' : 'var(--mc-red)');
    setTimeout(() => socket.emit('request_update'), 2000);
  } catch(e) { toast('Error: ' + e.message, 'var(--mc-red)'); }
}

async function doSync() {
  try {
    const r = await fetch('/api/sync', { method: 'POST' });
    const d = await r.json();
    toast('Sync: ' + d.status, d.status === 'started' ? 'var(--mc-blue)' : 'var(--mc-red)');
  } catch(e) { toast('Error: ' + e.message, 'var(--mc-red)'); }
}

async function doVideo() {
  try {
    const r = await fetch('/api/video', { method: 'POST' });
    const d = await r.json();
    toast('Video: ' + d.status, d.status === 'started' ? 'var(--mc-blue)' : 'var(--mc-red)');
  } catch(e) { toast('Error: ' + e.message, 'var(--mc-red)'); }
}

async function doRestart() {
  if (!confirm('Restart EA + Binance?')) return;
  try {
    const r = await fetch('/api/restart', { method: 'POST' });
    const d = await r.json();
    toast('Restart initiated', 'var(--mc-amber)');
    setTimeout(() => socket.emit('request_update'), 4000);
  } catch(e) { toast('Error: ' + e.message, 'var(--mc-red)'); }
}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    port = int(os.environ.get("MC_PORT", 10000))
    # Start background broadcast thread
    t = threading.Thread(target=_broadcast_loop, daemon=True)
    t.start()
    print(f"Mission Control v2 → http://localhost:{port}  (SocketIO refresh every 5s)")
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
