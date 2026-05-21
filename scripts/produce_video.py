#!/usr/bin/env python3
"""Produce a trading video for TikTok/YouTube Shorts."""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.social.media_generator import generate_short, generate_trading_content

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GEN_LOG      = PROJECT_ROOT / "data" / "media_output" / "generation_log.jsonl"


def _write_gen_log(entry: dict):
    """Append one JSON line to the generation log (atomic-safe, never throws)."""
    try:
        GEN_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(GEN_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[WARN] generation_log write failed: {e}", file=sys.stderr)


def _gdrive_upload(output_path: str, platform: str):
    """
    Upload the generated video to GDrive after production.
    Non-fatal — failure is logged but does not stop the pipeline.
    """
    import subprocess
    platform_map = {
        "tiktok":           "trading/tiktok",
        "youtube_shorts":   "trading/youtube",
        "instagram_reel":   "trading/tiktok",
    }
    dest_folder = "gdrive:HumanAI/videos/trading/all/"  # single folder for all trading videos
    try:
        r = subprocess.run(
            ["rclone", "copy", output_path, dest_folder, "--no-traverse"],
            capture_output=True, text=True, timeout=180,
        )
        if r.returncode == 0:
            print(f"[GDrive] Uploaded to {dest_folder}")
            try:
                import os as _os
                _os.remove(output_path)
                print(f"[GDrive] Local file deleted: {output_path}")
            except OSError as e:
                print(f"[GDrive] Warning: could not delete local file: {e}", file=sys.stderr)
        else:
            print(f"[GDrive] Upload failed (code {r.returncode}): {r.stderr[:200]}", file=sys.stderr)
    except FileNotFoundError:
        print("[GDrive] rclone not installed — skipping upload", file=sys.stderr)
    except subprocess.TimeoutExpired:
        print("[GDrive] rclone timed out after 180s — skipping upload", file=sys.stderr)
    except Exception as e:
        print(f"[GDrive] Upload exception: {e}", file=sys.stderr)


def produce_one(topic: str, platform: str, duration: int, signal: str | None) -> dict:
    """Run one full generation cycle and return the result dict."""
    start_ts = datetime.now(timezone.utc).isoformat()
    t0 = time.monotonic()

    if signal:
        result = generate_trading_content("XAUUSD", signal)
    else:
        result = generate_short(topic, platform, duration)

    elapsed = round(time.monotonic() - t0, 2)
    end_ts  = datetime.now(timezone.utc).isoformat()

    # Write generation log entry
    log_entry = {
        "start_time":        start_ts,
        "end_time":          end_ts,
        "duration_seconds":  elapsed,
        "platform":          platform,
        "topic":             topic,
        "signal":            signal,
        "success":           result.get("success", False),
        "filename":          result.get("output"),
        "file_size_kb":      result.get("file_size_kb", 0),
    }
    _write_gen_log(log_entry)

    # Upload to GDrive if generation succeeded
    if result.get("success") and result.get("output"):
        _gdrive_upload(result["output"], platform)

    return result


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--topic",    default="Gold trading signal XAUUSD")
    p.add_argument("--platform", default="tiktok",
                   choices=["tiktok", "youtube_shorts", "instagram_reel"])
    p.add_argument("--duration", type=int, default=30)
    p.add_argument("--signal",   choices=["BUY", "SELL", "HOLD"])
    p.add_argument("--batch",    type=int, default=1,
                   help="Generate N videos in sequence (default 1)")
    args = p.parse_args()

    for i in range(args.batch):
        if args.batch > 1:
            print(f"\n[batch {i+1}/{args.batch}]")
        result = produce_one(args.topic, args.platform, args.duration, args.signal)
        print(f"\n{'SUCCESS' if result['success'] else 'FAILED'}")
        if result["success"]:
            print(f"Output: {result['output']}")
            print(f"Size: {result['file_size_kb']}KB")
            print(f"Caption: {result['caption']}")
