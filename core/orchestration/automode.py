#!/usr/bin/env python3
"""
Auto Mode Controller — DECOMMISSIONED
=====================================
This script has been decommissioned. Active queue processing, task injection, 
and agent orchestration have been disabled. 

Only shared utility functions (logging, DeepSeek queries, greedy search, log readers) 
remain active for manual use and CLI introspection.
"""

import json
import time
import sys
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

_project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_project_root))
os.chdir(str(_project_root))

# ── Constants ────────────────────────────────────────────────
_LOG_DIR = _project_root / "data" / "logs"

# ── Agent log writer ─────────────────────────────────────────

def _agent_log(agent: str, msg: str):
    """Append a timestamped message to the agent's log file."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_name = agent.lower().replace('.', '').replace(' ', '_')
    log_file = _LOG_DIR / f"{log_name}.log"
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(log_file, 'a') as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

# ── DeepSeek browser agent integration ──────────────────────

def query_deepseek(prompt: str, agent: str = "automode", timeout: int = 120,
                   save_path: str = "") -> str:
    """
    Send a prompt to DeepSeek via the headless browser agent (Camoufox).
    Passes the question as a CLI argument (not stdin — script uses argparse).
    Returns the response text or empty string on failure.
    """
    _agent_log(agent, f"[DEEPSEEK] Querying: {prompt[:100]}")

    ds_script = _project_root / "scripts" / "utility" / "prompt_deepseek.py"
    if not ds_script.exists():
        _agent_log(agent, "[DEEPSEEK] Script not found")
        return ""

    cmd = [sys.executable, str(ds_script), prompt]
    if save_path:
        cmd += ["--save", save_path]

    env = {
        **os.environ,
        "DISPLAY": os.environ.get("DISPLAY", ":11"),
        "DEEPSEEK_PROMPT": prompt,   # fallback env var
    }

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, cwd=str(_project_root), env=env
        )
        if result.returncode == 0:
            out = result.stdout
            if "--- RESPONSE ---" in out:
                response = out.split("--- RESPONSE ---", 1)[1].strip()
            else:
                response = out.strip()
            if response:
                _agent_log(agent, f"[DEEPSEEK] Got {len(response)} chars")
                return response
            _agent_log(agent, f"[DEEPSEEK] Empty response (exit 0)")
        else:
            stderr_snippet = result.stderr[-300:] if result.stderr else ""
            _agent_log(agent, f"[DEEPSEEK] Exit {result.returncode}: {stderr_snippet[:200]}")
    except subprocess.TimeoutExpired:
        _agent_log(agent, f"[DEEPSEEK] Timeout after {timeout}s")
    except Exception as e:
        _agent_log(agent, f"[DEEPSEEK] Error: {e}")

    return f"[DeepSeek unavailable — session may need seeding via scripts/utility/masterseed.py]"

# ── Pi.dev greedy search ─────────────────────────────────────

def pidev_greedy_search(pattern: str, paths: List[str] = None,
                        file_types: List[str] = None, agent: str = "pi.dev") -> str:
    """
    Pi.dev greedy search: recursive grep across the codebase.
    Returns findings as a formatted string.
    """
    if paths is None:
        paths = ["agents", "apps", "core", "scripts"]
    if file_types is None:
        file_types = ["*.py", "*.yaml", "*.yml", "*.json", "*.sh"]

    _agent_log(agent, f"[GREEDY] Searching for: {pattern} in {paths}")
    results = []

    for search_path in paths:
        full_path = _project_root / search_path
        if not full_path.exists():
            continue
        for ft in file_types:
            try:
                r = subprocess.run(
                    ["grep", "-rn", "--include", ft, pattern, str(full_path)],
                    capture_output=True, text=True, timeout=30
                )
                if r.stdout.strip():
                    results.append(r.stdout.strip())
            except Exception:
                pass

    combined = "\n".join(results)
    _agent_log(agent, f"[GREEDY] Found {len(combined.splitlines())} matching lines")
    return combined or f"[No matches for '{pattern}' in {paths}]"

# ── Log reader utility ────────────────────────────────────────

class AgentLogReader:
    LOG_DIR = _LOG_DIR

    AGENT_LOGS = {
        'automode':   'automode.log',
        'openclaw':   'openclaw.log',
        'hermes':     'hermes.log',
        'opencode':   'opencode.log',
        'pi.dev':     'pidev.log',
        'researcher': 'researcher.log',
        'liveea':     'liveea.log',
        'binance':    'live_trading_binance.log',
        'social':     'social_media.log',
        'gsd':        'gsd_integration.log',
        'pai':        'pai_agent.log',
    }

    @classmethod
    def read_recent(cls, log_name: str, lines: int = 50) -> str:
        path = cls.LOG_DIR / log_name
        if not path.exists():
            return f"[Log not found: {path}]"
        try:
            all_lines = path.read_text(errors='replace').splitlines()
            return '\n'.join(all_lines[-lines:])
        except Exception as e:
            return f"[Error reading {path}: {e}]"

    @classmethod
    def find_errors(cls, log_name: str, window: int = 200) -> List[str]:
        content = cls.read_recent(log_name, window)
        return [l for l in content.splitlines()
                if any(kw in l for kw in ('ERROR', 'Error', 'EXCEPTION', 'Traceback',
                                           'failed', 'FAILED', '💥', '❌'))]

    @classmethod
    def agent_log(cls, agent: str, lines: int = 50) -> str:
        log_file = cls.AGENT_LOGS.get(agent.lower().replace('.', ''))
        if not log_file:
            log_file = f"{agent.lower()}.log"
        return cls.read_recent(log_file, lines)

    @classmethod
    def automode_errors(cls) -> List[str]:
        return cls.find_errors('automode.log')

    @classmethod
    def summarise_all(cls) -> str:
        lines = ["=== Log Health Summary ==="]
        for agent, log_file in cls.AGENT_LOGS.items():
            errors = cls.find_errors(log_file, 100)
            path = cls.LOG_DIR / log_file
            size = f"{path.stat().st_size//1024}KB" if path.exists() else "missing"
            lines.append(f"  {agent:<12} [{size}]  errors={len(errors)}")
        return '\n'.join(lines)

# ── CLI entry point ───────────────────────────────────────────

def main():
    if '--logs' in sys.argv:
        idx = sys.argv.index('--logs')
        agent = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else 'automode'
        print(AgentLogReader.agent_log(agent, lines=80))
        return

    if '--deepseek' in sys.argv:
        idx = sys.argv.index('--deepseek')
        question = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "What trading improvements can I make?"
        print(f"Querying DeepSeek: {question}")
        response = query_deepseek(question)
        print(response)
        return

    print("=========================================================")
    print("🤖 AutoMode Controller is DECOMMISSIONED.")
    print("Active task queues, loop execution, and automatic")
    print("task generation are disabled.")
    print("=========================================================")
    print("Available CLI commands:")
    print("  python3 automode.py --logs [agent]     - view recent logs")
    print("  python3 automode.py --deepseek [query]  - run DeepSeek query")
    print()

if __name__ == "__main__":
    main()
