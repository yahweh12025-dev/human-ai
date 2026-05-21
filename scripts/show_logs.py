#!/usr/bin/env python3
"""
show_logs.py — Human-AI Swarm Log Viewer
=========================================
A minimal CLI for inspecting agent logs without leaving the terminal.

Usage
-----
    python scripts/show_logs.py                         # table of all agents
    python scripts/show_logs.py ea                      # tail liveea.log (50 lines)
    python scripts/show_logs.py binance 100             # tail binance.log (100 lines)
    python scripts/show_logs.py --search error          # search unified.log (last 24h)
    python scripts/show_logs.py --search "order failed" --hours 6
    python scripts/show_logs.py --active                # only show active agents
    python scripts/show_logs.py --list                  # list all known agent names

Notes
-----
- Run from the project root or any subdirectory; paths are resolved automatically.
- Requires no third-party packages — stdlib only.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ── Bootstrap project path ────────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from core.utils.log_api import get_all_agents_status, get_log_tail, _AGENT_LOG_MAP
from core.utils.log_consolidator import search_logs

# ── ANSI colour helpers (degrade gracefully on Windows/no-tty) ─────────────
_COLOUR = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOUR else text

def _green(t: str) -> str:  return _c("32", t)
def _yellow(t: str) -> str: return _c("33", t)
def _red(t: str) -> str:    return _c("31", t)
def _bold(t: str) -> str:   return _c("1",  t)
def _dim(t: str) -> str:    return _c("2",  t)


# ── Sub-commands ──────────────────────────────────────────────────────────

def cmd_status(active_only: bool = False) -> None:
    """Print a table summarising every known agent log."""
    statuses = get_all_agents_status()

    # De-duplicate entries pointing to the same file (show once per file).
    seen_files: set[str] = set()
    rows = []
    for agent, s in sorted(statuses.items()):
        if s["log_file"] in seen_files:
            continue
        seen_files.add(s["log_file"])
        if active_only and not s["active"]:
            continue
        rows.append(s)

    if not rows:
        print("No log files found." if not active_only else "No active agents right now.")
        return

    col_agent = max(len(r["agent"]) for r in rows) + 2
    col_file  = max(len(r["log_file"]) for r in rows) + 2
    header = (
        f"{'AGENT':<{col_agent}} {'FILE':<{col_file}} "
        f"{'SIZE':>8}  {'LAST MODIFIED':<22}  {'ACTIVE':<7}  LAST LINE"
    )
    print(_bold(header))
    print("-" * (len(header) + 10))

    for s in rows:
        active_flag = _green("YES") if s["active"] else _dim("no")
        size_str    = s["size_human"]
        mtime       = s["last_modified"]
        last_line   = s["last_line"][:80] if s["last_line"] else _dim("(empty)")
        if not s["exists"]:
            last_line = _dim("(missing)")
        agent_str = _green(s["agent"]) if s["active"] else s["agent"]
        print(
            f"{agent_str:<{col_agent}} {s['log_file']:<{col_file}} "
            f"{size_str:>8}  {mtime:<22}  {active_flag:<7}  {last_line}"
        )

    print()
    active_count = sum(1 for r in rows if r["active"])
    print(_dim(f"Total: {len(rows)} log files  |  Active (last 10 min): {active_count}"))


def cmd_tail(agent: str, n: int = 50) -> None:
    """Tail the log for *agent*."""
    lines = get_log_tail(agent, n)
    if not lines:
        print(f"[No output for agent '{agent}']")
        return
    print(_bold(f"=== {agent} — last {len(lines)} line(s) ==="))
    for line in lines:
        # Colour-code log levels.
        if any(k in line for k in ("ERROR", "EXCEPTION", "CRITICAL", "Traceback")):
            print(_red(line))
        elif any(k in line for k in ("WARNING", "WARN")):
            print(_yellow(line))
        else:
            print(line)


def cmd_search(query: str, hours: int = 24) -> None:
    """Search unified.log for *query* in the last *hours* hours."""
    print(_bold(f"=== Searching unified.log for '{query}' (last {hours}h) ==="))
    matches = search_logs(query, last_hours=hours)
    if not matches:
        print(_dim(f"  No matches found."))
        return
    for line in matches:
        if any(k in line for k in ("ERROR", "EXCEPTION", "CRITICAL")):
            print(_red(line))
        elif "WARNING" in line:
            print(_yellow(line))
        else:
            print(line)
    print(_dim(f"\n{len(matches)} match(es)."))


def cmd_list() -> None:
    """List all known agent names."""
    names = sorted(set(_AGENT_LOG_MAP.keys()))
    print(_bold("Known agent names:"))
    for name in names:
        print(f"  {name}")


# ── CLI parser (stdlib argparse) ──────────────────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="show_logs",
        description="Human-AI Swarm — Log Viewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "agent", nargs="?", default=None,
        help="Agent name to tail (e.g. 'ea', 'binance', 'hermes'). "
             "Omit to show the status table.",
    )
    parser.add_argument(
        "lines", nargs="?", type=int, default=50,
        help="Number of tail lines (default 50). Only used with [agent].",
    )
    parser.add_argument(
        "--search", "-s", metavar="QUERY",
        help="Search unified.log for this string.",
    )
    parser.add_argument(
        "--hours", type=int, default=24,
        help="Hours window for --search (default 24).",
    )
    parser.add_argument(
        "--active", "-a", action="store_true",
        help="Status table: show only active agents (modified in last 10 min).",
    )
    parser.add_argument(
        "--list", "-l", action="store_true",
        help="List all known agent names and exit.",
    )

    args = parser.parse_args()

    if args.list:
        cmd_list()
    elif args.search:
        cmd_search(args.search, hours=args.hours)
    elif args.agent:
        cmd_tail(args.agent, n=args.lines)
    else:
        cmd_status(active_only=args.active)


if __name__ == "__main__":
    main()
