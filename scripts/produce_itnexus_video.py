#!/usr/bin/env python3
"""
ITNEXUS YouTube Channel — Gold Signal Trading Video Producer
Produces a 60-second portrait (1080x1920) video with:
  - edge-tts voiceover (en-US-GuyNeural, boundary='WordBoundary')
  - Word-level subtitle timing grouped into 4-word chunks
  - Pexels background video (portrait 1080x1920) or cached fallback
  - Dark overlay for text readability
  - ITNEXUS branding and gold signal label
  - Hardcoded (burned-in) subtitles via ffmpeg drawtext
  - rclone upload to gdrive:/Video Uploads/
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.parse
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT    = Path("/home/yahwehatwork/human-ai")
ENV_FILE     = REPO_ROOT / ".env"
OUTPUT_DIR   = REPO_ROOT / "data/media_output/itnexus_final"
OUTPUT_MP4   = OUTPUT_DIR / "itnexus_gold_signal.mp4"
META_JSON    = OUTPUT_DIR / "metadata.json"
FALLBACK_VID = REPO_ROOT / "data/media_output/pexels_8480279.mp4"

TMP_DIR    = Path("/tmp/itnexus_build")
TMP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VO_MP3     = TMP_DIR / "itnexus_vo.mp3"
PEXELS_MP4 = TMP_DIR / "pexels_bg.mp4"
SCALED_MP4 = TMP_DIR / "pexels_scaled.mp4"

# ── Script text ───────────────────────────────────────────────────────────────
SCRIPT = (
    "Gold is EXPLODING right now. And most traders are missing it. "
    "Our AI system detected a XAUUSD buy signal at 4,670. "
    "That's a key support level going back 3 weeks. "
    "The signal scored 4 out of 5 on our confidence meter. "
    "Here's what makes this different: our swarm of AI agents monitors "
    "8 indicators simultaneously. EMA crossovers, RSI, Bollinger Bands, "
    "ATR volatility, session timing. Then combines them into one clean signal. "
    "We caught the move. Follow ITNEXUS for daily AI trading signals "
    "on Gold, Silver, and Crypto. "
    "Like. Follow. Turn on notifications."
)

VOICE = "en-US-GuyNeural"
RATE  = "+10%"
PITCH = "+0Hz"


def log(msg: str):
    print(f"[itnexus] {msg}", flush=True)


def load_env():
    """Parse .env into os.environ (no external deps required)."""
    if not ENV_FILE.exists():
        return
    for raw_line in ENV_FILE.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ─────────────────────────────────────────────────────────────────────────────
# 1. VOICEOVER  (edge-tts with boundary='WordBoundary')
# ─────────────────────────────────────────────────────────────────────────────
async def generate_voiceover() -> list[dict]:
    """
    Stream audio from edge-tts and collect per-word timings.
    Returns list of {'word', 'start', 'duration'} dicts.
    """
    import edge_tts
    log("Generating voiceover with edge-tts (WordBoundary) …")

    word_timings: list[dict] = []
    audio_bytes = bytearray()

    comm = edge_tts.Communicate(
        SCRIPT, VOICE,
        rate=RATE, pitch=PITCH,
        boundary="WordBoundary",
    )

    async for chunk in comm.stream():
        ctype = chunk["type"]
        if ctype == "audio":
            audio_bytes.extend(chunk["data"])
        elif ctype == "WordBoundary":
            word_timings.append({
                "word":     chunk["text"],
                "start":    chunk["offset"]   / 10_000_000,   # 100-ns ticks → s
                "duration": chunk["duration"] / 10_000_000,
            })

    if not audio_bytes:
        raise RuntimeError("edge-tts returned no audio data")

    VO_MP3.write_bytes(bytes(audio_bytes))
    log(f"  Saved {VO_MP3.stat().st_size // 1024} KB  |  {len(word_timings)} word timings")
    return word_timings


# ─────────────────────────────────────────────────────────────────────────────
# 2. GROUP WORD TIMINGS INTO SUBTITLE CHUNKS
# ─────────────────────────────────────────────────────────────────────────────
def group_words(word_timings: list[dict], chunk_size: int = 4) -> list[dict]:
    """Group consecutive words into display chunks."""
    chunks = []
    i = 0
    while i < len(word_timings):
        group = word_timings[i : i + chunk_size]
        text  = " ".join(w["word"] for w in group)
        start = group[0]["start"]
        end   = group[-1]["start"] + group[-1]["duration"]
        chunks.append({"text": text, "start": start, "end": end})
        i += chunk_size
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# 3. PEXELS VIDEO DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────
def download_pexels_video(api_key: str) -> bool:
    """Download a portrait Pexels video. Returns True on success."""
    queries = ["gold bars finance", "trading chart finance", "gold coins wealth"]
    for query in queries:
        try:
            url = (
                "https://api.pexels.com/videos/search?"
                + urllib.parse.urlencode({
                    "query": query,
                    "per_page": 10,
                    "orientation": "portrait",
                })
            )
            req = urllib.request.Request(url, headers={"Authorization": api_key})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())

            for v in data.get("videos", []):
                for vf in v.get("video_files", []):
                    w, h = vf.get("width", 0), vf.get("height", 0)
                    if w >= 720 and h > w:
                        log(f"  Downloading Pexels {w}x{h} portrait video …")
                        urllib.request.urlretrieve(vf["link"], PEXELS_MP4)
                        log(f"  Saved {PEXELS_MP4.stat().st_size // 1024} KB")
                        return True
        except Exception as exc:
            log(f"  Pexels '{query}' failed: {exc}")

    log("  Pexels download failed — will use cached fallback")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# 4. PREPARE BACKGROUND VIDEO (loop + scale/crop to 1080x1920)
# ─────────────────────────────────────────────────────────────────────────────
def get_video_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-select_streams", "v:0", str(path)],
        capture_output=True, text=True, check=True,
    )
    d = json.loads(r.stdout)
    return float(d["streams"][0].get("duration", 60))


def prepare_background(src: Path, target_dur: float) -> Path:
    log(f"Preparing background: {src.name} → 1080x1920 …")
    src_dur = get_video_duration(src)
    loops   = max(0, int(target_dur / src_dur) + 1)
    log(f"  src_dur={src_dur:.1f}s  loops={loops}")

    # Scale + crop to portrait 1080x1920 in one pass, looping via -stream_loop
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", str(loops),
        "-i", str(src),
        "-t", str(target_dur + 2),
        "-vf", (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920"
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        str(SCALED_MP4),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        log("ffmpeg scale stderr: " + r.stderr[-1000:])
        raise RuntimeError("Background scaling failed")
    log(f"  Background ready: {SCALED_MP4}")
    return SCALED_MP4


# ─────────────────────────────────────────────────────────────────────────────
# 5. BUILD FFMPEG DRAWTEXT FILTER CHAIN
# ─────────────────────────────────────────────────────────────────────────────
def find_font() -> str:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in candidates:
        if Path(fp).exists():
            return fp
    # fc-match fallback
    r = subprocess.run(
        ["fc-match", "--format=%{file}", "sans-serif:bold"],
        capture_output=True, text=True
    )
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    return candidates[0]   # best-guess, may fail


def esc(text: str) -> str:
    """Escape text for ffmpeg drawtext value."""
    # Order matters — backslash first
    text = text.replace("\\", "\\\\")
    text = text.replace("'",  "")         # drop apostrophes to avoid quoting nightmare
    text = text.replace(":",  r"\:")
    text = text.replace(",",  "\\,")
    text = text.replace("[",  "\\[")
    text = text.replace("]",  "\\]")
    return text


def build_filter(chunks: list[dict], total_dur: float, font: str) -> str:
    """
    Build full ffmpeg vf filter string:
      - dark overlay at bottom 35%
      - ITNEXUS brand text at top
      - Gold XAUUSD price label (gold-coloured, mid-screen)
      - Per-chunk subtitle text at 75% height
      - @ITNEXUS handle at bottom
    """
    f = []

    # Dark overlay at lower 35% for readability
    f.append(
        "drawbox=x=0:y=ih*0.65:w=iw:h=ih*0.35:color=black@0.60:t=fill"
    )

    # Top branding bar
    f.append(
        f"drawtext=text='ITNEXUS  |  AI TRADING SIGNALS'"
        f":fontfile='{font}':fontsize=36:fontcolor=white"
        f":bordercolor=black@0.9:borderw=3"
        f":x=(w-text_w)/2:y=75"
        f":enable='between(t,0,{total_dur:.2f})'"
    )

    # Gold signal label — shown from 4s onward
    f.append(
        f"drawtext=text='XAUUSD  BUY  4\\,670'"
        f":fontfile='{font}':fontsize=46:fontcolor=#FFD700"
        f":bordercolor=black@0.95:borderw=4"
        f":x=(w-text_w)/2:y=h*0.67"
        f":enable='between(t,4,55)'"
    )

    # Per-chunk subtitles
    for chunk in chunks:
        safe = esc(chunk["text"])
        ts   = chunk["start"]
        te   = chunk["end"]
        f.append(
            f"drawtext=text='{safe}'"
            f":fontfile='{font}':fontsize=52:fontcolor=white"
            f":bordercolor=black@0.95:borderw=4"
            f":x=(w-text_w)/2:y=h*0.76"
            f":enable='between(t,{ts:.3f},{te:.3f})'"
        )

    # Bottom handle
    f.append(
        f"drawtext=text='@ITNEXUS'"
        f":fontfile='{font}':fontsize=40:fontcolor=#FFD700"
        f":bordercolor=black@0.9:borderw=3"
        f":x=(w-text_w)/2:y=h*0.89"
        f":enable='between(t,0,{total_dur:.2f})'"
    )

    return ",".join(f)


# ─────────────────────────────────────────────────────────────────────────────
# 6. FINAL ASSEMBLY
# ─────────────────────────────────────────────────────────────────────────────
def get_audio_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-select_streams", "a:0", str(path)],
        capture_output=True, text=True, check=True,
    )
    d = json.loads(r.stdout)
    return float(d["streams"][0].get("duration", 62))


def assemble(bg: Path, vo: Path, vf: str, total_dur: float) -> Path:
    log("Assembling final video …")

    # Check whether background video has an audio stream
    probe_r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", str(bg)],
        capture_output=True, text=True, check=True,
    )
    probe_d = json.loads(probe_r.stdout)
    has_bg_audio = any(s["codec_type"] == "audio" for s in probe_d.get("streams", []))

    if has_bg_audio:
        filter_complex = (
            f"[0:v]{vf}[vout];"
            "[0:a]volume=0.15[bga];"
            "[1:a]volume=1.0[voa];"
            "[bga][voa]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        audio_map = "[aout]"
    else:
        filter_complex = (
            f"[0:v]{vf}[vout];"
            "[1:a]volume=1.0[aout]"
        )
        audio_map = "[aout]"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(bg),
        "-i", str(vo),
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", audio_map,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(total_dur),
        "-movflags", "+faststart",
        str(OUTPUT_MP4),
    ]

    log("  Running ffmpeg encode (30-90s) …")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        log("ffmpeg stderr (last 3000 chars):")
        print(r.stderr[-3000:])
        raise RuntimeError("ffmpeg assembly failed")

    size_mb = OUTPUT_MP4.stat().st_size / (1024 * 1024)
    log(f"  Output: {OUTPUT_MP4}  ({size_mb:.1f} MB)")
    return OUTPUT_MP4


# ─────────────────────────────────────────────────────────────────────────────
# 7. VALIDATE
# ─────────────────────────────────────────────────────────────────────────────
def validate(path: Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return {"valid": False, "error": r.stderr[:500]}
    d  = json.loads(r.stdout)
    sm = {s["codec_type"]: s for s in d.get("streams", [])}
    fmt = d.get("format", {})
    return {
        "valid":       "video" in sm and "audio" in sm,
        "duration_s":  round(float(fmt.get("duration", 0)), 2),
        "size_mb":     round(path.stat().st_size / (1024 * 1024), 2),
        "resolution":  f"{sm['video'].get('width')}x{sm['video'].get('height')}" if "video" in sm else "N/A",
        "video_codec": sm.get("video", {}).get("codec_name", "N/A"),
        "audio_codec": sm.get("audio", {}).get("codec_name", "N/A"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. METADATA
# ─────────────────────────────────────────────────────────────────────────────
def write_metadata(word_timings: list[dict], chunks: list[dict], v_info: dict):
    meta = {
        "channel":             "ITNEXUS",
        "title":               "AI Detected THIS Gold Buy Signal — XAUUSD 4,670",
        "description": (
            "Our AI swarm caught a high-confidence XAUUSD buy signal at 4,670. "
            "8 indicators, one clean signal. Follow ITNEXUS for daily AI trading alerts."
        ),
        "script":              SCRIPT,
        "word_count":          len(SCRIPT.split()),
        "word_timings":        len(word_timings),
        "subtitle_chunks":     len(chunks),
        "voice":               VOICE,
        "rate":                RATE,
        "output":              v_info,
        "produced_at":         time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tags": [
            "gold trading", "XAUUSD", "AI trading signals",
            "forex", "algorithmic trading", "ITNEXUS",
        ],
    }
    META_JSON.write_text(json.dumps(meta, indent=2))
    log(f"  Metadata: {META_JSON}")


# ─────────────────────────────────────────────────────────────────────────────
# 9. GDRIVE UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
def upload_gdrive() -> bool:
    log("Uploading to GDrive (gdrive:HumanAI/videos/trading/tiktok/) …")
    try:
        r = subprocess.run(
            ["rclone", "copy", str(OUTPUT_MP4), "gdrive:HumanAI/videos/trading/tiktok/"],
            capture_output=True, text=True, timeout=300,
        )
        if r.returncode == 0:
            log("  Upload complete.")
            return True
        log(f"  rclone failed (code {r.returncode}): {r.stderr[:400]}")
        return False
    except subprocess.TimeoutExpired:
        log("  rclone timed out")
        return False
    except FileNotFoundError:
        log("  rclone not installed — skipping upload")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
async def main() -> int:
    load_env()
    pexels_key = os.environ.get("PEXELS_API_KEY", "")
    t0 = time.time()

    log("=" * 60)
    log("ITNEXUS Gold Signal Video Producer")
    log("=" * 60)

    # 1. Voiceover
    word_timings = await generate_voiceover()

    # 2. Audio duration → video target length
    audio_dur    = get_audio_duration(VO_MP3)
    total_dur    = max(audio_dur + 1.5, 60.0)
    log(f"Audio duration: {audio_dur:.2f}s  →  Target: {total_dur:.2f}s")

    # 3. Subtitle chunks
    chunks = group_words(word_timings, chunk_size=4)
    log(f"Subtitle chunks: {len(chunks)}  (from {len(word_timings)} words)")

    # 4. Background video
    bg_src = None
    if pexels_key:
        if download_pexels_video(pexels_key):
            bg_src = PEXELS_MP4
    if bg_src is None or not bg_src.exists():
        log(f"Using cached fallback: {FALLBACK_VID}")
        bg_src = FALLBACK_VID

    # 5. Prepare background
    bg_ready = prepare_background(bg_src, total_dur)

    # 6. Font + filter chain
    font = find_font()
    log(f"Font: {font}")
    vf = build_filter(chunks, total_dur, font)

    # 7. Assemble
    assemble(bg_ready, VO_MP3, vf, total_dur)

    # 8. Validate
    v_info = validate(OUTPUT_MP4)
    log(
        f"Validated: valid={v_info['valid']}  "
        f"{v_info['duration_s']}s  {v_info['size_mb']}MB  "
        f"{v_info['resolution']}  v={v_info['video_codec']} a={v_info['audio_codec']}"
    )

    # 9. Metadata
    write_metadata(word_timings, chunks, v_info)

    # 10. Upload
    uploaded = upload_gdrive()

    # Summary
    elapsed = time.time() - t0
    log("=" * 60)
    log("PRODUCTION COMPLETE")
    log(f"  Output file : {OUTPUT_MP4}")
    log(f"  Size        : {v_info['size_mb']} MB")
    log(f"  Duration    : {v_info['duration_s']}s")
    log(f"  Resolution  : {v_info['resolution']}")
    log(f"  Voiceover   : YES (edge-tts {VOICE})")
    log(f"  Subtitles   : YES (burned-in, {len(chunks)} chunks)")
    log(f"  GDrive      : {'YES' if uploaded else 'NO (non-fatal)'}")
    log(f"  Elapsed     : {elapsed:.0f}s")
    log("=" * 60)

    return 0 if v_info["valid"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
