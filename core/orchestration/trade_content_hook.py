#!/usr/bin/env python3
"""
Trade Content Hook — v1.0
=========================
Watches ea_live_trades.jsonl and binance_live_trades.jsonl for EXIT events.
On each EXIT: generates a trading video, uploads to GDrive, queues to Postiz.

Usage:
    python3 core/orchestration/trade_content_hook.py --daemon     # background watcher
    python3 core/orchestration/trade_content_hook.py --test       # fire a fake EXIT
    python3 core/orchestration/trade_content_hook.py --once       # single poll then exit
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_FILE     = PROJECT_ROOT / "data" / "logs" / "trade_content_hook.log"
STATE_FILE   = PROJECT_ROOT / "data" / "feeds" / ".trade_content_hook_state.json"

EA_FEED      = PROJECT_ROOT / "data" / "feeds" / "ea_live_trades.jsonl"
BINANCE_FEED = PROJECT_ROOT / "data" / "feeds" / "binance_live_trades.jsonl"

PRODUCE_SCRIPT = PROJECT_ROOT / "scripts" / "produce_video.py"
GDRIVE_DEST    = "gdrive:HumanAI/videos/trading/"

POLL_INTERVAL  = 30   # seconds between feed polls

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("trade_content_hook")


# ── State: track read position per feed so we don't replay old events ─────────
def _load_state() -> dict:
    """Load byte-offset state for each feed file."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_state(state: dict):
    """Persist byte-offset state."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        log.warning(f"Could not save state: {e}")


# ── Feed polling ──────────────────────────────────────────────────────────────
def poll_feed(feed_path: Path, state: dict) -> list[dict]:
    """
    Read new lines appended to feed_path since last poll.
    Returns list of parsed trade dicts where data.type == 'EXIT'.
    """
    if not feed_path.exists():
        return []

    key = str(feed_path)
    last_pos = state.get(key, 0)
    exits = []

    try:
        size = feed_path.stat().st_size
        if size < last_pos:
            # File was rotated/truncated — reset to beginning
            log.info(f"Feed {feed_path.name} appears rotated, resetting offset.")
            last_pos = 0

        if size == last_pos:
            return []

        with open(feed_path, "rb") as f:
            f.seek(last_pos)
            new_bytes = f.read()
            state[key] = f.tell()

        for raw_line in new_bytes.decode("utf-8", errors="replace").splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                envelope = json.loads(raw_line)
                data = envelope.get("data", {})
                if data.get("type") == "EXIT":
                    exits.append({"source": envelope.get("source", "?"), **data})
            except json.JSONDecodeError:
                log.warning(f"Bad JSON line in {feed_path.name}: {raw_line[:80]}")

    except Exception as e:
        log.error(f"Error polling {feed_path.name}: {e}")

    return exits


# ── Trade data → video args ───────────────────────────────────────────────────
def _build_topic(trade: dict) -> str:
    """Build a human-readable topic string from trade fields."""
    symbol    = trade.get("symbol", "UNKNOWN")
    direction = trade.get("direction") or trade.get("side", "?")
    pnl       = trade.get("pnl", 0.0)
    entry     = trade.get("entry_price") or trade.get("entry", 0.0)
    exit_p    = trade.get("exit_price") or trade.get("exit", 0.0)
    reason    = trade.get("reason", "exit")
    source    = trade.get("source", "")

    pnl_str  = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
    engine   = "EA" if "EA" in source.upper() else "Binance"

    return (
        f"{symbol} {direction} trade closed {pnl_str} — "
        f"entry {entry} exit {exit_p} [{reason}] via {engine} AI signal"
    )


def _detect_platform(trade: dict) -> str:
    """Choose platform based on symbol type."""
    symbol = trade.get("symbol", "")
    if any(x in symbol.upper() for x in ("USDT", "BTC", "ETH", "BNB", "SOL", "XRP")):
        return "tiktok"
    return "youtube_shorts"


# ── Video generation ──────────────────────────────────────────────────────────
def generate_video(trade: dict) -> str | None:
    """
    Call produce_video.py via subprocess. Returns the output video path on
    success, or None on failure.
    """
    topic    = _build_topic(trade)
    platform = _detect_platform(trade)
    pnl      = trade.get("pnl", 0.0)
    signal   = "BUY" if (trade.get("direction") or trade.get("side", "BUY")) == "BUY" else "SELL"

    cmd = [
        sys.executable,
        str(PRODUCE_SCRIPT),
        "--topic", topic,
        "--platform", platform,
        "--signal", signal,
        "--duration", "45",
    ]

    log.info(f"Generating video for trade: {trade.get('symbol')} PnL={pnl:+.2f}")
    log.info(f"  cmd: {' '.join(cmd[:6])} ...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode != 0:
            log.error(f"Video generation failed (exit {result.returncode}):\n{result.stderr[-500:]}")
            return None

        # Extract output path from stdout — produce_video.py prints "Output: /path/to/file.mp4"
        output_path = None
        for line in result.stdout.splitlines():
            if line.strip().startswith("Output:"):
                output_path = line.split("Output:", 1)[1].strip()
                break

        if output_path and Path(output_path).exists():
            log.info(f"Video generated: {output_path}")
            return output_path

        # Fallback: scan media_output for the most recently modified mp4
        media_dir = PROJECT_ROOT / "data" / "media_output"
        mp4s = sorted(media_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if mp4s:
            candidate = str(mp4s[0])
            log.info(f"Video output path inferred from newest mp4: {candidate}")
            return candidate

        log.warning("Video generation succeeded but output path not found.")
        return None

    except subprocess.TimeoutExpired:
        log.error("Video generation timed out (300s).")
        return None
    except FileNotFoundError:
        log.error(f"produce_video.py not found at {PRODUCE_SCRIPT}")
        return None
    except Exception as e:
        log.error(f"Unexpected error during video generation: {e}")
        return None


# ── GDrive upload ─────────────────────────────────────────────────────────────
def upload_to_gdrive(video_path: str) -> bool:
    """
    rclone copy the video to GDrive, then delete the local file.
    Returns True on success.
    """
    log.info(f"Uploading to GDrive: {video_path} → {GDRIVE_DEST}")
    try:
        result = subprocess.run(
            ["rclone", "copy", video_path, GDRIVE_DEST, "--no-traverse"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            log.error(f"rclone failed (exit {result.returncode}): {result.stderr[:300]}")
            return False

        log.info("GDrive upload complete.")

        # Delete local copy after successful upload
        try:
            Path(video_path).unlink()
            log.info(f"Deleted local video: {video_path}")
        except Exception as e:
            log.warning(f"Could not delete local video: {e}")

        return True

    except FileNotFoundError:
        log.warning("rclone not installed — skipping GDrive upload.")
        return False
    except subprocess.TimeoutExpired:
        log.error("rclone timed out (300s).")
        return False
    except Exception as e:
        log.error(f"Unexpected error during GDrive upload: {e}")
        return False


# ── Postiz queuing ────────────────────────────────────────────────────────────
def queue_to_postiz(trade: dict, video_path: str | None) -> bool:
    """
    Upload video to Postiz and create a scheduled post.
    Silently skips if Postiz is unavailable — never crashes the pipeline.
    """
    try:
        # Import here so a missing/broken postiz_connector doesn't prevent startup
        sys.path.insert(0, str(PROJECT_ROOT))
        from agents.social.postiz_connector import PostizConnector
    except ImportError as e:
        log.warning(f"PostizConnector not importable: {e} — skipping Postiz.")
        return False

    try:
        connector = PostizConnector()
        if not connector.health_check():
            log.warning(f"Postiz at {connector.api_url} not reachable — skipping.")
            return False
    except Exception as e:
        log.warning(f"Postiz health check failed: {e} — skipping.")
        return False

    # Build caption
    symbol    = trade.get("symbol", "UNKNOWN")
    direction = trade.get("direction") or trade.get("side", "?")
    pnl       = trade.get("pnl", 0.0)
    reason    = trade.get("reason", "exit")
    pnl_emoji = "✅" if pnl >= 0 else "❌"
    pnl_str   = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"

    caption = (
        f"{pnl_emoji} {symbol} {direction} trade closed {pnl_str} [{reason}]\n"
        f"AI swarm caught it. Follow for daily signals.\n"
        f"#AI #Trading #{symbol} #AlgoTrading #ITNEXUS"
    )

    try:
        media_id = None
        if video_path and Path(video_path).exists():
            upload_result = connector.upload_media(video_path, file_type="video")
            media_id = upload_result.get("id")
            log.info(f"Video uploaded to Postiz, media_id={media_id}")

        media_ids = [media_id] if media_id else None
        result = connector.publish_content(
            content=caption,
            media_ids=media_ids,
        )
        post_id = result.get("id", "?")
        log.info(f"Queued to Postiz: post_id={post_id}")
        return True

    except Exception as e:
        log.error(f"Postiz publish failed: {e}")
        return False


# ── Single trade handler ──────────────────────────────────────────────────────
def handle_exit(trade: dict):
    """Full pipeline for one EXIT event: video → gdrive → postiz."""
    symbol = trade.get("symbol", "?")
    pnl    = trade.get("pnl", 0.0)
    log.info(f"=== EXIT event: {symbol} PnL={pnl:+.2f} ===")

    video_path = generate_video(trade)

    if video_path:
        upload_to_gdrive(video_path)
        # After upload, video_path may be deleted. Pass it to Postiz before deletion.
        # Note: if file was deleted in upload_to_gdrive, Postiz will skip media upload gracefully.
        queue_to_postiz(trade, video_path)
    else:
        # Still try Postiz with caption-only (no video)
        log.warning("No video generated — queuing caption-only to Postiz.")
        queue_to_postiz(trade, None)

    log.info(f"=== Finished processing EXIT: {symbol} ===")


# ── Fake trade for --test ─────────────────────────────────────────────────────
def _fake_ea_exit() -> dict:
    return {
        "source": "EAv11_TEST",
        "type": "EXIT",
        "symbol": "XAUUSD",
        "direction": "BUY",
        "lot": 0.01,
        "entry_price": 3280.50,
        "exit_price": 3284.20,
        "pnl": 3.70,
        "reason": "TP1",
        "elapsed": 240,
        "timestamp": datetime.now().isoformat(),
    }


def _fake_binance_exit() -> dict:
    return {
        "source": "BinanceV2_TEST",
        "type": "EXIT",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "direction": "BUY",
        "entry_price": 67200.00,
        "exit_price": 67402.00,
        "qty": 0.001,
        "pnl": 0.202,
        "pnl_pct": 0.30,
        "leverage": 25,
        "reason": "TP1",
        "elapsed": 45,
        "timestamp": datetime.now().isoformat(),
    }


# ── Main polling loop ─────────────────────────────────────────────────────────
def run_daemon():
    """Poll both feeds every POLL_INTERVAL seconds, process all new EXITs."""
    log.info(f"Trade content hook starting. Poll interval: {POLL_INTERVAL}s")
    log.info(f"  EA feed:      {EA_FEED}")
    log.info(f"  Binance feed: {BINANCE_FEED}")

    state = _load_state()

    # On first run, fast-forward to EOF so we don't replay historical trades
    for feed in (EA_FEED, BINANCE_FEED):
        key = str(feed)
        if key not in state and feed.exists():
            state[key] = feed.stat().st_size
            log.info(f"Fast-forwarding {feed.name} to EOF ({state[key]} bytes) — skipping history.")
    _save_state(state)

    while True:
        try:
            for feed in (EA_FEED, BINANCE_FEED):
                exits = poll_feed(feed, state)
                for trade in exits:
                    try:
                        handle_exit(trade)
                    except Exception as e:
                        log.error(f"Unhandled error in handle_exit: {e}", exc_info=True)
            _save_state(state)
        except Exception as e:
            log.error(f"Error in poll loop: {e}", exc_info=True)

        time.sleep(POLL_INTERVAL)


def run_once():
    """Single poll pass — useful for cron or systemd timer mode."""
    log.info("Trade content hook — single poll pass.")
    state = _load_state()
    for feed in (EA_FEED, BINANCE_FEED):
        exits = poll_feed(feed, state)
        for trade in exits:
            try:
                handle_exit(trade)
            except Exception as e:
                log.error(f"Unhandled error in handle_exit: {e}", exc_info=True)
    _save_state(state)
    log.info("Single poll pass complete.")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trade content hook — video on EXIT")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--daemon",
        action="store_true",
        help="Run as continuous background watcher (poll every 30s)",
    )
    group.add_argument(
        "--test",
        action="store_true",
        help="Fire a fake EA EXIT and a fake Binance EXIT to test the full pipeline",
    )
    group.add_argument(
        "--once",
        action="store_true",
        help="Run a single poll pass then exit",
    )
    args = parser.parse_args()

    if args.test:
        log.info("=== TEST MODE: firing fake EA EXIT ===")
        handle_exit(_fake_ea_exit())
        log.info("=== TEST MODE: firing fake Binance EXIT ===")
        handle_exit(_fake_binance_exit())
        log.info("=== TEST MODE complete ===")
    elif args.once:
        run_once()
    else:
        # Default: daemon
        run_daemon()
