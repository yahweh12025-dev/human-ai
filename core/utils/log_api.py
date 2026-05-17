#!/usr/bin/env python3
"""
Log API
=======
Lightweight read-only helpers for the dashboard's ``/api/logs`` endpoints.

Designed to be imported by ``apps/dashboard/monitoring_dashboard.py`` and
``core/apps/dashboard/mission_control.py``.

Public API
----------
    get_log_tail(agent_name, n=50)  -> list[str]
    get_all_agents_status()          -> dict[str, AgentLogStatus]
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import TypedDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR: Path = Path(os.getenv("LOG_DIR", str(_PROJECT_ROOT / "data" / "logs")))

# Canonical map: logical agent name → actual log file name.
# Agents can appear under multiple aliases.
_AGENT_LOG_MAP: dict[str, str] = {
    "automode":          "automode.log",
    "openclaw":          "openclaw.log",
    "hermes":            "hermes.log",
    "hermes_trade":      "hermes_trade.log",
    "opencode":          "opencode.log",
    "opencode_trade":    "opencode_trade.log",
    "pidev":             "pidev.log",
    "pi.dev":            "pidev.log",
    "pidev_monitor":     "pidev_monitor.log",
    "researcher":        "researcher.log",
    "liveea":            "liveea.log",
    "ea":                "liveea.log",
    "live_trading_ea":   "liveea.log",          # alias — both point to liveea.log
    "binance":           "binance.log",
    "live_trading_binance": "live_trading_binance.log",
    "dashboard":         "dashboard.log",
    "gsd":               "gsd.log",
    "gsd_integration":   "gsd_integration.log",
    "pai":               "pai.log",
    "pai_agent":         "pai_agent.log",
    "social":            "social.log",
    "mcp":               "mcp_server.log",
    "backup":            "backup.log",
    "gold_signal":       "gold_signal_listener.log",
    "mt5_terminal":      "mt5_terminal.log",
    "mission_control":   "mission_control.log",
    "ai_agents":         "ai_agents.log",
    "video_scheduler":   "video_scheduler.log",
    "unified":           "unified.log",
}


class AgentLogStatus(TypedDict):
    """Status record for a single agent log."""
    agent: str
    log_file: str
    path: str
    exists: bool
    size_bytes: int
    size_human: str
    last_modified: str          # ISO-8601 or "N/A"
    last_modified_ago_s: float  # seconds since last write; -1 if missing
    last_line: str
    active: bool                # True if modified in the last 10 minutes


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def get_log_tail(agent_name: str, n: int = 50) -> list[str]:
    """
    Return the last *n* lines from the named agent's log file.

    Parameters
    ----------
    agent_name:
        Logical agent name (see ``_AGENT_LOG_MAP``).  If not found in the
        map the function looks for ``data/logs/{agent_name}.log`` directly.
    n:
        Number of lines to return (default 50).

    Returns
    -------
    list[str]
        Lines from the tail, newest last.  Returns a single-element list
        with an error string if the file cannot be read.
    """
    key = agent_name.lower().replace(".", "").replace(" ", "_")
    # Try canonical map first, then alias with dot, then bare name.
    log_file = (
        _AGENT_LOG_MAP.get(key)
        or _AGENT_LOG_MAP.get(agent_name.lower())
        or f"{key}.log"
    )
    log_path = _LOG_DIR / log_file
    if not log_path.exists():
        return [f"[log not found: {log_path}]"]
    try:
        lines = log_path.read_text(errors="replace").splitlines()
        return lines[-n:]
    except Exception as exc:
        return [f"[error reading {log_path}: {exc}]"]


def get_all_agents_status() -> dict[str, AgentLogStatus]:
    """
    Return a status dict for every known agent log.

    Keys are the logical agent names; values are ``AgentLogStatus`` dicts.
    Agents that share a log file (e.g. ``ea`` and ``liveea``) each appear
    as separate keys but report the same underlying file stats.

    Returns
    -------
    dict[str, AgentLogStatus]
    """
    now = datetime.now().timestamp()
    result: dict[str, AgentLogStatus] = {}

    for agent, log_file in _AGENT_LOG_MAP.items():
        log_path = _LOG_DIR / log_file
        if not log_path.exists():
            result[agent] = AgentLogStatus(
                agent=agent,
                log_file=log_file,
                path=str(log_path),
                exists=False,
                size_bytes=0,
                size_human="0 B",
                last_modified="N/A",
                last_modified_ago_s=-1.0,
                last_line="",
                active=False,
            )
            continue

        try:
            stat = log_path.stat()
            size_bytes = stat.st_size
            mtime = stat.st_mtime
            ago_s = now - mtime
            last_modified = datetime.fromtimestamp(mtime).isoformat(timespec="seconds")
            active = ago_s < 600  # active if written in last 10 min

            # Read last line efficiently using a small tail.
            try:
                lines = log_path.read_text(errors="replace").splitlines()
                last_line = lines[-1].strip() if lines else ""
            except Exception:
                last_line = ""

            result[agent] = AgentLogStatus(
                agent=agent,
                log_file=log_file,
                path=str(log_path),
                exists=True,
                size_bytes=size_bytes,
                size_human=_human_size(size_bytes),
                last_modified=last_modified,
                last_modified_ago_s=round(ago_s, 1),
                last_line=last_line[:200],
                active=active,
            )
        except Exception as exc:
            result[agent] = AgentLogStatus(
                agent=agent,
                log_file=log_file,
                path=str(log_path),
                exists=True,
                size_bytes=0,
                size_human="0 B",
                last_modified="N/A",
                last_modified_ago_s=-1.0,
                last_line=f"[error: {exc}]",
                active=False,
            )

    return result


def get_active_agents() -> list[str]:
    """Return a list of agent names whose logs were written in the last 10 minutes."""
    return [name for name, status in get_all_agents_status().items() if status["active"]]


if __name__ == "__main__":
    import json

    print("=== Active agents ===")
    for a in get_active_agents():
        print(f"  {a}")

    print("\n=== All agents status (abbreviated) ===")
    for name, s in get_all_agents_status().items():
        print(
            f"  {name:<20} {s['size_human']:>8}  "
            f"modified={s['last_modified']}  active={s['active']}"
        )
