"""
vault_logger.py — Centralized Obsidian vault logging for all swarm agents.

Usage:
    from core.integrations.vault_logger import vault_log, vault_read, vault_append

    vault_log("hermes", "DECISION", "Chose ATR-based SL over fixed % due to volatility", data={"atr": 1.5})
    vault_log("openclaw", "HEALTH", "All agents nominal", data={"ea": "RUNNING", "binance": "DOWN"})
    vault_log("opencode", "CODE_CHANGE", "Updated Binance v10 TP multiplier", data={"file": "live_trading_binance.py"})

    vault_log("social", "VIDEO", "Produced XAUUSD BUY signal video", data={"output": "path/to/video.mp4"})
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_VAULT_ROOT = Path(__file__).resolve().parents[2] / "data" / "obsidian"

_AGENT_DIRS = {
    "openclaw":   _VAULT_ROOT / "agents" / "openclaw",
    "hermes":     _VAULT_ROOT / "agents" / "hermes",
    "opencode":   _VAULT_ROOT / "agents" / "opencode",
    "social":     _VAULT_ROOT / "agents" / "social",
    "social_media": _VAULT_ROOT / "agents" / "social",
    "pai":        _VAULT_ROOT / "agents" / "shared",
    "gsd":        _VAULT_ROOT / "agents" / "shared",
    "automode":   _VAULT_ROOT / "system" / "sessions",
    "ea":         _VAULT_ROOT / "trading" / "ea",
    "binance":    _VAULT_ROOT / "trading" / "binance",
}

_SECTION_DIRS = {
    "trading/ea":       _VAULT_ROOT / "trading" / "ea",
    "trading/binance":  _VAULT_ROOT / "trading" / "binance",
    "trading/analysis": _VAULT_ROOT / "trading" / "analysis",
    "system/state":     _VAULT_ROOT / "system" / "state",
    "system/health":    _VAULT_ROOT / "system" / "health",
    "system/sessions":  _VAULT_ROOT / "system" / "sessions",
    "knowledge/docs":   _VAULT_ROOT / "knowledge" / "docs",
    "knowledge/research": _VAULT_ROOT / "knowledge" / "research",
}


def vault_log(
    agent: str,
    action_type: str,
    description: str,
    data: Optional[dict] = None,
    date: Optional[str] = None,
) -> Path:
    """
    Append a structured log entry to the agent's daily vault file.

    Args:
        agent: Agent name (openclaw, hermes, opencode, social, ea, binance, ...)
        action_type: Short tag (DECISION, CODE_CHANGE, HEALTH, SECURITY, VIDEO, TRADE, etc.)
        description: Human-readable description of what happened
        data: Optional dict of structured data to include
        date: Override date string (YYYY-MM-DD), defaults to today UTC

    Returns:
        Path to the file written
    """
    agent_lower = agent.lower().replace("-", "").replace(".", "")
    agent_dir = _AGENT_DIRS.get(agent.lower(), _VAULT_ROOT / "agents" / "shared")
    agent_dir.mkdir(parents=True, exist_ok=True)

    today = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    log_file = agent_dir / f"{today}-{agent_lower}.md"

    lines = [f"\n## [{action_type}] {ts}\n", f"{description}\n"]
    if data:
        lines.append("\n```json\n")
        lines.append(json.dumps(data, indent=2, default=str))
        lines.append("\n```\n")
    lines.append("\n---\n")

    with open(log_file, "a") as f:
        f.writelines(lines)

    return log_file


def vault_write(section: str, filename: str, content: str) -> Path:
    """
    Write or overwrite a file in a vault section.

    Args:
        section: Section path like 'system/state', 'knowledge/docs', 'agents/hermes'
        filename: Filename (e.g. 'current_context.md')
        content: Full markdown content

    Returns:
        Path written
    """
    if section in _SECTION_DIRS:
        target_dir = _SECTION_DIRS[section]
    elif section.startswith("agents/"):
        agent = section.split("/", 1)[1]
        target_dir = _VAULT_ROOT / "agents" / agent
    else:
        target_dir = _VAULT_ROOT / section

    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / filename
    path.write_text(content)
    return path


def vault_read(section: str, filename: str) -> str:
    """Read a file from the vault. Returns empty string if not found."""
    if section in _SECTION_DIRS:
        target_dir = _SECTION_DIRS[section]
    elif section.startswith("agents/"):
        agent = section.split("/", 1)[1]
        target_dir = _VAULT_ROOT / "agents" / agent
    else:
        target_dir = _VAULT_ROOT / section

    path = target_dir / filename
    return path.read_text() if path.exists() else ""


def vault_append(section: str, filename: str, content: str) -> Path:
    """Append content to a vault file (creates it if missing)."""
    if section in _SECTION_DIRS:
        target_dir = _SECTION_DIRS[section]
    elif section.startswith("agents/"):
        agent = section.split("/", 1)[1]
        target_dir = _VAULT_ROOT / "agents" / agent
    else:
        target_dir = _VAULT_ROOT / section

    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / filename
    with open(path, "a") as f:
        f.write(content)
    return path


def vault_get_agent_context(agent: str, days: int = 3) -> str:
    """
    Get recent log entries for an agent (last N days).
    Useful for agents to load their own context before starting a task.
    """
    agent_lower = agent.lower().replace("-", "").replace(".", "")
    agent_dir = _AGENT_DIRS.get(agent.lower(), _VAULT_ROOT / "agents" / "shared")

    if not agent_dir.exists():
        return ""

    from datetime import timedelta
    lines = []
    for i in range(days):
        date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        log_file = agent_dir / f"{date}-{agent_lower}.md"
        if log_file.exists():
            lines.append(f"\n# {date}\n")
            lines.append(log_file.read_text())

    return "\n".join(lines) if lines else ""
