#!/usr/bin/env python3
"""
Rename reel directories and their MP4 files to meaningful, slug-based names.

Usage:
    python scripts/rename_videos.py --dry-run    # show what would happen
    python scripts/rename_videos.py --apply      # actually rename

Naming format:
    {platform}_{date}_{topic_slug}.mp4
    e.g.  tiktok_20260515_gold_bullish_breakout.mp4

Directory renames follow the same pattern:
    reel_tiktok_20260515_gold_bullish_breakout/

A log entry is appended to data/media_output/rename_log.jsonl for every change.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEDIA_DIR    = PROJECT_ROOT / "data" / "media_output"
RENAME_LOG   = MEDIA_DIR / "rename_log.jsonl"

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def _to_slug(text: str, max_len: int = 40) -> str:
    """Convert free-form text to a lowercase alphanumeric+underscore slug."""
    # Strip emoji / non-ASCII
    text = text.encode("ascii", "ignore").decode()
    # Lowercase
    text = text.lower()
    # Replace non-alphanum chars with spaces
    text = re.sub(r"[^a-z0-9]+", " ", text)
    # Collapse spaces, strip
    text = text.strip()
    words = text.split()
    slug = "_".join(words)[:max_len]
    # Remove trailing underscores after truncation
    slug = slug.rstrip("_")
    return slug or "unknown"


def _extract_platform_date(dir_name: str) -> tuple[str, str]:
    """
    Parse reel_{platform}_{YYYYMMDD}_{HHMMSS} directory names.
    Returns (platform, date_str).  date_str is YYYYMMDD.
    """
    # Pattern: reel_<platform>_<YYYYMMDD>_<HHMMSS>
    m = re.match(r"reel_(.+?)_(\d{8})_\d{6}$", dir_name)
    if m:
        return m.group(1), m.group(2)
    # Fallback: try to pull any 8-digit date
    dm = re.search(r"(\d{8})", dir_name)
    date_str = dm.group(1) if dm else datetime.now().strftime("%Y%m%d")
    # Platform is everything between first _ and the date block
    parts = dir_name.split("_")
    if len(parts) >= 3:
        # reel_<platform...>_YYYYMMDD_HHMMSS
        # platform may be multi-part: youtube_shorts
        date_idx = next(
            (i for i, p in enumerate(parts) if re.fullmatch(r"\d{8}", p)), -1
        )
        platform = "_".join(parts[1:date_idx]) if date_idx > 1 else parts[1]
    else:
        platform = "unknown"
    return platform, date_str


def _read_topic_from_metadata(reel_dir: Path) -> str | None:
    """Read topic from reel_metadata.json if it exists and looks clean."""
    meta_path = reel_dir / "reel_metadata.json"
    if not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text())
        topic = meta.get("topic", "")
        if not topic:
            return None
        # Reject topics that are clearly internal task descriptions (paths / filenames)
        if re.search(r"docs/pow|\.md\b|extract one concrete", topic):
            return None
        # Truncate very long topics
        return topic[:200]
    except Exception:
        return None


_SCRIPT_GARBAGE_RE = re.compile(
    r"docs/pow|\.md\b|extract one concrete|write the improvement|action_\d{8}"
)

def _read_topic_from_script(reel_dir: Path) -> str | None:
    """Fall back: grab first 5 meaningful words from caption.txt or any .txt file."""
    for candidate in ["caption.txt", "script.txt", "voiceover.txt"]:
        p = reel_dir / candidate
        if p.exists():
            text = p.read_text(errors="replace").strip()
            if _SCRIPT_GARBAGE_RE.search(text):
                continue  # internal task bleed — skip
            # Strip emoji, hashtags, leading punctuation
            text = re.sub(r"[^\w\s.,!?-]", " ", text)
            words = text.split()[:5]
            if words:
                return " ".join(words)
    # Any .txt file
    for p in reel_dir.glob("*.txt"):
        text = p.read_text(errors="replace").strip()
        if _SCRIPT_GARBAGE_RE.search(text):
            continue
        text = re.sub(r"[^\w\s.,!?-]", " ", text)
        words = text.split()[:5]
        if words:
            return " ".join(words)
    return None


def _find_mp4(reel_dir: Path) -> Path | None:
    """Return the first (usually only) MP4 in the directory, or None."""
    mp4s = list(reel_dir.glob("*.mp4"))
    if not mp4s:
        return None
    # Prefer the largest file (skip tiny thumbnail/background clips)
    return max(mp4s, key=lambda p: p.stat().st_size)


# ── core logic ────────────────────────────────────────────────────────────────

def compute_rename(reel_dir: Path) -> dict | None:
    """
    Work out the desired new name for a reel directory and its MP4.
    Returns a dict or None if the directory is already well-named / has no MP4.
    """
    dir_name = reel_dir.name

    # Skip dirs that have already been renamed (no longer match timestamp pattern)
    if not re.search(r"\d{8}_\d{6}", dir_name):
        return None

    platform, date_str = _extract_platform_date(dir_name)

    # Determine topic slug
    topic_raw = _read_topic_from_metadata(reel_dir) or _read_topic_from_script(reel_dir)
    if topic_raw:
        slug = _to_slug(topic_raw)
    else:
        slug = _to_slug(platform)  # last resort: just platform

    new_dir_name  = f"reel_{platform}_{date_str}_{slug}"
    new_mp4_name  = f"{platform}_{date_str}_{slug}.mp4"

    mp4 = _find_mp4(reel_dir)
    if mp4 is None:
        # Empty reel dir — note it but skip renaming
        log.debug(f"[SKIP-NOMP4] {dir_name}")
        return None

    old_mp4_name = mp4.name

    # Nothing to change?
    if dir_name == new_dir_name and old_mp4_name == new_mp4_name:
        return None

    return {
        "old_dir":     str(reel_dir),
        "new_dir":     str(reel_dir.parent / new_dir_name),
        "old_mp4":     str(mp4),
        "new_mp4_rel": new_mp4_name,         # relative to new_dir
        "platform":    platform,
        "date":        date_str,
        "slug":        slug,
        "topic_raw":   topic_raw or "",
        "source":      "metadata" if _read_topic_from_metadata(reel_dir) else "script",
    }


def _write_log(entry: dict):
    """Append one JSON line to rename_log.jsonl."""
    try:
        RENAME_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(RENAME_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        log.warning(f"[WARN] rename_log write failed: {e}")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true",
                       help="Show planned renames without touching the filesystem")
    group.add_argument("--apply",   action="store_true",
                       help="Apply renames to disk and write rename_log.jsonl")
    p.add_argument("--dir", default=str(MEDIA_DIR),
                   help=f"Media output directory (default: {MEDIA_DIR})")
    args = p.parse_args()

    media_dir = Path(args.dir)
    if not media_dir.is_dir():
        log.error(f"Directory not found: {media_dir}")
        sys.exit(1)

    # Collect all reel_* subdirectories
    reel_dirs = sorted(d for d in media_dir.iterdir()
                       if d.is_dir() and d.name.startswith("reel_"))

    plans: list[dict] = []
    skipped = 0
    for reel_dir in reel_dirs:
        plan = compute_rename(reel_dir)
        if plan:
            plans.append(plan)
        else:
            skipped += 1

    log.info(f"\nFound {len(reel_dirs)} reel directories: "
             f"{len(plans)} to rename, {skipped} already clean / empty.\n")

    if not plans:
        log.info("Nothing to rename.")
        return

    for plan in plans:
        old_dir_name = Path(plan["old_dir"]).name
        new_dir_name = Path(plan["new_dir"]).name
        old_mp4_name = Path(plan["old_mp4"]).name
        new_mp4_name = plan["new_mp4_rel"]
        src = f"[{plan['source']}]"

        log.info(f"  DIR  {old_dir_name}")
        log.info(f"    -> {new_dir_name}  {src}")
        if old_mp4_name != new_mp4_name:
            log.info(f"  MP4  {old_mp4_name} -> {new_mp4_name}")
        log.info("")

    if args.dry_run:
        log.info(f"[DRY-RUN] {len(plans)} rename(s) would be applied. "
                 f"Re-run with --apply to execute.")
        return

    # ── actually apply ───────────────────────────────────────────
    applied = 0
    errors  = 0
    ts = datetime.now(timezone.utc).isoformat()

    for plan in plans:
        old_dir  = Path(plan["old_dir"])
        new_dir  = Path(plan["new_dir"])
        old_mp4  = Path(plan["old_mp4"])
        new_mp4  = new_dir / plan["new_mp4_rel"]

        log_entry = {**plan, "timestamp": ts, "status": "pending"}
        try:
            # Step 1: rename MP4 inside the directory (before moving the dir)
            if old_mp4.name != new_mp4.name:
                new_mp4_in_old = old_dir / plan["new_mp4_rel"]
                old_mp4.rename(new_mp4_in_old)
                log.info(f"[RENAMED-MP4] {old_mp4.name} -> {new_mp4_in_old.name}")

            # Step 2: update reel_metadata.json output path (best-effort)
            meta_path = old_dir / "reel_metadata.json"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                    meta["output"] = str(new_mp4)
                    meta_path.write_text(json.dumps(meta, indent=2))
                except Exception as e_meta:
                    log.warning(f"[WARN] metadata update failed: {e_meta}")

            # Step 3: rename the directory
            if old_dir != new_dir:
                # Guard against collision
                if new_dir.exists():
                    suffix = datetime.now().strftime("%f")
                    new_dir = new_dir.parent / f"{new_dir.name}_{suffix}"
                    plan["new_dir"] = str(new_dir)
                    log.warning(f"[COLLISION] target exists, using suffix: {new_dir.name}")
                old_dir.rename(new_dir)
                log.info(f"[RENAMED-DIR] {old_dir.name} -> {new_dir.name}")

            log_entry["status"] = "ok"
            applied += 1
        except Exception as e:
            log.error(f"[ERROR] {old_dir.name}: {e}")
            log_entry["status"] = "error"
            log_entry["error"]  = str(e)
            errors += 1

        _write_log(log_entry)

    log.info(f"\nDone: {applied} renamed, {errors} errors.")
    log.info(f"Log written to: {RENAME_LOG}")


if __name__ == "__main__":
    main()
