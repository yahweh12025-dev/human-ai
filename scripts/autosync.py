#!/usr/bin/env python3
"""
autosync.py — Standalone sync/backup script (replaces fragmented sync approaches).

Sync operations (each idempotent, independent — failure of one doesn't stop others):
  1. Obsidian vault → GDrive: rclone sync data/obsidian gdrive:backups/obsidian
  2. Supabase backup: run scripts/backup_supabase_to_gdrive.sh
  3. Firebase backup: run scripts/system/backup_to_cloud.py
  4. Dify sync: from core.integrations.dify_brain import DifyBrain
  5. Graphify sync: run scripts/sync/dify_graphify_bridge.py
  6. .env backup: rclone copy .env gdrive:backups/env/
  7. VIDEO_INDEX.json: sync to gdrive:videos/VIDEO_INDEX.json
  8. Git status check: warn if uncommitted changes > 5 files

Runs once immediately on launch, then every 6 hours.
Logs with timestamps to data/logs/autosync.log
Writes summary to data/obsidian/system/state/sync_status.json
PID: data/logs/autosync.pid
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
    from automode import _agent_log, _LOG_DIR
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


# ── Constants ─────────────────────────────────────────────────
_LOG_FILE      = _LOG_DIR / "autosync.log"
_PID_FILE      = _LOG_DIR / "autosync.pid"
_SYNC_INTERVAL = 6 * 60 * 60   # 6 hours in seconds

_OBSIDIAN_DIR      = _PROJECT_ROOT / "data" / "obsidian"
_VIDEO_INDEX       = _PROJECT_ROOT / "data" / "media_output" / "VIDEO_INDEX.json"
_SUPABASE_SCRIPT   = _PROJECT_ROOT / "scripts" / "backup_supabase_to_gdrive.sh"
_FIREBASE_SCRIPT   = _PROJECT_ROOT / "scripts" / "system" / "backup_to_cloud.py"
_GRAPHIFY_SCRIPT   = _PROJECT_ROOT / "scripts" / "sync" / "dify_graphify_bridge.py"
_STATUS_FILE       = _OBSIDIAN_DIR / "system" / "state" / "sync_status.json"
_GIT_WARN_THRESHOLD = 5   # warn if more than this many uncommitted files

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
    _agent_log("autosync", msg)


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


# ── Summary writer ────────────────────────────────────────────

def _write_status(results: dict) -> None:
    """Write sync summary to data/obsidian/system/state/sync_status.json."""
    _STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_sync": datetime.now().isoformat(),
        "results": results,
    }
    try:
        _STATUS_FILE.write_text(json.dumps(payload, indent=2))
        _log(f"[STATUS] Summary written to {_STATUS_FILE}")
    except Exception as exc:
        _log(f"[STATUS] Could not write summary: {exc}")


# ── Individual sync steps ─────────────────────────────────────

def _step_obsidian_gdrive() -> str:
    """1. Sync Obsidian vault to GDrive."""
    if not _OBSIDIAN_DIR.exists():
        return "SKIP (obsidian dir not found)"
    try:
        result = subprocess.run(
            ["rclone", "sync", str(_OBSIDIAN_DIR), "gdrive:backups/obsidian",
             "--no-traverse"],
            capture_output=True, text=True, timeout=300,
            cwd=str(_PROJECT_ROOT),
        )
        if result.returncode == 0:
            return "OK"
        return f"FAIL: {result.stderr[:150]}"
    except FileNotFoundError:
        return "SKIP (rclone not found)"
    except subprocess.TimeoutExpired:
        return "FAIL: timeout 300s"
    except Exception as exc:
        return f"FAIL: {exc}"


def _step_supabase_backup() -> str:
    """2. Run Supabase → GDrive backup script."""
    if not _SUPABASE_SCRIPT.exists():
        return "SKIP (script not found)"
    try:
        result = subprocess.run(
            ["bash", str(_SUPABASE_SCRIPT)],
            capture_output=True, text=True, timeout=300,
            cwd=str(_PROJECT_ROOT),
        )
        if result.returncode == 0:
            return "OK"
        return f"FAIL: {result.stderr[:150]}"
    except subprocess.TimeoutExpired:
        return "FAIL: timeout 300s"
    except Exception as exc:
        return f"FAIL: {exc}"


def _step_firebase_backup() -> str:
    """3. Run Firebase backup script."""
    if not _FIREBASE_SCRIPT.exists():
        return "SKIP (script not found)"
    try:
        result = subprocess.run(
            [sys.executable, str(_FIREBASE_SCRIPT)],
            capture_output=True, text=True, timeout=300,
            cwd=str(_PROJECT_ROOT),
        )
        if result.returncode == 0:
            return "OK"
        return f"FAIL: {result.stderr[:150]}"
    except subprocess.TimeoutExpired:
        return "FAIL: timeout 300s"
    except Exception as exc:
        return f"FAIL: {exc}"


def _step_dify_sync() -> str:
    """4. Trigger Dify brain sync."""
    try:
        from core.integrations.dify_brain import DifyBrain
        brain = DifyBrain()
        # Attempt a lightweight sync — try available methods
        if hasattr(brain, "sync"):
            brain.sync()
            return "OK (sync)"
        elif hasattr(brain, "health_check"):
            brain.health_check()
            return "OK (health_check)"
        return "OK (imported — no sync method)"
    except ImportError:
        return "SKIP (dify_brain not importable)"
    except Exception as exc:
        return f"FAIL: {exc}"


def _step_graphify_sync() -> str:
    """5. Run Graphify bridge sync."""
    if not _GRAPHIFY_SCRIPT.exists():
        return "SKIP (script not found)"
    try:
        result = subprocess.run(
            [sys.executable, str(_GRAPHIFY_SCRIPT)],
            capture_output=True, text=True, timeout=300,
            cwd=str(_PROJECT_ROOT),
        )
        if result.returncode == 0:
            return "OK"
        return f"FAIL: {result.stderr[:150]}"
    except subprocess.TimeoutExpired:
        return "FAIL: timeout 300s"
    except Exception as exc:
        return f"FAIL: {exc}"


def _step_env_backup() -> str:
    """6. Backup .env to GDrive (excludes secrets from git but keeps cloud copy)."""
    env_path = _PROJECT_ROOT / ".env"
    if not env_path.exists():
        return "SKIP (.env not found)"
    try:
        result = subprocess.run(
            ["rclone", "copy", str(env_path), "gdrive:backups/env/"],
            capture_output=True, text=True, timeout=60,
            cwd=str(_PROJECT_ROOT),
        )
        if result.returncode == 0:
            return "OK"
        return f"FAIL: {result.stderr[:150]}"
    except FileNotFoundError:
        return "SKIP (rclone not found)"
    except subprocess.TimeoutExpired:
        return "FAIL: timeout 60s"
    except Exception as exc:
        return f"FAIL: {exc}"


def _step_video_index_sync() -> str:
    """7. Sync VIDEO_INDEX.json to GDrive."""
    if not _VIDEO_INDEX.exists():
        return "SKIP (VIDEO_INDEX.json not found)"
    try:
        result = subprocess.run(
            ["rclone", "copy", str(_VIDEO_INDEX), "gdrive:backups/"],
            capture_output=True, text=True, timeout=60,
            cwd=str(_PROJECT_ROOT),
        )
        if result.returncode == 0:
            return "OK"
        return f"FAIL: {result.stderr[:150]}"
    except FileNotFoundError:
        return "SKIP (rclone not found)"
    except subprocess.TimeoutExpired:
        return "FAIL: timeout 60s"
    except Exception as exc:
        return f"FAIL: {exc}"


def _step_git_status_check() -> str:
    """8. Warn if git has too many uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=15,
            cwd=str(_PROJECT_ROOT),
        )
        lines = [l for l in result.stdout.splitlines() if l.strip()]
        count = len(lines)
        if count > _GIT_WARN_THRESHOLD:
            _log(f"[GIT-CHECK] WARNING: {count} uncommitted changes (threshold {_GIT_WARN_THRESHOLD})")
            return f"WARN: {count} uncommitted files"
        return f"OK ({count} modified)"
    except subprocess.TimeoutExpired:
        return "FAIL: timeout"
    except Exception as exc:
        return f"FAIL: {exc}"


# ── Full sync run ─────────────────────────────────────────────

def run_sync() -> dict:
    """Run all sync steps. Returns dict of step_name → status."""
    _log("[SYNC] Starting full sync cycle ...")

    steps = [
        ("obsidian_gdrive",   _step_obsidian_gdrive),
        ("supabase_backup",   _step_supabase_backup),
        ("firebase_backup",   _step_firebase_backup),
        ("dify_sync",         _step_dify_sync),
        ("graphify_sync",     _step_graphify_sync),
        ("env_backup",        _step_env_backup),
        ("video_index_sync",  _step_video_index_sync),
        ("git_status_check",  _step_git_status_check),
    ]

    results: dict = {}
    for step_name, step_fn in steps:
        _log(f"[SYNC] Step: {step_name} ...")
        try:
            status = step_fn()
        except Exception as exc:
            status = f"EXCEPTION: {exc}"
        results[step_name] = status
        _log(f"[SYNC] {step_name}: {status}")
        _agent_log("autosync", f"[{step_name.upper()}] {status}")

    ok_count   = sum(1 for v in results.values() if v.startswith("OK"))
    skip_count = sum(1 for v in results.values() if v.startswith("SKIP"))
    fail_count = sum(1 for v in results.values() if v.startswith("FAIL") or v.startswith("EXCEPTION"))
    warn_count = sum(1 for v in results.values() if v.startswith("WARN"))

    summary = (f"[SYNC] COMPLETE — OK={ok_count} SKIP={skip_count} "
               f"FAIL={fail_count} WARN={warn_count}")
    _log(summary)
    _write_status(results)
    return results


# ── Main loop ─────────────────────────────────────────────────

def main() -> None:
    global _running

    print("=" * 70)
    print("  autosync.py — Standalone Sync/Backup Script")
    print(f"  Project root   : {_PROJECT_ROOT}")
    print(f"  Log            : {_LOG_FILE}")
    print(f"  PID            : {_PID_FILE}")
    print(f"  Sync interval  : {_SYNC_INTERVAL // 3600}h")
    print(f"  automode       : {'available' if _AUTOMODE_AVAILABLE else 'UNAVAILABLE (standalone mode)'}")
    print("=" * 70)

    _write_pid()
    _log(f"[START] autosync started (PID={os.getpid()})")

    # Run once immediately on launch
    run_sync()

    _loop_count = 0

    try:
        while _running:
            _log(f"[SCHEDULE] Next sync in {_SYNC_INTERVAL // 3600}h — sleeping ...")
            # Sleep in small increments so SIGTERM is handled promptly
            elapsed = 0
            while _running and elapsed < _SYNC_INTERVAL:
                time.sleep(60)
                elapsed += 60

            if not _running:
                break

            _loop_count += 1
            _log(f"[LOOP #{_loop_count}] ---- autosync cycle ----")
            run_sync()

    except KeyboardInterrupt:
        _log("[STOP] KeyboardInterrupt — shutting down")
    finally:
        _running = False
        _remove_pid()
        _log("[STOP] autosync stopped cleanly")


if __name__ == "__main__":
    main()
