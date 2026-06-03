#!/usr/bin/env python3
"""
Log Consolidator
================
Unified logging for the Human-AI swarm.  Drop-in replacement for
``import logging`` — every logger writes to both its own per-agent file
and to a shared ``unified.log`` that aggregates all agents.

Usage
-----
    from core.utils.log_consolidator import get_logger

    log = get_logger("hermes")
    log.info("Strategy update complete")
    log.warning("Drawdown threshold approached")
    log.error("Order failed: %s", err)

Rotation policy
---------------
- Per-agent file : 10 MB max, 3 backups  → data/logs/{name}.log
- unified.log    : 50 MB max, 5 backups  → data/logs/unified.log

Unified format
--------------
    [2026-05-15 14:32:01] [hermes] [INFO] Strategy update complete
"""

from __future__ import annotations

import logging
import os
import sys
from collections import deque
from datetime import datetime, timezone, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR: Path = Path(os.getenv("LOG_DIR", str(_PROJECT_ROOT / "data" / "logs")))
_UNIFIED_LOG: Path = _LOG_DIR / "unified.log"

# ── Registry: one stdlib logger per name ──────────────────────────────────
_LOGGERS: dict[str, logging.Logger] = {}


# ── Unified formatter ─────────────────────────────────────────────────────
class _UnifiedFormatter(logging.Formatter):
    """Formats records as [TIMESTAMP] [AGENT] [LEVEL] message."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        agent = getattr(record, "agent_name", record.name)
        level = record.levelname
        msg = record.getMessage()
        if record.exc_info:
            msg = msg + "\n" + self.formatException(record.exc_info)
        return f"[{ts}] [{agent}] [{level}] {msg}"


# ── Per-agent formatter ────────────────────────────────────────────────────
class _AgentFormatter(logging.Formatter):
    """Human-readable format for the per-agent file."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = record.getMessage()
        if record.exc_info:
            msg = msg + "\n" + self.formatException(record.exc_info)
        return f"[{ts}] [{record.levelname}] {msg}"


def _ensure_log_dir() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


def _build_unified_handler() -> RotatingFileHandler:
    """Return (or reuse) the shared unified.log handler."""
    _ensure_log_dir()
    handler = RotatingFileHandler(
        _UNIFIED_LOG,
        maxBytes=50 * 1024 * 1024,  # 50 MB
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(_UnifiedFormatter())
    handler.setLevel(logging.DEBUG)
    return handler


# Singleton unified handler — created once, shared by all loggers.
_unified_handler: Optional[RotatingFileHandler] = None


def _get_unified_handler() -> RotatingFileHandler:
    global _unified_handler
    if _unified_handler is None:
        _unified_handler = _build_unified_handler()
    return _unified_handler


def get_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Return a Python ``logging.Logger`` that writes to:
      • data/logs/{name}.log   (10 MB, 3 backups)
      • data/logs/unified.log  (50 MB, 5 backups)

    The logger is cached; repeated calls with the same *name* return the
    same instance.

    Parameters
    ----------
    name:
        Agent or component name, e.g. ``"hermes"``, ``"binance"``.
        Used as the log-file stem and the ``[AGENT]`` field in unified.log.
    level:
        Minimum log level (default DEBUG — all messages are recorded).
    """
    safe_name = name.lower().replace(".", "").replace(" ", "_")
    if safe_name in _LOGGERS:
        return _LOGGERS[safe_name]

    _ensure_log_dir()

    logger = logging.getLogger(f"swarm.{safe_name}")
    logger.setLevel(level)
    # Prevent propagation to root logger to avoid duplicate console output.
    logger.propagate = False

    # ── Per-agent rotating file handler ──────────────────────────────────
    agent_log_path = _LOG_DIR / f"{safe_name}.log"
    agent_handler = RotatingFileHandler(
        agent_log_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=3,
        encoding="utf-8",
    )
    agent_handler.setFormatter(_AgentFormatter())
    agent_handler.setLevel(level)
    logger.addHandler(agent_handler)

    # ── Shared unified handler ────────────────────────────────────────────
    unified_handler = _get_unified_handler()
    # Attach a filter so the unified handler can stamp the agent name.
    class _AgentFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.agent_name = safe_name
            return True

    # Clone the unified handler to attach the agent-specific filter without
    # affecting other agents' records.
    clone = RotatingFileHandler(
        _UNIFIED_LOG,
        maxBytes=50 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    clone.setFormatter(_UnifiedFormatter())
    clone.setLevel(level)
    clone.addFilter(_AgentFilter())
    logger.addHandler(clone)

    _LOGGERS[safe_name] = logger
    return logger


# ── Utility functions ──────────────────────────────────────────────────────

def tail_log(name: str, n: int = 50) -> list[str]:
    """
    Return the last *n* lines from the named agent's log file.

    Parameters
    ----------
    name:
        Agent name, e.g. ``"hermes"`` → reads ``data/logs/hermes.log``.
    n:
        Number of tail lines to return (default 50).

    Returns
    -------
    list[str]
        Lines from the end of the file, or a single-element list with an
        error message if the file cannot be read.
    """
    safe_name = name.lower().replace(".", "").replace(" ", "_")
    log_path = _LOG_DIR / f"{safe_name}.log"
    if not log_path.exists():
        return [f"[log not found: {log_path}]"]
    try:
        lines = log_path.read_text(errors="replace").splitlines()
        return lines[-n:]
    except Exception as exc:
        return [f"[error reading {log_path}: {exc}]"]


def search_logs(query: str, last_hours: int = 24) -> list[str]:
    """
    Search ``unified.log`` for lines containing *query* within the last
    *last_hours* hours.

    The search is case-insensitive.  Lines are returned in chronological
    order (oldest first).

    Parameters
    ----------
    query:
        Substring to look for.
    last_hours:
        Only return lines whose timestamp falls within this many hours
        before now.  If a line's timestamp cannot be parsed the line is
        still included.

    Returns
    -------
    list[str]
        Matching log lines.
    """
    if not _UNIFIED_LOG.exists():
        return [f"[unified.log not found: {_UNIFIED_LOG}]"]

    cutoff = datetime.now() - timedelta(hours=last_hours)
    query_lower = query.lower()
    matches: list[str] = []

    try:
        for raw_line in _UNIFIED_LOG.read_text(errors="replace").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if query_lower not in line.lower():
                continue
            # Attempt to parse timestamp for time-window filtering.
            # Unified format: [2026-05-15 14:32:01] [agent] [LEVEL] ...
            try:
                ts_str = line[1:20]  # Extract between first [ and ]
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                if ts < cutoff:
                    continue
            except (ValueError, IndexError):
                pass  # Can't parse — include the line anyway
            matches.append(line)
    except Exception as exc:
        return [f"[error reading unified.log: {exc}]"]

    return matches


# ── Module self-test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    log = get_logger("test_consolidator")
    log.info("Log consolidator self-test — INFO")
    log.warning("Log consolidator self-test — WARNING")
    log.error("Log consolidator self-test — ERROR")
    print("Per-agent tail (last 3 lines):")
    for line in tail_log("test_consolidator", n=3):
        print(" ", line)
    print("\nSearch unified.log for 'self-test':")
    for line in search_logs("self-test", last_hours=1):
        print(" ", line)
    print("\nDone. Check data/logs/test_consolidator.log and data/logs/unified.log")
