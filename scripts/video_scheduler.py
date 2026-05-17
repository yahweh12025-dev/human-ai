#!/usr/bin/env python3
"""
Video Scheduler — 3 videos per day, fully autonomous
=====================================================
Produces 3 videos on a fixed daily schedule:
  06:00 UTC — FaithNexus scripture video (daily devotional)
  12:00 UTC — Trading signal video (midday market update)
  18:00 UTC — FaithNexus scripture video (evening encouragement)

Run as a daemon:  nohup python3 scripts/video_scheduler.py > data/logs/video_scheduler.log 2>&1 &
Stop:             kill $(cat agents/trading-agent/trades/mt5/video_scheduler.pid)

Each run produces a video, logs timing, and queues it to Postiz if configured.
"""

import os
import sys
import json
import time
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

LOG_DIR  = PROJECT_ROOT / "data" / "logs"
PID_FILE = PROJECT_ROOT / "data" / "logs" / "video_scheduler.pid"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Video Mode Control ────────────────────────────────────────
# MODE is read from data/config/video_mode.json at runtime.
# "christian" (default): all slots produce FaithNexus/biblical videos.
# "trading": all slots produce trading signal videos.
# OpenClaw can switch modes by writing to video_mode.json.
MODE_FILE = PROJECT_ROOT / "data" / "config" / "video_mode.json"
(PROJECT_ROOT / "data" / "config").mkdir(parents=True, exist_ok=True)
if not MODE_FILE.exists():
    MODE_FILE.write_text('{"mode": "christian"}')  # default: christian

def get_video_mode() -> str:
    """Read current video mode. Defaults to christian."""
    try:
        return json.loads(MODE_FILE.read_text()).get("mode", "christian")
    except Exception:
        return "christian"

def set_video_mode(mode: str):
    """OpenClaw calls this to switch between christian and trading modes."""
    assert mode in ("christian", "trading"), f"Invalid mode: {mode}"
    MODE_FILE.write_text(json.dumps({"mode": mode, "set_at": datetime.now(timezone.utc).isoformat()}))
    print(f"[SCHEDULER] Mode switched to: {mode}")

# ── Schedule: 4 videos per day ────────────────────────────────
# In "christian" mode: all slots → FaithNexus/biblical videos
# In "trading" mode: OpenClaw has requested trading signal videos
SCHEDULE_HOURS = [6, 10, 14, 18]  # 4 videos/day at these UTC hours

_running = True

def _stop(*_):
    global _running
    _running = False
    print("[SCHEDULER] Stopping...")

signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT,  _stop)


def _log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line, flush=True)


def produce_faithnexus() -> dict:
    """Run produce_faithnexus_video.py --auto, return timing + result."""
    script = PROJECT_ROOT / "scripts" / "produce_faithnexus_video.py"
    start  = time.time()
    _log("Starting FaithNexus video production...")
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--auto"],
            capture_output=True, text=True, timeout=600, cwd=str(PROJECT_ROOT)
        )
        elapsed = round(time.time() - start, 1)
        success = proc.returncode == 0
        output  = proc.stdout[-1000:] + (proc.stderr[-300:] if proc.stderr else "")
        _log(f"FaithNexus done in {elapsed}s | success={success}")
        if not success:
            _log(f"  ERROR: {proc.stderr[-300:]}")
        return {"type": "faithnexus", "success": success, "elapsed_s": elapsed, "output": output}
    except subprocess.TimeoutExpired:
        _log("FaithNexus TIMEOUT after 600s")
        return {"type": "faithnexus", "success": False, "elapsed_s": 600, "error": "timeout"}
    except Exception as e:
        _log(f"FaithNexus EXCEPTION: {e}")
        return {"type": "faithnexus", "success": False, "error": str(e)}


def _pick_daily_topic() -> str:
    """Return a topic from the rotating TRADING_TOPICS list keyed to today's date."""
    import importlib
    try:
        mg = importlib.import_module("agents.social.media_generator")
        topics = mg.TRADING_TOPICS
        # Deterministic daily rotation — same topic all day, new one each day
        idx = datetime.now(timezone.utc).toordinal() % len(topics)
        return topics[idx]
    except Exception:
        return "XAUUSD gold market midday analysis and key levels"


def produce_trading(topic: str = None, signal: str = None, platform: str = "tiktok") -> dict:
    """Run produce_video.py, return timing + result."""
    script = PROJECT_ROOT / "scripts" / "produce_video.py"
    start  = time.time()
    topic  = topic or _pick_daily_topic()
    cmd    = [sys.executable, str(script), "--platform", platform,
              "--topic", topic, "--duration", "30"]
    _log(f"Starting trading video: {topic[:60]}...")
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300, cwd=str(PROJECT_ROOT)
        )
        elapsed = round(time.time() - start, 1)
        success = proc.returncode == 0
        _log(f"Trading video done in {elapsed}s | success={success}")
        return {"type": "trading", "success": success, "elapsed_s": elapsed,
                "output": proc.stdout[-500:]}
    except subprocess.TimeoutExpired:
        _log("Trading video TIMEOUT after 300s")
        return {"type": "trading", "success": False, "elapsed_s": 300, "error": "timeout"}
    except Exception as e:
        _log(f"Trading video EXCEPTION: {e}")
        return {"type": "trading", "success": False, "error": str(e)}


def log_result(result: dict):
    """Append result to daily video log."""
    log_file = LOG_DIR / f"video_log_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
    entry = {**result, "timestamp": datetime.now(timezone.utc).isoformat()}
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _already_ran_today(hour: int, minute: int, video_type: str) -> bool:
    """Check daily log to avoid re-running a slot after scheduler restart."""
    log_file = LOG_DIR / f"video_log_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
    if not log_file.exists():
        return False
    try:
        for line in log_file.read_text().splitlines():
            entry = json.loads(line)
            ts = datetime.fromisoformat(entry.get("timestamp", "2000-01-01T00:00:00+00:00"))
            if ts.hour == hour and entry.get("type") == video_type and entry.get("success"):
                return True
    except Exception:
        pass
    return False


def main():
    PID_FILE.write_text(str(os.getpid()))
    _log(f"Video Scheduler started (PID {os.getpid()})")
    _log(f"Schedule: {len(SCHEDULE_HOURS)} videos/day at {SCHEDULE_HOURS} UTC | mode={get_video_mode()}")

    while _running:
        now  = datetime.now(timezone.utc)
        h, m = now.hour, now.minute
        mode = get_video_mode()

        if m == 0 and h in SCHEDULE_HOURS:
            if _already_ran_today(h, 0, mode):
                time.sleep(30)
                continue
            _log(f"Slot triggered: {h:02d}:00 UTC → mode={mode}")
            if mode == "trading":
                result = produce_trading(
                    signal=None,
                    topic=_pick_daily_topic(),
                    platform="tiktok"
                )
            else:
                # christian mode: FaithNexus biblical video
                result = produce_faithnexus()
            log_result(result)

        time.sleep(30)  # check every 30s

    try:
        PID_FILE.unlink()
    except Exception:
        pass
    _log("Video Scheduler stopped.")


if __name__ == "__main__":
    main()
