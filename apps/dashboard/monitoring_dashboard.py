#!/usr/bin/env python3
"""Mission Control Dashboard - Human-AI Swarm
Full Flask monitoring dashboard on port 10000.
Reads live state from trading agents, logs, MCP registry, and video pipeline.
"""
import glob
import json
import os
import subprocess
import time
from datetime import datetime, timezone, date, timedelta
from pathlib import Path

from flask import Flask, jsonify, render_template_string, Response

app = Flask(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRADES_BIN   = PROJECT_ROOT / "agents/trading-agent/trades/binance"
TRADES_MT5   = PROJECT_ROOT / "agents/trading-agent/trades/mt5"
LOGS         = PROJECT_ROOT / "data/logs"
FEEDS        = PROJECT_ROOT / "data/feeds"
MCP_REG      = PROJECT_ROOT / "core/mcp/agent_registry.json"
MEDIA_OUT    = PROJECT_ROOT / "data/media_output"
PRODUCE_VID  = PROJECT_ROOT / "scripts/produce_video.py"

# In-memory store for video generation job state
_video_job = {"pid": None, "started_at": None, "status": "idle"}


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {}


def _pid_running(pidfile):
    try:
        pid = int(Path(pidfile).read_text().strip())
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _tail(logfile, n=50):
    try:
        lines = Path(logfile).read_text(errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return f"(log not found: {logfile})"


def _last_trades_from_feeds(feed_file, source_label, limit=10):
    """Read last N EXIT trades from a live_trades JSONL feed."""
    trades = []
    try:
        lines = Path(feed_file).read_text().splitlines()
        for raw in reversed(lines):
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
                data = obj.get("data", obj)
                if data.get("type") == "EXIT":
                    trades.append({
                        "time": (data.get("timestamp", "")[:19] or obj.get("timestamp", "")[:19]),
                        "agent": source_label,
                        "symbol": data.get("symbol", "?"),
                        "side": data.get("direction", data.get("side", "?")),
                        "pnl": float(data.get("pnl", 0)),
                        "reason": data.get("reason", ""),
                    })
                    if len(trades) >= limit:
                        break
            except Exception:
                continue
    except Exception:
        pass
    return trades


# ---------------------------------------------------------------------------
# Daily P&L helpers
# ---------------------------------------------------------------------------

def _today_str():
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _daily_pnl_from_mt5_trades(today=None):
    """
    Calculate today's P&L from individual MT5 trade JSON files.
    Files are named: trade_SYMBOL_YYYYMMDD_HHMMSS[_N].json
    Returns (pnl_today, wins_today, total_today).
    """
    if today is None:
        today = _today_str()
    pnl = 0.0
    wins = 0
    total = 0
    pattern = str(TRADES_MT5 / f"trade_*_{today}_*.json")
    for fpath in glob.glob(pattern):
        try:
            data = json.loads(Path(fpath).read_text())
            trade_pnl = data.get("pnl", data.get("profit", None))
            ttype = data.get("type", "")
            if trade_pnl is not None:
                trade_pnl = float(trade_pnl)
                pnl += trade_pnl
                total += 1
                if trade_pnl > 0:
                    wins += 1
        except Exception:
            continue
    return round(pnl, 2), wins, total


def _daily_pnl_from_binance_state(bin_state):
    """
    Extract binance daily P&L. Uses pnl_today from state if present,
    otherwise attempts to calculate from feed.
    Returns (pnl_today, wins_today, total_today).
    """
    pnl = round(float(bin_state.get("pnl_today", 0)), 2)
    wins = bin_state.get("wins_today", 0)
    total = bin_state.get("trades_today", 0)
    # Fallback: scan JSONL feed for today's exits
    if pnl == 0.0 and total == 0:
        today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%dT")
        feed = FEEDS / "binance_live_trades.jsonl"
        try:
            for raw in Path(feed).read_text().splitlines():
                if not raw.strip():
                    continue
                obj = json.loads(raw)
                data = obj.get("data", obj)
                ts = data.get("timestamp", obj.get("timestamp", ""))
                if data.get("type") == "EXIT" and ts.startswith(today_prefix):
                    p = float(data.get("pnl", 0))
                    pnl += p
                    total += 1
                    if p > 0:
                        wins += 1
        except Exception:
            pass
        pnl = round(pnl, 2)
    return pnl, wins, total


def _daily_pnl_7days_ea():
    """
    Returns list of (date_str, pnl) for last 7 days for EA.
    date_str format: MM-DD
    """
    results = []
    today = datetime.now(timezone.utc).date()
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_str = d.strftime("%Y%m%d")
        label = d.strftime("%m-%d")
        pnl, _, _ = _daily_pnl_from_mt5_trades(day_str)
        results.append({"date": label, "pnl": pnl})
    return results


# ---------------------------------------------------------------------------
# Agent status helpers
# ---------------------------------------------------------------------------

def _agent_log_status():
    """
    Check last-modified time of known agent logs.
    Returns list of dicts with name, log file, age_seconds, status_label.
    """
    agents = [
        ("Hermes",       LOGS / "hermes.log"),
        ("OpenCode",     LOGS / "opencode.log"),
        ("Pi.dev",       LOGS / "pidev.log"),
        ("OpenClaw",     LOGS / "openclaw.log"),
        ("Automode",     LOGS / "automode.log"),
        ("PAI",          LOGS / "pai_agent.log"),
        ("Social/Video", LOGS / "social.log"),
    ]
    results = []
    now = time.time()
    for name, logpath in agents:
        try:
            mtime = logpath.stat().st_mtime
            age_sec = int(now - mtime)
            if age_sec < 120:
                label = f"active {age_sec}s ago"
                css = "green"
            elif age_sec < 3600:
                label = f"active {age_sec // 60}m ago"
                css = "yellow"
            else:
                label = f"idle {age_sec // 3600}h ago"
                css = "muted"
        except Exception:
            label = "no log"
            css = "muted"
            age_sec = 99999
        results.append({"name": name, "label": label, "css": css, "age": age_sec})
    return results


# ---------------------------------------------------------------------------
# MCP status
# ---------------------------------------------------------------------------

def _mcp_status():
    reg = _read_json(MCP_REG)
    agents = reg.get("agents", {})
    try:
        result = subprocess.run(
            ["pgrep", "-f", "mcp_server.py"],
            capture_output=True, text=True, timeout=3
        )
        running = result.returncode == 0
    except Exception:
        running = bool(agents)
    return {
        "running": running,
        "agents": len(agents),
        "agent_names": list(agents.keys()),
    }


# ---------------------------------------------------------------------------
# Video pipeline helpers
# ---------------------------------------------------------------------------

def _video_stats():
    """
    Scan media_output for video files.
    Returns dict with today_count, alltime_count, last_5, avg_gen_time_sec.
    """
    today_prefix = datetime.now(timezone.utc).strftime("%Y%m%d")
    today_count = 0
    all_count = 0
    last_5 = []
    gen_times = []

    # Scan reel directories (old-style reel_tiktok_* and new-style trading/)
    reel_dirs_old = sorted(MEDIA_OUT.glob("reel_tiktok_*"), reverse=True)
    reel_dirs_new = sorted((MEDIA_OUT / "trading" / "tiktok").glob("*.mp4"), reverse=True)
    reel_dirs_new_yt = sorted((MEDIA_OUT / "trading" / "youtube").glob("*.mp4"), reverse=True)

    # Count new-style flat trading videos
    for mp4 in list(reel_dirs_new) + list(reel_dirs_new_yt):
        try:
            mtime = mp4.stat().st_mtime
        except Exception:
            continue
        from datetime import datetime as _dt
        mp4_date = _dt.utcfromtimestamp(mtime).strftime("%Y%m%d")
        plat = "tiktok" if mp4.parent.name == "tiktok" else "youtube"
        all_count += 1
        if mp4_date == today_prefix:
            today_count += 1
        if len(last_5) < 5:
            last_5.append({
                "filename": mp4.name,
                "platform": plat,
                "created": mp4_date,
                "dir": f"trading/{plat}",
            })

    reel_dirs = reel_dirs_old
    for rdir in reel_dirs:
        # Extract timestamp from dirname: reel_tiktok_YYYYMMDD_HHMMSS
        parts = rdir.name.split("_")
        if len(parts) >= 3:
            dir_date = parts[2]  # YYYYMMDD
        else:
            dir_date = ""

        # Find mp4s in this dir
        mp4s = list(rdir.glob("*.mp4"))
        if not mp4s:
            continue

        mp4 = mp4s[0]
        all_count += 1

        # Determine platform from dir name
        platform = "tiktok" if "tiktok" in rdir.name else "unknown"

        # Try reading metadata for generated_at
        meta = _read_json(rdir / "reel_metadata.json")
        gen_at = meta.get("generated_at", "")

        # Creation time estimate: compare dir mtime to mp4 mtime
        try:
            dir_ctime = rdir.stat().st_ctime
            mp4_mtime = mp4.stat().st_mtime
            diff = max(0, mp4_mtime - dir_ctime)
            gen_times.append(diff)
        except Exception:
            pass

        if dir_date == today_prefix:
            today_count += 1

        if len(last_5) < 5:
            last_5.append({
                "filename": mp4.name,
                "platform": platform,
                "created": gen_at[:19] if gen_at else dir_date,
                "dir": rdir.name,
            })

    # Also count faithnexus/christian videos (old faithnexus/ tree + new christian/ flat)
    fn_mp4s = list(MEDIA_OUT.glob("faithnexus/**/*.mp4")) + list(MEDIA_OUT.glob("christian/*.mp4"))
    for mp4 in fn_mp4s:
        if "background" in mp4.name:
            continue
        all_count += 1
        parts = mp4.parent.name.split("_")
        dir_date = ""
        for p in parts:
            if len(p) == 8 and p.isdigit():
                dir_date = p
                break
        if dir_date == today_prefix:
            today_count += 1
        if len(last_5) < 5:
            last_5.append({
                "filename": mp4.name,
                "platform": "faithnexus",
                "created": dir_date,
                "dir": mp4.parent.name,
            })

    avg_gen = round(sum(gen_times) / len(gen_times), 1) if gen_times else 0

    # Video queue status
    global _video_job
    if _video_job["pid"]:
        try:
            os.kill(_video_job["pid"], 0)
            # Still running
            elapsed = int(time.time() - _video_job["started_at"])
            queue_status = f"running ({elapsed}s)"
            queue_css = "yellow"
        except OSError:
            _video_job["status"] = "idle"
            _video_job["pid"] = None
            queue_status = "idle"
            queue_css = "green"
    else:
        queue_status = "idle"
        queue_css = "green"

    return {
        "today_count": today_count,
        "alltime_count": all_count,
        "avg_gen_time": avg_gen,
        "last_5": last_5,
        "queue_status": queue_status,
        "queue_css": queue_css,
    }


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def collect_all():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # EA / MT5
    ea_state = _read_json(TRADES_MT5 / "state.json")
    # Prefer pnl_today from state, fallback to trade file scan
    ea_pnl_today_state = round(float(ea_state.get("pnl_today", 0)), 2)
    ea_pnl_today_calc, ea_wins_today, ea_trades_today = _daily_pnl_from_mt5_trades()
    # Use state value if non-zero, else use calculated
    ea_pnl_today = ea_pnl_today_state if ea_pnl_today_state != 0.0 else ea_pnl_today_calc
    ea_win_rate = round(100 * ea_wins_today / ea_trades_today, 1) if ea_trades_today > 0 else 0.0

    ea = {
        "running": ea_state.get("session_active", False) or ea_state.get("mt5_live", False),
        "balance": round(ea_state.get("balance", ea_state.get("mt5_balance", 0)), 2),
        "equity": round(ea_state.get("equity", ea_state.get("mt5_equity", 0)), 2),
        "pnl": round(float(ea_state.get("total_pnl", 0)), 2),
        "trades": ea_state.get("trade_count", 0),
        "streak": ea_state.get("streak", 0),
        "positions": ea_state.get("open_positions", ea_state.get("mt5_positions", 0)),
        "daily_loss_pct": ea_state.get("daily_loss_pct", 0.0),
        "pnl_today": ea_pnl_today,
        "wins_today": ea_wins_today,
        "trades_today": ea_trades_today,
        "win_rate_today": ea_win_rate,
        "symbols": ea_state.get("symbols_active", ["XAUUSD", "XAGUSD"]),
        "account": ea_state.get("mt5_account", ""),
        "server": ea_state.get("mt5_server", ""),
        "last_update": ea_state.get("last_update", "")[:19],
    }

    # Binance
    bin_state = _read_json(TRADES_BIN / "state.json")
    bin_pnl_today, bin_wins_today, bin_trades_today = _daily_pnl_from_binance_state(bin_state)
    bin_win_rate = round(100 * bin_wins_today / bin_trades_today, 1) if bin_trades_today > 0 else 0.0
    binance = {
        "running": bool(bin_state),
        "balance": round(float(bin_state.get("current_balance", 0)), 2),
        "start_bal": round(float(bin_state.get("starting_balance", 0)), 2),
        "pnl": round(float(bin_state.get("total_pnl", 0)), 2),
        "trades": bin_state.get("trade_count", 0),
        "positions": bin_state.get("open_positions", 0),
        "symbols": bin_state.get("symbols", []),
        "pnl_today": bin_pnl_today,
        "wins_today": bin_wins_today,
        "trades_today": bin_trades_today,
        "win_rate_today": bin_win_rate,
        "last_update": bin_state.get("last_update", "")[:19],
    }
    try:
        lu = datetime.fromisoformat(bin_state.get("last_update", "1970-01-01T00:00:00"))
        age_secs = (datetime.now() - lu).total_seconds()
        binance["running"] = age_secs < 300
    except Exception:
        pass

    # Combined daily P&L
    combined_daily = round(ea_pnl_today + bin_pnl_today, 2)

    # MCP
    mcp = _mcp_status()

    # Agents status
    agents_status = _agent_log_status()

    # Video stats
    video = _video_stats()

    # 7-day EA chart data
    ea_7day = _daily_pnl_7days_ea()

    # Trades from feeds
    ea_trades = _last_trades_from_feeds(FEEDS / "ea_live_trades.jsonl", "EA", 10)
    bin_trades = _last_trades_from_feeds(FEEDS / "binance_live_trades.jsonl", "Binance", 10)
    all_trades = sorted(ea_trades + bin_trades, key=lambda t: t["time"], reverse=True)[:15]

    return {
        "timestamp": ts,
        "ea": ea,
        "binance": binance,
        "combined_daily": combined_daily,
        "mcp": mcp,
        "agents_status": agents_status,
        "video": video,
        "ea_7day": ea_7day,
        "trades": all_trades,
    }


# ---------------------------------------------------------------------------
# HTML Template
# ---------------------------------------------------------------------------

HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Human-AI Swarm Control</title>
<meta http-equiv="refresh" content="30">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{
  --bg:#060910;--bg2:#0c1220;--bg3:#111928;
  --border:#1e2d45;--green:#10b981;--red:#ef4444;
  --blue:#3b82f6;--yellow:#f59e0b;--cyan:#06b6d4;
  --purple:#8b5cf6;--text:#e2e8f0;--muted:#64748b
}
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New',monospace}
body{background:var(--bg);color:var(--text);min-height:100vh;font-size:13px;padding:0}
.topbar{
  background:linear-gradient(90deg,#0a0f1e,#0c1629);
  border-bottom:1px solid var(--border);
  padding:10px 20px;display:flex;justify-content:space-between;align-items:center
}
.topbar h1{color:var(--cyan);font-size:1.1em;letter-spacing:3px;text-shadow:0 0 20px rgba(6,182,212,.4)}
.topbar .meta{text-align:right;font-size:.75em;color:var(--muted)}
.content{padding:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-bottom:14px}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:14px}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px}
@media(max-width:900px){.grid-3{grid-template-columns:1fr 1fr}.grid-2{grid-template-columns:1fr}}
@media(max-width:600px){.grid-3{grid-template-columns:1fr}}
.panel{
  background:var(--bg2);border:1px solid var(--border);border-radius:8px;
  padding:14px;position:relative;overflow:hidden
}
.panel::before{
  content:'';position:absolute;top:0;left:0;right:0;height:2px;border-radius:8px 8px 0 0
}
.panel.p-ea::before{background:linear-gradient(90deg,var(--green),var(--cyan))}
.panel.p-bin::before{background:linear-gradient(90deg,var(--yellow),var(--green))}
.panel.p-mcp::before{background:linear-gradient(90deg,var(--purple),var(--blue))}
.panel.p-log::before{background:linear-gradient(90deg,var(--muted),var(--border))}
.panel.p-trades::before{background:linear-gradient(90deg,var(--cyan),var(--purple))}
.panel.p-daily::before{background:linear-gradient(90deg,var(--cyan),var(--green))}
.panel.p-video::before{background:linear-gradient(90deg,var(--purple),var(--cyan))}
.panel.p-agents::before{background:linear-gradient(90deg,var(--blue),var(--purple))}
h2{color:var(--blue);font-size:.72em;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--border)}
.row{display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid rgba(30,45,69,.5)}
.row:last-child{border-bottom:none}
.lbl{color:var(--muted);font-size:.78em}
.val{font-weight:bold;font-size:.78em}
.green{color:var(--green)}
.red{color:var(--red)}
.yellow{color:var(--yellow)}
.cyan{color:var(--cyan)}
.muted{color:var(--muted)}
.status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px}
.dot-on{background:var(--green);box-shadow:0 0 6px var(--green)}
.dot-off{background:var(--red)}
.log-box{
  background:#030508;border:1px solid #1a2535;border-radius:4px;
  padding:8px;height:220px;overflow-y:auto;font-size:.68em;line-height:1.5;
  white-space:pre-wrap;word-break:break-all;color:#94a3b8
}
.log-2col{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px}
@media(max-width:700px){.log-2col{grid-template-columns:1fr}}
table{width:100%;border-collapse:collapse;font-size:.75em}
table th{background:#0c1220;padding:5px 8px;text-align:left;color:var(--muted);font-weight:normal;letter-spacing:.5px;border-bottom:1px solid var(--border)}
table td{padding:4px 8px;border-bottom:1px solid rgba(30,45,69,.4)}
.api-links{margin-top:8px;font-size:.72em;color:var(--muted)}
.api-links a{color:var(--cyan);text-decoration:none;margin-right:12px}
.api-links a:hover{text-decoration:underline}
.daily-summary{
  display:flex;gap:16px;flex-wrap:wrap;justify-content:space-around;
  margin:4px 0 8px 0
}
.daily-card{
  text-align:center;flex:1;min-width:80px;
  background:var(--bg3);border-radius:6px;padding:8px 12px;border:1px solid var(--border)
}
.daily-card .big{font-size:1.4em;font-weight:bold;margin-bottom:2px}
.daily-card .sub{font-size:.65em;color:var(--muted);letter-spacing:.5px;text-transform:uppercase}
.agent-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:6px;margin-top:4px}
.agent-chip{
  background:var(--bg3);border:1px solid var(--border);border-radius:5px;
  padding:6px 8px;font-size:.7em
}
.agent-chip .agent-name{color:var(--text);font-weight:bold;margin-bottom:2px}
.agent-chip .agent-status{color:var(--muted)}
.btn{
  display:inline-block;padding:6px 14px;border-radius:4px;border:none;cursor:pointer;
  font-family:'Courier New',monospace;font-size:.75em;font-weight:bold;letter-spacing:.5px;
  text-transform:uppercase;transition:opacity .15s
}
.btn:hover{opacity:.85}
.btn-cyan{background:var(--cyan);color:#000}
.btn-green{background:var(--green);color:#000}
.video-table td{font-size:.7em}
.chart-wrap{margin-top:10px;height:90px;position:relative}
.section-label{
  color:var(--muted);font-size:.65em;letter-spacing:2px;text-transform:uppercase;
  margin:14px 0 6px 0
}
</style>
</head>
<body>
<div class="topbar">
  <h1>&#x1F916; HUMAN-AI SWARM CONTROL</h1>
  <div class="meta">
    Last updated: {{ timestamp }}<br>
    Auto-refresh: 30s &nbsp;|&nbsp;
    <a href="/api/status" style="color:var(--cyan);text-decoration:none">API</a>
  </div>
</div>

<div class="content">

<!-- ============================================================ -->
<!-- DAILY P&L SUMMARY BANNER                                     -->
<!-- ============================================================ -->
<p class="section-label">Daily P&amp;L Summary (UTC)</p>
<div class="panel p-daily" style="margin-bottom:14px">
  <h2>Daily P&amp;L Summary</h2>
  <div class="daily-summary">
    <div class="daily-card">
      <div class="big {% if ea.pnl_today > 0 %}green{% elif ea.pnl_today < 0 %}red{% else %}yellow{% endif %}">${{ "{:+,.2f}".format(ea.pnl_today) }}</div>
      <div class="sub">EA Daily</div>
      {% if ea.trades_today > 0 %}
      <div style="font-size:.65em;color:var(--muted);margin-top:2px">{{ ea.trades_today }} trades &bull; {{ ea.win_rate_today }}% win</div>
      {% endif %}
    </div>
    <div class="daily-card">
      <div class="big {% if binance.pnl_today > 0 %}green{% elif binance.pnl_today < 0 %}red{% else %}yellow{% endif %}">${{ "{:+,.2f}".format(binance.pnl_today) }}</div>
      <div class="sub">Binance Daily</div>
      {% if binance.trades_today > 0 %}
      <div style="font-size:.65em;color:var(--muted);margin-top:2px">{{ binance.trades_today }} trades &bull; {{ binance.win_rate_today }}% win</div>
      {% endif %}
    </div>
    <div class="daily-card">
      <div class="big {% if combined_daily > 0 %}green{% elif combined_daily < 0 %}red{% else %}yellow{% endif %}">${{ "{:+,.2f}".format(combined_daily) }}</div>
      <div class="sub">Combined Daily</div>
    </div>
  </div>
</div>

<!-- ============================================================ -->
<!-- TRADING AGENT STATUS CARDS                                   -->
<!-- ============================================================ -->
<p class="section-label">Trading Agents</p>
<div class="grid">

  <!-- EA Agent -->
  <div class="panel p-ea">
    <h2>EA Trading Agent (XAUUSD / XAGUSD)</h2>
    <div class="row">
      <span class="lbl">Status</span>
      <span class="val {% if ea.running %}green{% else %}red{% endif %}">
        <span class="status-dot {% if ea.running %}dot-on{% else %}dot-off{% endif %}"></span>
        {{ 'LIVE' if ea.running else 'STOPPED' }}
      </span>
    </div>
    <div class="row"><span class="lbl">Balance</span><span class="val">${{ "{:,.2f}".format(ea.balance) }}</span></div>
    <div class="row"><span class="lbl">Equity</span><span class="val">${{ "{:,.2f}".format(ea.equity) }}</span></div>
    <div class="row">
      <span class="lbl">Daily P&amp;L</span>
      <span class="val {% if ea.pnl_today > 0 %}green{% elif ea.pnl_today < 0 %}red{% else %}yellow{% endif %}">${{ "{:+,.2f}".format(ea.pnl_today) }}</span>
    </div>
    <div class="row">
      <span class="lbl">Daily Win Rate</span>
      <span class="val {% if ea.win_rate_today >= 50 %}green{% elif ea.win_rate_today > 0 %}yellow{% else %}muted{% endif %}">
        {{ ea.win_rate_today }}% ({{ ea.wins_today }}/{{ ea.trades_today }})
      </span>
    </div>
    <div class="row">
      <span class="lbl">Total PnL (all-time)</span>
      <span class="val {% if ea.pnl >= 0 %}green{% else %}red{% endif %}">${{ "{:+,.2f}".format(ea.pnl) }}</span>
    </div>
    <div class="row"><span class="lbl">Total Trades</span><span class="val">{{ ea.trades }}</span></div>
    <div class="row">
      <span class="lbl">Streak</span>
      <span class="val {% if ea.streak > 0 %}green{% elif ea.streak < 0 %}red{% else %}yellow{% endif %}">{{ "{:+d}".format(ea.streak) }}</span>
    </div>
    <div class="row"><span class="lbl">Open Positions</span><span class="val">{{ ea.positions }}</span></div>
    <div class="row">
      <span class="lbl">Daily Loss %</span>
      <span class="val {% if ea.daily_loss_pct > 1.5 %}red{% elif ea.daily_loss_pct > 0.5 %}yellow{% else %}green{% endif %}">{{ ea.daily_loss_pct }}%</span>
    </div>
    <div class="row"><span class="lbl">Account</span><span class="val muted">{{ ea.account }} @ {{ ea.server }}</span></div>
    <div class="row"><span class="lbl">Updated</span><span class="val muted">{{ ea.last_update }}</span></div>
    <!-- 7-day mini chart -->
    <div class="chart-wrap">
      <canvas id="ea7dayChart"></canvas>
    </div>
  </div>

  <!-- Binance Agent -->
  <div class="panel p-bin">
    <h2>Binance Futures Agent</h2>
    <div class="row">
      <span class="lbl">Status</span>
      <span class="val {% if binance.running %}green{% else %}red{% endif %}">
        <span class="status-dot {% if binance.running %}dot-on{% else %}dot-off{% endif %}"></span>
        {{ 'LIVE' if binance.running else 'STOPPED' }}
      </span>
    </div>
    <div class="row"><span class="lbl">Balance</span><span class="val">${{ "{:,.2f}".format(binance.balance) }}</span></div>
    <div class="row"><span class="lbl">Starting Balance</span><span class="val muted">${{ "{:,.2f}".format(binance.start_bal) }}</span></div>
    <div class="row">
      <span class="lbl">Daily P&amp;L</span>
      <span class="val {% if binance.pnl_today > 0 %}green{% elif binance.pnl_today < 0 %}red{% else %}yellow{% endif %}">${{ "{:+,.2f}".format(binance.pnl_today) }}</span>
    </div>
    <div class="row">
      <span class="lbl">Daily Win Rate</span>
      <span class="val {% if binance.win_rate_today >= 50 %}green{% elif binance.win_rate_today > 0 %}yellow{% else %}muted{% endif %}">
        {{ binance.win_rate_today }}% ({{ binance.wins_today }}/{{ binance.trades_today }})
      </span>
    </div>
    <div class="row">
      <span class="lbl">Total PnL (all-time)</span>
      <span class="val {% if binance.pnl >= 0 %}green{% else %}red{% endif %}">${{ "{:+,.2f}".format(binance.pnl) }}</span>
    </div>
    <div class="row">
      <span class="lbl">Net P&amp;L (bal delta)</span>
      <span class="val {% if (binance.balance - binance.start_bal) >= 0 %}green{% else %}red{% endif %}">${{ "{:+,.2f}".format(binance.balance - binance.start_bal) }}</span>
    </div>
    <div class="row"><span class="lbl">Total Trades</span><span class="val">{{ binance.trades }}</span></div>
    <div class="row"><span class="lbl">Open Positions</span><span class="val">{{ binance.positions }}</span></div>
    {% if binance.symbols %}
    <div class="row"><span class="lbl">Active Symbols</span><span class="val muted">{{ binance.symbols | join(', ') }}</span></div>
    {% endif %}
    <div class="row"><span class="lbl">Updated</span><span class="val muted">{{ binance.last_update }}</span></div>
  </div>

  <!-- MCP Gateway -->
  <div class="panel p-mcp">
    <h2>MCP Gateway (A2A)</h2>
    <div class="row">
      <span class="lbl">Status</span>
      <span class="val {% if mcp.running %}green{% else %}red{% endif %}">
        <span class="status-dot {% if mcp.running %}dot-on{% else %}dot-off{% endif %}"></span>
        {{ 'RUNNING' if mcp.running else 'STOPPED' }}
      </span>
    </div>
    <div class="row"><span class="lbl">Port</span><span class="val">8765</span></div>
    <div class="row"><span class="lbl">Agents Registered</span><span class="val">{{ mcp.agents }}</span></div>
    {% if mcp.agent_names %}
    <div class="row"><span class="lbl">Agent IDs</span><span class="val muted" style="text-align:right;max-width:180px;word-break:break-all">{{ mcp.agent_names | join(', ') }}</span></div>
    {% endif %}
  </div>

</div>

<!-- ============================================================ -->
<!-- AGENTS STATUS                                                -->
<!-- ============================================================ -->
<p class="section-label">Autonomous Agents</p>
<div class="panel p-agents" style="margin-bottom:14px">
  <h2>Agents Status</h2>
  <div class="agent-grid">
    {% for ag in agents_status %}
    <div class="agent-chip">
      <div class="agent-name">{{ ag.name }}</div>
      <div class="agent-status {{ ag.css }}">{{ ag.label }}</div>
    </div>
    {% endfor %}
  </div>
</div>

<!-- ============================================================ -->
<!-- VIDEO GENERATION PIPELINE                                    -->
<!-- ============================================================ -->
<p class="section-label">Content Pipeline</p>
<div class="panel p-video" style="margin-bottom:14px">
  <h2>Video Generation Pipeline</h2>
  <div class="daily-summary" style="margin-bottom:10px">
    <div class="daily-card">
      <div class="big cyan">{{ video.today_count }}</div>
      <div class="sub">Today</div>
    </div>
    <div class="daily-card">
      <div class="big">{{ video.alltime_count }}</div>
      <div class="sub">All-time</div>
    </div>
    <div class="daily-card">
      <div class="big">{{ video.avg_gen_time }}s</div>
      <div class="sub">Avg Gen</div>
    </div>
    <div class="daily-card">
      <div class="big {{ video.queue_css }}">{{ video.queue_status }}</div>
      <div class="sub">Queue</div>
    </div>
  </div>
  {% if video.last_5 %}
  <table class="video-table">
    <thead>
      <tr>
        <th>Filename</th><th>Platform</th><th>Created</th>
      </tr>
    </thead>
    <tbody>
    {% for v in video.last_5 %}
      <tr>
        <td class="muted" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ v.filename }}</td>
        <td style="color:var(--purple)">{{ v.platform }}</td>
        <td class="muted">{{ v.created }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% endif %}
  <div style="margin-top:10px">
    <button class="btn btn-cyan" onclick="generateVideo()">&#x25B6; Generate Video</button>
    <span id="gen-status" style="margin-left:10px;font-size:.72em;color:var(--muted)"></span>
  </div>
</div>

<!-- ============================================================ -->
<!-- LOG STREAMING BOXES                                          -->
<!-- ============================================================ -->
<p class="section-label">Live Logs (streaming every 5s)</p>
<div class="log-2col">
  <div class="panel p-log">
    <h2>EA Agent Log</h2>
    <div class="log-box" id="log-ea">(loading...)</div>
  </div>
  <div class="panel p-log">
    <h2>Binance Agent Log</h2>
    <div class="log-box" id="log-binance">(loading...)</div>
  </div>
</div>

<!-- ============================================================ -->
<!-- RECENT TRADES                                                -->
<!-- ============================================================ -->
<div class="panel p-trades" style="margin-bottom:14px">
  <h2>Recent Trades (last 15 exits)</h2>
  {% if trades %}
  <table>
    <thead>
      <tr>
        <th>Time</th><th>Agent</th><th>Symbol</th><th>Side</th><th>PnL</th><th>Reason</th>
      </tr>
    </thead>
    <tbody>
    {% for t in trades %}
      <tr style="background:{% if t.pnl > 0 %}rgba(16,185,129,0.07){% elif t.pnl < 0 %}rgba(239,68,68,0.07){% else %}transparent{% endif %}">
        <td class="muted">{{ t.time }}</td>
        <td>{{ t.agent }}</td>
        <td style="color:var(--cyan)">{{ t.symbol }}</td>
        <td class="{% if t.side in ('BUY','LONG') %}green{% else %}red{% endif %}">{{ t.side }}</td>
        <td class="{% if t.pnl >= 0 %}green{% else %}red{% endif %}">${{ "{:+.2f}".format(t.pnl) }}</td>
        <td class="muted">{{ t.reason }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
  <p class="muted" style="padding:8px">No trade history found.</p>
  {% endif %}
</div>

<div class="api-links" style="margin-top:12px;padding-bottom:20px">
  API:
  <a href="/api/status">/api/status</a>
  <a href="/api/trades">/api/trades</a>
  <a href="/api/mcp">/api/mcp</a>
  <a href="/api/logs/ea">/api/logs/ea</a>
  <a href="/api/logs/binance">/api/logs/binance</a>
  <a href="/api/video/generate" style="color:var(--purple)">/api/video/generate</a>
  <a href="/api/video/status" style="color:var(--purple)">/api/video/status</a>
</div>

</div><!-- /content -->

<script>
// ---- 7-day EA P&L bar chart ----
(function(){
  var data = {{ ea_7day | tojson }};
  var labels = data.map(function(d){return d.date});
  var values = data.map(function(d){return d.pnl});
  var colors = values.map(function(v){
    return v > 0 ? 'rgba(16,185,129,0.8)' : v < 0 ? 'rgba(239,68,68,0.8)' : 'rgba(245,158,11,0.5)';
  });
  var ctx = document.getElementById('ea7dayChart');
  if(!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: colors,
        borderColor: colors,
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {display: false},
        tooltip: {
          callbacks: {
            label: function(c){ return '$' + (c.raw >= 0 ? '+' : '') + c.raw.toFixed(2); }
          }
        }
      },
      scales: {
        x: {
          ticks: {color: '#64748b', font: {size: 9, family: 'Courier New'}},
          grid: {color: 'rgba(30,45,69,0.4)'}
        },
        y: {
          ticks: {
            color: '#64748b', font: {size: 9, family: 'Courier New'},
            callback: function(v){ return '$' + v; }
          },
          grid: {color: 'rgba(30,45,69,0.4)'}
        }
      }
    }
  });
})();

// ---- Log line colorizer ----
function colorizeLog(text) {
  var lines = (text || '(empty)').split('\n');
  var html = lines.map(function(line) {
    var escaped = line.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    if (/ERROR|EXCEPTION|TRACEBACK/i.test(line)) {
      return '<span style="color:#ef4444">' + escaped + '</span>';
    } else if (/WARNING/i.test(line)) {
      return '<span style="color:#f59e0b">' + escaped + '</span>';
    } else if (/PROFIT|WIN|✓/i.test(line)) {
      return '<span style="color:#10b981">' + escaped + '</span>';
    }
    return escaped;
  });
  return html.join('\n');
}

// ---- Log streaming ----
function fetchLog(endpoint, elementId) {
  fetch(endpoint)
    .then(function(r){ return r.json(); })
    .then(function(data){
      var box = document.getElementById(elementId);
      if(box){
        box.innerHTML = colorizeLog(data.lines);
        box.scrollTop = box.scrollHeight;
      }
    })
    .catch(function(e){ console.warn('log fetch failed', endpoint, e); });
}

function refreshLogs() {
  fetchLog('/api/logs/ea', 'log-ea');
  fetchLog('/api/logs/binance', 'log-binance');
}

// Initial load + every 5s
refreshLogs();
setInterval(refreshLogs, 5000);

// ---- Video generation ----
var _videoPoller = null;

function pollVideoStatus() {
  fetch('/api/video/status')
    .then(function(r){ return r.json(); })
    .then(function(data){
      var btn = document.querySelector('.btn-cyan');
      var status = document.getElementById('gen-status');
      if(data.status === 'running'){
        status.textContent = 'Generating... ' + data.elapsed + 's';
        status.style.color = 'var(--yellow)';
        btn.disabled = true;
        btn.textContent = 'Running...';
      } else {
        status.textContent = status.textContent.indexOf('Generating') !== -1 ? 'Done' : status.textContent;
        if(status.textContent === 'Done') status.style.color = 'var(--green)';
        btn.disabled = false;
        btn.textContent = '▶ Generate Video';
        if(_videoPoller){ clearInterval(_videoPoller); _videoPoller = null; }
      }
    })
    .catch(function(){
      if(_videoPoller){ clearInterval(_videoPoller); _videoPoller = null; }
    });
}

// Check video status on page load
pollVideoStatus();

function generateVideo() {
  var btn = document.querySelector('.btn-cyan');
  var status = document.getElementById('gen-status');
  btn.disabled = true;
  btn.textContent = 'Starting...';
  status.textContent = '';
  fetch('/api/video/generate', {method: 'POST'})
    .then(function(r){ return r.json(); })
    .then(function(data){
      if(data.status === 'started'){
        status.textContent = 'Generating... 0s';
        status.style.color = 'var(--yellow)';
        btn.textContent = 'Running...';
        if(_videoPoller) clearInterval(_videoPoller);
        _videoPoller = setInterval(pollVideoStatus, 2000);
      } else if(data.status === 'already_running'){
        status.textContent = 'Already running (PID ' + data.pid + ')';
        status.style.color = 'var(--yellow)';
        btn.disabled = false;
        btn.textContent = '▶ Generate Video';
        if(_videoPoller) clearInterval(_videoPoller);
        _videoPoller = setInterval(pollVideoStatus, 2000);
      } else {
        status.textContent = data.error || 'Error';
        status.style.color = 'var(--red)';
        btn.disabled = false;
        btn.textContent = '▶ Generate Video';
      }
    })
    .catch(function(e){
      status.textContent = 'Request failed';
      status.style.color = 'var(--red)';
      btn.disabled = false;
      btn.textContent = '▶ Generate Video';
    });
}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    data = collect_all()
    return render_template_string(HTML, **data)


@app.route("/api/status")
def api_status():
    data = collect_all()
    return jsonify({
        "timestamp": data["timestamp"],
        "ea": data["ea"],
        "binance": data["binance"],
        "combined_daily_pnl": data["combined_daily"],
        "mcp": data["mcp"],
        "agents_status": data["agents_status"],
        "video": data["video"],
    })


@app.route("/api/trades")
def api_trades():
    ea_trades = _last_trades_from_feeds(FEEDS / "ea_live_trades.jsonl", "EA", 20)
    bin_trades = _last_trades_from_feeds(FEEDS / "binance_live_trades.jsonl", "Binance", 20)
    all_trades = sorted(ea_trades + bin_trades, key=lambda t: t["time"], reverse=True)
    return jsonify({"trades": all_trades, "count": len(all_trades)})


@app.route("/api/mcp")
def api_mcp():
    reg = _read_json(MCP_REG)
    return jsonify({
        "status": _mcp_status(),
        "registry": reg,
    })


@app.route("/api/logs/ea")
def api_logs_ea():
    lines = _tail(LOGS / "liveea.log", 50)
    return jsonify({"lines": lines, "source": "liveea.log"})


@app.route("/api/logs/binance")
def api_logs_binance():
    lines = _tail(LOGS / "live_trading_binance.log", 50)
    return jsonify({"lines": lines, "source": "live_trading_binance.log"})


@app.route("/api/video/generate", methods=["POST"])
def api_video_generate():
    global _video_job
    # Check if already running
    if _video_job["pid"] is not None:
        try:
            os.kill(_video_job["pid"], 0)
            return jsonify({
                "status": "already_running",
                "pid": _video_job["pid"],
                "started_at": _video_job["started_at"],
            })
        except OSError:
            # Process ended
            _video_job["pid"] = None

    # Launch produce_video.py as background subprocess
    try:
        proc = subprocess.Popen(
            ["python", str(PRODUCE_VID)],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _video_job["pid"] = proc.pid
        _video_job["started_at"] = time.time()
        _video_job["status"] = "running"
        return jsonify({
            "status": "started",
            "pid": proc.pid,
            "script": str(PRODUCE_VID),
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/video/status")
def api_video_status():
    global _video_job
    if _video_job["pid"] is not None:
        try:
            os.kill(_video_job["pid"], 0)
            elapsed = int(time.time() - _video_job["started_at"])
            return jsonify({
                "status": "running",
                "pid": _video_job["pid"],
                "elapsed": elapsed,
                "started_at": _video_job["started_at"],
            })
        except OSError:
            _video_job["status"] = "idle"
            _video_job["pid"] = None
    return jsonify({"status": "idle", "pid": None, "elapsed": 0})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "ts": datetime.now().isoformat()})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"[{datetime.now():%H:%M:%S}] Human-AI Mission Control starting on port 10000")
    print(f"[{datetime.now():%H:%M:%S}] Project root: {PROJECT_ROOT}")
    app.run(host="0.0.0.0", port=10000, debug=False, threaded=True)
