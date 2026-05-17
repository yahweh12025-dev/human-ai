#!/usr/bin/env python3
"""
autosocial.py — Focused automode for Social/Video agents.

Manages:
  - VIDEO-PRODUCE-BUY, VIDEO-PRODUCE-SELL, VIDEO-PRODUCE-UPDATE tasks (every 4 hours)
  - FAITHNEXUS-VIDEO task (daily, morning between 06:00–09:00 local)
  - VIDEO-SYNC-GDRIVE: sync produced videos to GDrive after production
  - Update VIDEO_INDEX.json after each production run

Loop interval: 300 seconds (5 minutes)
Log: data/logs/autosocial.log
PID: data/logs/autosocial.pid
"""

from __future__ import annotations

import json
import os
import re
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
        inject_idle_tasks,
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

    def inject_idle_tasks(*_a, **_kw) -> int:  # type: ignore[misc]
        return 0

    _LOW_WATERMARK = 5


# ── Constants ─────────────────────────────────────────────────
_LOG_FILE   = _LOG_DIR / "autosocial.log"
_PID_FILE   = _LOG_DIR / "autosocial.pid"
_TASKS_FILE = _PROJECT_ROOT / "unified_tasks.json"

_PRODUCE_VIDEO_SCRIPT   = _PROJECT_ROOT / "scripts" / "produce_video.py"
_FAITHNEXUS_SCRIPT      = _PROJECT_ROOT / "scripts" / "produce_faithnexus_video.py"
_VIDEO_INDEX            = _PROJECT_ROOT / "data" / "media_output" / "VIDEO_INDEX.json"

_LOOP_INTERVAL       = 300    # 5 minutes
_VIDEO_INTERVAL_S    = 4 * 60 * 60   # 4 hours
_FAITHNEXUS_HOUR_MIN = 6     # earliest hour to fire FaithNexus (06:00)
_FAITHNEXUS_HOUR_MAX = 9     # latest  hour to fire FaithNexus (09:00)

_running = True

# Track last run timestamps (persist across loop iterations, reset on restart)
_last_video_run:     float = 0.0
_last_faithnexus_day: str  = ""   # ISO date string "YYYY-MM-DD"


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
    _agent_log("autosocial", msg)


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


# ── VIDEO_INDEX helpers ───────────────────────────────────────

def _load_video_index() -> dict:
    if not _VIDEO_INDEX.exists():
        return {"videos": [], "last_updated": ""}
    try:
        return json.loads(_VIDEO_INDEX.read_text())
    except Exception:
        return {"videos": [], "last_updated": ""}


def _save_video_index(idx: dict) -> None:
    idx["last_updated"] = datetime.now().isoformat()
    _VIDEO_INDEX.parent.mkdir(parents=True, exist_ok=True)
    _VIDEO_INDEX.write_text(json.dumps(idx, indent=2))


def _register_video(filepath: str, signal_type: str, platform: str = "tiktok") -> None:
    """Add a produced video to VIDEO_INDEX.json."""
    idx = _load_video_index()
    p = Path(filepath)
    entry = {
        "filename": p.name,
        "path": str(p),
        "signal": signal_type,
        "platform": platform,
        "produced_at": datetime.now().isoformat(),
        "size_bytes": p.stat().st_size if p.exists() else 0,
    }
    # Dedup by filename
    existing_names = {v["filename"] for v in idx.get("videos", [])}
    if p.name not in existing_names:
        idx.setdefault("videos", []).append(entry)
        _save_video_index(idx)
        _log(f"[VIDEO-INDEX] Registered: {p.name}")
    else:
        _log(f"[VIDEO-INDEX] Already indexed: {p.name}")


def _dedup_video_index() -> None:
    """Remove duplicate entries from VIDEO_INDEX.json."""
    idx = _load_video_index()
    seen: set = set()
    deduped = []
    for v in idx.get("videos", []):
        name = v.get("filename", "")
        if name and name not in seen:
            seen.add(name)
            deduped.append(v)
    before = len(idx.get("videos", []))
    idx["videos"] = deduped
    after = len(deduped)
    if before != after:
        _save_video_index(idx)
        _log(f"[VIDEO-INDEX] Deduplication: {before} → {after} entries")


# ── GDrive sync ───────────────────────────────────────────────

def _sync_videos_to_gdrive() -> None:
    """Sync produced video directories to GDrive."""
    _log("[VIDEO-SYNC] Syncing videos to GDrive ...")
    sync_pairs = [
        ("data/media_output/trading/all", "gdrive:videos/trading"),
        ("data/media_output/christian",   "gdrive:videos/christian"),
        ("data/media_output/faithnexus",  "gdrive:videos/christian"),
    ]
    for local_rel, remote in sync_pairs:
        local_abs = _PROJECT_ROOT / local_rel
        if not local_abs.exists():
            _log(f"[VIDEO-SYNC] Skip (not found): {local_rel}")
            continue
        try:
            result = subprocess.run(
                ["rclone", "sync", str(local_abs), remote, "--no-traverse"],
                capture_output=True, text=True, timeout=120,
                cwd=str(_PROJECT_ROOT),
            )
            status = "OK" if result.returncode == 0 else result.stderr[:100]
            _log(f"[VIDEO-SYNC] {local_rel} → {remote}: {status}")
        except FileNotFoundError:
            _log("[VIDEO-SYNC] rclone not found — skipping GDrive sync")
            break
        except subprocess.TimeoutExpired:
            _log(f"[VIDEO-SYNC] Timeout syncing {local_rel}")
        except Exception as exc:
            _log(f"[VIDEO-SYNC] Error: {exc}")


# ── Video production helpers ──────────────────────────────────

def _run_produce_video(args: list[str], timeout: int = 300) -> tuple[bool, str]:
    """Run produce_video.py with given args. Returns (success, output)."""
    if not _PRODUCE_VIDEO_SCRIPT.exists():
        return False, f"produce_video.py not found: {_PRODUCE_VIDEO_SCRIPT}"
    cmd = [sys.executable, str(_PRODUCE_VIDEO_SCRIPT)] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, cwd=str(_PROJECT_ROOT),
        )
        output = (result.stdout + result.stderr).strip()
        success = result.returncode == 0
        return success, output
    except subprocess.TimeoutExpired:
        return False, f"Timeout after {timeout}s"
    except Exception as exc:
        return False, str(exc)


def _write_pow(name: str, content: str) -> None:
    pow_dir = _PROJECT_ROOT / "data" / "logs" / "pow"
    pow_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    (pow_dir / f"{name}_{ts}.md").write_text(
        f"# autosocial — {name} — {ts}\n\n"
        f"**Date:** {datetime.now().isoformat()}\n\n"
        f"## Output\n\n```\n{content[:3000]}\n```\n"
    )


# ── Scheduled tasks ───────────────────────────────────────────

def _run_video_production_cycle() -> None:
    """Run BUY / SELL / UPDATE video production cycle."""
    global _last_video_run

    _log("[VIDEO-CYCLE] Starting BUY/SELL/UPDATE video production ...")
    _agent_log("social", "[VIDEO-CYCLE] Starting video production cycle")

    for signal_type, extra_args in [
        ("BUY",  ["--signal", "BUY"]),
        ("SELL", ["--signal", "SELL"]),
        ("UPDATE", ["--topic", "XAUUSD daily market analysis and key levels",
                    "--platform", "youtube_shorts", "--duration", "45"]),
    ]:
        _log(f"[VIDEO-CYCLE] Producing {signal_type} video ...")
        success, output = _run_produce_video(extra_args, timeout=300)
        _log(f"[VIDEO-CYCLE] {signal_type}: {'OK' if success else 'FAILED'} — {output[-200:]}")
        _write_pow(f"video_produce_{signal_type.lower()}", output)
        _agent_log("social", f"[VIDEO-{signal_type}] {'OK' if success else 'FAILED'}: {output[-100:]}")

        # Try to extract output path from script output and register in index
        path_match = re.search(r"(data/media_output/\S+\.(?:mp4|mov|avi))", output)
        if path_match:
            _register_video(str(_PROJECT_ROOT / path_match.group(1)), signal_type)

    _last_video_run = time.time()

    # Sync after production
    _sync_videos_to_gdrive()
    _dedup_video_index()
    _log("[VIDEO-CYCLE] Cycle complete")


def _run_faithnexus_video() -> None:
    """Produce daily FaithNexus scripture video (morning window only)."""
    global _last_faithnexus_day

    today = datetime.now().strftime("%Y-%m-%d")
    now_hour = datetime.now().hour

    if _last_faithnexus_day == today:
        return  # already ran today
    if not (_FAITHNEXUS_HOUR_MIN <= now_hour < _FAITHNEXUS_HOUR_MAX):
        return  # outside morning window

    if not _FAITHNEXUS_SCRIPT.exists():
        _log(f"[FAITHNEXUS] Script not found: {_FAITHNEXUS_SCRIPT}")
        return

    _log("[FAITHNEXUS] Producing FaithNexus scripture video ...")
    _agent_log("social", "[FAITHNEXUS] Starting daily scripture video production")

    try:
        result = subprocess.run(
            [sys.executable, str(_FAITHNEXUS_SCRIPT), "--auto"],
            capture_output=True, text=True,
            timeout=300, cwd=str(_PROJECT_ROOT),
        )
        output = (result.stdout + result.stderr).strip()
        success = result.returncode == 0 and "SUCCESS" in output
        _log(f"[FAITHNEXUS] {'OK' if success else 'FAILED'} — {output[-300:]}")
        _write_pow("faithnexus_video", output)
        _agent_log("social", f"[FAITHNEXUS] {'OK' if success else 'FAILED'}: {output[-100:]}")

        if success:
            _last_faithnexus_day = today
            # Sync christian videos to GDrive
            try:
                subprocess.run(
                    ["rclone", "sync",
                     str(_PROJECT_ROOT / "data" / "media_output" / "faithnexus"),
                     "gdrive:videos/christian", "--no-traverse"],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(_PROJECT_ROOT),
                )
                _log("[FAITHNEXUS] Synced to gdrive:videos/christian")
            except Exception as exc:
                _log(f"[FAITHNEXUS] GDrive sync error: {exc}")

    except subprocess.TimeoutExpired:
        _log("[FAITHNEXUS] Timeout after 300s")
    except Exception as exc:
        _log(f"[FAITHNEXUS] Exception: {exc}")


# ── Task injection for social agents ─────────────────────────

def _inject_social_tasks() -> None:
    if not _TASKS_FILE.exists():
        return
    try:
        injected = inject_idle_tasks(_TASKS_FILE, "social", _LOW_WATERMARK)
        if injected:
            _log(f"[INJECT] {injected} task(s) injected for agent 'social'")
    except Exception as exc:
        _log(f"[INJECT] Error: {exc}")


# ── Main loop ─────────────────────────────────────────────────

def main() -> None:
    global _running

    print("=" * 70)
    print("  autosocial.py — Social/Video Production Automode")
    print(f"  Project root    : {_PROJECT_ROOT}")
    print(f"  Log             : {_LOG_FILE}")
    print(f"  PID             : {_PID_FILE}")
    print(f"  Loop interval   : {_LOOP_INTERVAL}s (5 min)")
    print(f"  Video interval  : {_VIDEO_INTERVAL_S//3600}h")
    print(f"  FaithNexus hour : {_FAITHNEXUS_HOUR_MIN:02d}:00–{_FAITHNEXUS_HOUR_MAX:02d}:00")
    print(f"  automode        : {'available' if _AUTOMODE_AVAILABLE else 'UNAVAILABLE (standalone mode)'}")
    print("=" * 70)

    _write_pid()
    _log(f"[START] autosocial started (PID={os.getpid()})")

    # Run video production immediately on first launch
    _run_video_production_cycle()
    _run_faithnexus_video()

    _loop_count = 0

    try:
        while _running:
            _loop_count += 1
            now = time.time()
            _log(f"[LOOP #{_loop_count}] ---- autosocial cycle ----")

            # 1. Video production cycle every 4 hours
            if now - _last_video_run >= _VIDEO_INTERVAL_S:
                _run_video_production_cycle()

            # 2. FaithNexus daily morning video
            _run_faithnexus_video()

            # 3. Inject social agent tasks
            if _loop_count % 3 == 0:
                _inject_social_tasks()

            # 4. Periodic dedup check
            if _loop_count % 12 == 0:
                _dedup_video_index()

            _log(f"[LOOP #{_loop_count}] Sleeping {_LOOP_INTERVAL}s ...")
            time.sleep(_LOOP_INTERVAL)

    except KeyboardInterrupt:
        _log("[STOP] KeyboardInterrupt — shutting down")
    finally:
        _running = False
        _remove_pid()
        _log("[STOP] autosocial stopped cleanly")


if __name__ == "__main__":
    main()
