#!/usr/bin/env python3
"""
Video Metrics — Throughput tracker for the video generation pipeline.

Scans data/media_output/ for all reel_* folders, parses timestamps from folder
names, calculates per-day counts, platform breakdown, avg generation time, and
current rate. Writes:
  - data/media_output/metrics.json     (consumed by dashboard)
  - data/media_output/capacity_estimate.json

Usage:
  python3 scripts/video_metrics.py          # compute and write JSON
  python3 scripts/video_metrics.py --print  # also pretty-print to stdout
"""

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEDIA_DIR    = PROJECT_ROOT / "data" / "media_output"
GEN_LOG      = MEDIA_DIR / "generation_log.jsonl"
METRICS_OUT  = MEDIA_DIR / "metrics.json"
CAPACITY_OUT = MEDIA_DIR / "capacity_estimate.json"


def _parse_folders() -> list[dict]:
    """Return list of dicts for every reel_* folder that matches the timestamp pattern."""
    pattern = re.compile(r"reel_(tiktok|youtube_shorts|instagram_reel)_(\d{8}_\d{6})")
    entries = []
    for folder in MEDIA_DIR.iterdir():
        if not folder.is_dir():
            continue
        m = pattern.match(folder.name)
        if not m:
            continue
        platform = m.group(1)
        dt = datetime.strptime(m.group(2), "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
        mp4s = list(folder.glob("*.mp4"))
        entries.append({
            "folder":   folder.name,
            "platform": platform,
            "dt":       dt,
            "has_mp4":  len(mp4s) > 0,
            "mp4_path": str(mp4s[0]) if mp4s else None,
            "file_size_kb": round(mp4s[0].stat().st_size / 1024, 1) if mp4s else 0,
            "mp4_mtime": datetime.fromtimestamp(mp4s[0].stat().st_mtime, tz=timezone.utc) if mp4s else None,
        })
    entries.sort(key=lambda x: x["dt"])
    return entries


def _compute_generation_times(entries: list[dict]) -> list[float]:
    """
    Approximate generation time per video:
      - First priority: generation_log.jsonl (has real start/end times)
      - Fallback: (mp4_mtime - folder_dt) for entries where result is plausible
    """
    # Try generation log first
    gen_times: list[float] = []
    if GEN_LOG.exists():
        for line in GEN_LOG.read_text().splitlines():
            try:
                rec = json.loads(line)
                if rec.get("duration_seconds", 0) > 0:
                    gen_times.append(float(rec["duration_seconds"]))
            except Exception:
                pass

    if gen_times:
        return gen_times

    # Fallback: mtime – folder_dt, keep only plausible values (5s – 600s)
    fallback = []
    for e in entries:
        if e["has_mp4"] and e["mp4_mtime"]:
            delta = (e["mp4_mtime"] - e["dt"]).total_seconds()
            if 5 < delta < 600:
                fallback.append(delta)
    return fallback


def compute_metrics(entries: list[dict]) -> dict:
    now_utc = datetime.now(timezone.utc)
    today   = now_utc.strftime("%Y-%m-%d")

    # Per-day counts
    day_counts:    defaultdict[str, int]        = defaultdict(int)
    day_platforms: defaultdict[str, Counter]    = defaultdict(Counter)
    day_successes: defaultdict[str, int]        = defaultdict(int)
    for e in entries:
        day = e["dt"].strftime("%Y-%m-%d")
        day_counts[day]            += 1
        day_platforms[day][e["platform"]] += 1
        if e["has_mp4"]:
            day_successes[day]     += 1

    total_folders  = len(entries)
    total_with_mp4 = sum(1 for e in entries if e["has_mp4"])
    total_empty    = total_folders - total_with_mp4
    platform_total = Counter(e["platform"] for e in entries)

    # Success rate
    success_rate = round(total_with_mp4 / total_folders * 100, 1) if total_folders else 0.0

    # Today
    today_entries  = [e for e in entries if e["dt"].strftime("%Y-%m-%d") == today]
    today_count    = len(today_entries)
    today_success  = sum(1 for e in today_entries if e["has_mp4"])

    # Current rate (videos per hour today)
    current_rate_per_hour = 0.0
    if len(today_entries) >= 2:
        span_h = (today_entries[-1]["dt"] - today_entries[0]["dt"]).total_seconds() / 3600
        if span_h > 0:
            current_rate_per_hour = round(today_count / span_h, 2)

    # Average generation time
    gen_times = _compute_generation_times(entries)
    avg_gen_s = round(sum(gen_times) / len(gen_times), 1) if gen_times else None

    # Per-day history (last 7 days, most-recent first)
    daily_history = []
    for day in sorted(day_counts.keys(), reverse=True)[:7]:
        daily_history.append({
            "date":      day,
            "total":     day_counts[day],
            "successes": day_successes[day],
            "platforms": dict(day_platforms[day]),
        })

    metrics = {
        "generated_at":           now_utc.isoformat(),
        "total_folders":          total_folders,
        "total_with_mp4":         total_with_mp4,
        "total_empty_folders":    total_empty,
        "success_rate_pct":       success_rate,
        "platform_breakdown":     dict(platform_total),
        "today": {
            "date":    today,
            "total":   today_count,
            "success": today_success,
            "rate_per_hour": current_rate_per_hour,
        },
        "avg_generation_seconds": avg_gen_s,
        "daily_history":          daily_history,
        "latest_video": {
            "folder":       entries[-1]["folder"]   if entries else None,
            "platform":     entries[-1]["platform"] if entries else None,
            "dt":           entries[-1]["dt"].isoformat() if entries else None,
            "has_mp4":      entries[-1]["has_mp4"]  if entries else None,
            "file_size_kb": entries[-1]["file_size_kb"] if entries else None,
        },
    }
    return metrics


def compute_capacity(metrics: dict) -> dict:
    avg_s   = metrics.get("avg_generation_seconds")
    today   = metrics.get("today", {})
    current = today.get("rate_per_hour", 0)

    if avg_s and avg_s > 0:
        max_per_day = int(86400 / avg_s)
    else:
        max_per_day = None  # unknown — no timing data yet

    return {
        "generated_at":           metrics["generated_at"],
        "avg_generation_seconds": avg_s,
        "max_videos_per_day":     max_per_day,
        "current_rate_per_hour":  current,
        "current_rate_per_day":   round(current * 24, 1) if current else None,
        "note": (
            "avg_generation_seconds derived from generation_log.jsonl when present, "
            "otherwise estimated from (mp4_mtime - folder_creation_timestamp)."
        ),
    }


def main():
    print_output = "--print" in sys.argv

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    entries  = _parse_folders()
    metrics  = compute_metrics(entries)
    capacity = compute_capacity(metrics)

    METRICS_OUT.write_text(json.dumps(metrics, indent=2))
    CAPACITY_OUT.write_text(json.dumps(capacity, indent=2))

    if print_output:
        print("=== Video Pipeline Metrics ===")
        print(f"Total reel folders : {metrics['total_folders']}")
        print(f"With MP4 (success) : {metrics['total_with_mp4']}  ({metrics['success_rate_pct']}%)")
        print(f"Empty (failed)     : {metrics['total_empty_folders']}")
        print(f"Platform breakdown : {metrics['platform_breakdown']}")
        print(f"\nToday ({metrics['today']['date']}):")
        print(f"  Total    : {metrics['today']['total']}")
        print(f"  Success  : {metrics['today']['success']}")
        print(f"  Rate     : {metrics['today']['rate_per_hour']} videos/hour")
        print(f"\nAvg generation time: {metrics['avg_generation_seconds']}s")
        print(f"\n=== Capacity Estimate ===")
        print(f"Avg gen time       : {capacity['avg_generation_seconds']}s")
        print(f"Max videos/day     : {capacity['max_videos_per_day']}")
        print(f"Current rate/day   : {capacity['current_rate_per_day']}")
        print(f"\nWrote: {METRICS_OUT}")
        print(f"Wrote: {CAPACITY_OUT}")
    else:
        print(f"Metrics: {METRICS_OUT}")
        print(f"Capacity: {CAPACITY_OUT}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
