#!/usr/bin/env python3
"""
Media Generator — Real video pipeline for TikTok/YouTube Shorts
Uses Pexels for stock video, ffmpeg + MoviePy for assembly, edge-tts for voiceover, PIL for images.
"""
import asyncio, json, os, subprocess, sys, time, uuid, re, logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import requests

# ── Optional library imports (graceful fallback if unavailable) ──────────────
try:
    # moviepy v2.x: classes imported directly (no .editor submodule)
    from moviepy import (VideoFileClip, AudioFileClip, CompositeVideoClip,
                         TextClip, ImageClip, concatenate_videoclips,
                         concatenate_audioclips, CompositeAudioClip, ColorClip)
    import moviepy as mpe
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

try:
    import edge_tts
    EDGE_TTS_OK = True
except ImportError:
    EDGE_TTS_OK = False

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MEDIA_DIR    = PROJECT_ROOT / "data" / "media_output"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# Canonical output dirs for final (upload-ready) videos
_TRADING_TIKTOK  = MEDIA_DIR / "trading" / "tiktok"  # kept for legacy
_TRADING_ALL = MEDIA_DIR / "trading" / "all"
_TRADING_YOUTUBE = MEDIA_DIR / "trading" / "youtube"
_TRADING_DIRS = {
    "tiktok":         _TRADING_ALL,
    "youtube_shorts": _TRADING_ALL,
    "instagram_reel": _TRADING_ALL,  # all trading videos go to single folder
}
for _d in (_TRADING_TIKTOK, _TRADING_ALL):
    _d.mkdir(parents=True, exist_ok=True)

# Load .env if keys not already in environment
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists() and not os.getenv("PEXELS_API_KEY"):
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PEXELS_KEY   = os.getenv("PEXELS_API_KEY", "")
NVIDIA_KEY   = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/llama-3.1-nemotron-nano-8b-v1")
NVIDIA_BASE  = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

# TikTok/Shorts: 1080x1920 portrait, 15-60s, H.264
VIDEO_SPECS = {
    "tiktok":         {"w": 1080, "h": 1920, "max_s": 60, "fps": 30},
    "youtube_shorts": {"w": 1080, "h": 1920, "max_s": 60, "fps": 30},
    "instagram_reel": {"w": 1080, "h": 1920, "max_s": 90, "fps": 30},
}

def _generate_script(topic: str, platform: str, duration_s: int = 30) -> str:
    """Generate a short script/hook via NVIDIA NIM (no OpenRouter — no rate limits)."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from core.llm import complete
        result = complete(
            prompt=(f"Write a punchy {duration_s}s video script for {platform} about: {topic}. "
                    f"Format: HOOK (5 words), BODY (2-3 bullets), CTA (follow/like). "
                    f"Max 100 words total. Include 3 relevant hashtags."),
            max_tokens=200,
            temperature=0.7,
        )
        if result:
            return result
    except Exception as e:
        logger.warning(f"Script gen failed: {e}")
    return f"🔥 {topic} — Your trading edge starts here! Follow for daily signals. #trading #forex #gold"

# Legacy OpenRouter shim kept for backwards compat — not called
def _generate_script_openrouter_DISABLED(topic: str, platform: str, duration_s: int = 30) -> str:
    """DISABLED — was OpenRouter. Replaced by NVIDIA NIM via core.llm."""
    if not NVIDIA_KEY:
        return f"🚀 {topic} — follow for daily trading insights! #trading #forex #gold"
    try:
        r = requests.post(
            f"{NVIDIA_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {NVIDIA_KEY}",
                     "Content-Type": "application/json"},
            json={
                "model": NVIDIA_MODEL,
                "messages": [{
                    "role": "user",
                    "content": (f"Write a punchy {duration_s}s video script for {platform} about: {topic}. "
                                f"Format: HOOK (5 words), BODY (2-3 bullets), CTA (follow/like). "
                                f"Max 100 words total. Include 3 relevant hashtags.")
                }],
                "max_tokens": 200,
            },
            timeout=15
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"Script gen failed: {e}")
    return f"🔥 {topic} — Your trading edge starts here! Follow for daily signals. #trading #forex #gold"


def _get_used_pexels_ids() -> set:
    """Return set of Pexels video IDs already used in produced videos (dedup)."""
    idx_path = MEDIA_DIR / "VIDEO_INDEX.json"
    if not idx_path.exists():
        return set()
    try:
        import json as _json
        idx = _json.loads(idx_path.read_text())
        used = set()
        for v in idx.get("videos", []):
            src = v.get("pexels_id")
            if src:
                used.add(str(src))
        return used
    except Exception:
        return set()


def _fetch_pexels_video(query: str, min_duration: int = 10) -> Optional[str]:
    """Download a Pexels video clip. Returns local path or None.
    Deduplication: skip Pexels IDs already used in VIDEO_INDEX.json."""
    if not PEXELS_KEY:
        logger.warning("No PEXELS_API_KEY — cannot fetch stock video")
        return None
    used_ids = _get_used_pexels_ids()
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": query, "per_page": 15, "size": "medium", "orientation": "portrait"},
            timeout=10
        )
        if r.status_code != 200:
            logger.warning(f"Pexels API {r.status_code}: {r.text[:100]}")
            return None
        videos = r.json().get("videos", [])
        # Filter by portrait orientation, min duration, AND not already used
        for v in videos:
            vid_id = str(v["id"])
            if vid_id in used_ids:
                logger.debug(f"Skipping used Pexels video {vid_id}")
                continue
            if v.get("duration", 0) >= min_duration:
                files = sorted(v.get("video_files", []),
                               key=lambda f: f.get("width", 0) * f.get("height", 0),
                               reverse=True)
                for f in files:
                    if f.get("width", 1) < f.get("height", 1):  # portrait
                        url = f["link"]
                        _source_dir = MEDIA_DIR / "_source"
                        _source_dir.mkdir(parents=True, exist_ok=True)
                        dest = _source_dir / f"pexels_{vid_id}.mp4"
                        if not dest.exists():
                            _old_dest = MEDIA_DIR / f"pexels_{vid_id}.mp4"
                            if _old_dest.exists():
                                dest = _old_dest
                        if dest.exists():
                            return str(dest)
                        logger.info(f"Downloading new Pexels {vid_id} (unique)...")
                        data = requests.get(url, timeout=60, stream=True)
                        with open(dest, "wb") as fp:
                            for chunk in data.iter_content(8192):
                                fp.write(chunk)
                        return str(dest)
        logger.warning(f"All Pexels results for '{query}' already used — trying with page 2")
        # Fallback: page 2 to get fresh content
        r2 = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": query, "per_page": 5, "page": 2, "size": "medium", "orientation": "portrait"},
            timeout=10
        )
        if r2.status_code == 200:
            for v in r2.json().get("videos", []):
                if v.get("duration", 0) >= min_duration:
                    files = sorted(v.get("video_files", []), key=lambda f: f.get("width", 0)*f.get("height", 0), reverse=True)
                    for f in files:
                        if f.get("width", 1) < f.get("height", 1):
                            url = f["link"]
                            vid_id = str(v["id"])
                            dest = MEDIA_DIR / "_source" / f"pexels_{vid_id}.mp4"
                            if not dest.exists():
                                data = requests.get(url, timeout=60, stream=True)
                                with open(dest, "wb") as fp:
                                    for chunk in data.iter_content(8192): fp.write(chunk)
                            return str(dest)
    except Exception as e:
        logger.error(f"Pexels fetch failed: {e}")
    return None


def _make_text_overlay_filter(text: str, w: int, h: int) -> str:
    """Build ffmpeg drawtext filter for text overlay."""
    # Escape special chars for ffmpeg filter
    safe = re.sub(r"[:'\\]", " ", text)[:80]
    return (
        f"drawtext=text='{safe}':"
        f"fontcolor=white:fontsize=48:borderw=3:bordercolor=black:"
        f"x=(w-text_w)/2:y=h*0.15:line_spacing=10:"
        f"font=DejaVuSans-Bold"
    )


def _make_gradient_background(w: int, h: int, output: str):
    """Create a gradient background image using PIL."""
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (w, h))
        draw = ImageDraw.Draw(img)
        # Dark gradient: dark blue to dark purple
        for y in range(h):
            ratio = y / h
            r = int(10 + ratio * 20)
            g = int(10 + ratio * 5)
            b = int(40 + ratio * 60)
            draw.line([(0, y), (w, y)], fill=(r, g, b))
        img.save(output)
        return True
    except Exception as e:
        logger.warning(f"PIL gradient failed: {e}")
        return False


async def _edge_tts_voiceover(text: str, output_path: str, voice: str = "en-US-GuyNeural") -> bool:
    """Generate voiceover MP3 via edge-tts. Returns True on success."""
    if not EDGE_TTS_OK:
        return False
    try:
        # Strip emoji and markdown for clean TTS
        clean = re.sub(r'[^\w\s.,!?#@]', '', text)[:300]
        communicate = edge_tts.Communicate(clean, voice)
        await communicate.save(output_path)
        return Path(output_path).exists() and Path(output_path).stat().st_size > 1000
    except Exception as e:
        logger.warning(f"edge-tts failed: {e}")
        return False


def _generate_voiceover(text: str, output_path: str, voice: str = "en-US-GuyNeural") -> bool:
    """Sync wrapper for edge-tts voiceover generation."""
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_edge_tts_voiceover(text, output_path, voice))
        loop.close()
        return result
    except Exception as e:
        logger.warning(f"Voiceover generation failed: {e}")
        return False


def _compose_with_moviepy(video_path: str, audio_path: str, output_path: str,
                           caption: str, duration_s: int, w: int, h: int) -> bool:
    """
    Compose final video using MoviePy:
    - Load stock/background video clip
    - Add edge-tts voiceover audio
    - Add text caption overlay
    - Export to output_path
    """
    if not MOVIEPY_OK:
        return False
    try:
        _src = VideoFileClip(video_path)
        video = _src.subclipped(0, min(duration_s, _src.duration))
        video = video.resized((w, h))

        # Mix in voiceover audio (moviepy v2 API)
        if Path(audio_path).exists() and Path(audio_path).stat().st_size > 1000:
            vo = AudioFileClip(audio_path)
            vo_dur = min(vo.duration, video.duration)
            vo = vo.with_end(vo_dur)
            if video.audio:
                bg_audio = video.audio.with_volume_scaled(0.3)
                mixed = CompositeAudioClip([bg_audio, vo])
                video = video.with_audio(mixed)
            else:
                video = video.with_audio(vo)

        # Text overlay — moviepy v2 TextClip requires ImageMagick for caption method
        safe_caption = re.sub(r'[^\w\s.,!?#]', '', caption)[:60]
        try:
            txt = (TextClip(text=safe_caption, font_size=50, color='white',
                            stroke_color='black', stroke_width=2,
                            size=(w - 80, None), method='caption')
                   .with_position(('center', int(h * 0.08)))
                   .with_duration(video.duration))
            video = CompositeVideoClip([video, txt])
        except Exception as e_txt:
            logger.warning(f"TextClip overlay skipped (ImageMagick needed): {e_txt}")

        video.write_videofile(output_path, fps=30, codec='libx264',
                              audio_codec='aac', bitrate='3000k',
                              ffmpeg_params=['-preset', 'medium', '-movflags', '+faststart'],
                              logger=None)
        return Path(output_path).exists() and Path(output_path).stat().st_size > 10000
    except Exception as e:
        logger.error(f"MoviePy composition failed: {e}")
        return False


def _topic_slug(topic: str, max_len: int = 40) -> str:
    """Convert a topic string to a safe filename slug."""
    # Strip non-ASCII (emoji etc.)
    text = topic.encode("ascii", "ignore").decode().lower()
    # Replace non-alphanum with spaces
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    words = text.split()
    slug  = "_".join(words)[:max_len].rstrip("_")
    return slug or "trading"


def generate_short(
    topic: str,
    platform: str = "tiktok",
    duration_s: int = 30,
    search_query: Optional[str] = None,
    use_voiceover: bool = True,
) -> dict:
    """
    Generate a TikTok/YouTube Shorts video.
    Returns dict with output_path, caption, script, success.
    """
    spec   = VIDEO_SPECS.get(platform, VIDEO_SPECS["tiktok"])
    w, h   = spec["w"], spec["h"]
    fps    = spec["fps"]
    date_str = datetime.now().strftime("%Y%m%d")
    ts_str   = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug     = _topic_slug(topic)
    out_dir  = MEDIA_DIR / f"reel_{platform}_{ts_str}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = out_dir / f"{platform}_{date_str}_{slug}.mp4"
    thumb   = out_dir / "thumbnail.jpg"

    logger.info(f"[MediaGen] Generating {platform} video | moviepy={MOVIEPY_OK} edge_tts={EDGE_TTS_OK}")

    # ── 1. Script + voiceover script ─────────────────────────
    script = _generate_script(topic, platform, duration_s)
    caption_hook = script.split("\n")[0] if script else topic
    (out_dir / "caption.txt").write_text(script)

    # ── 2. Generate voiceover (edge-tts) ─────────────────────
    vo_path = str(out_dir / "voiceover.mp3")
    has_vo = False
    if use_voiceover and EDGE_TTS_OK:
        # Build spoken version: first line + key points, stripped of hashtags
        spoken = re.sub(r'#\w+', '', script).strip()[:200]
        has_vo = _generate_voiceover(spoken, vo_path)
        if has_vo:
            logger.info(f"[MediaGen] Voiceover generated: {Path(vo_path).stat().st_size // 1024}KB")

    # ── 3. Try Pexels stock video ─────────────────────────────
    q = search_query or topic
    src_video = _fetch_pexels_video(q, min_duration=duration_s)

    # ── 4a. MoviePy composition (preferred when available) ────
    success = False
    if MOVIEPY_OK and src_video:
        logger.info("[MediaGen] Using MoviePy for composition")
        success = _compose_with_moviepy(src_video, vo_path if has_vo else "",
                                        str(out_mp4), caption_hook, duration_s, w, h)
        if success:
            logger.info(f"[MediaGen] MoviePy success: {out_mp4.stat().st_size // 1024}KB")

    # ── 4b. ffmpeg fallback ───────────────────────────────────
    if not success:
        logger.info("[MediaGen] Using ffmpeg fallback")
        if src_video:
            vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                  f"crop={w}:{h},"
                  f"{_make_text_overlay_filter(caption_hook, w, h)}")
            ffcmd = ["ffmpeg", "-y", "-i", src_video, "-t", str(duration_s),
                     "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-b:v", "3000k",
                     "-c:a", "aac", "-b:a", "128k", "-r", str(fps),
                     "-movflags", "+faststart", str(out_mp4)]
            # Mix in voiceover if available
            if has_vo:
                ffcmd = ["ffmpeg", "-y", "-i", src_video, "-i", vo_path,
                         "-t", str(duration_s), "-vf", vf,
                         "-filter_complex", "[0:a]volume=0.3[bg];[1:a]volume=1.0[vo];[bg][vo]amix=inputs=2:duration=first[a]",
                         "-map", "0:v", "-map", "[a]",
                         "-c:v", "libx264", "-preset", "medium", "-b:v", "3000k",
                         "-c:a", "aac", "-b:a", "128k", "-r", str(fps),
                         "-movflags", "+faststart", str(out_mp4)]
        else:
            bg_path = str(out_dir / "bg.png")
            _make_gradient_background(w, h, bg_path)
            if has_vo:
                ffcmd = ["ffmpeg", "-y", "-loop", "1", "-i", bg_path, "-i", vo_path,
                         "-t", str(duration_s),
                         "-vf", _make_text_overlay_filter(script.replace("\n", " | ")[:120], w, h),
                         "-c:v", "libx264", "-preset", "medium", "-b:v", "3000k",
                         "-c:a", "aac", "-b:a", "128k",
                         "-pix_fmt", "yuv420p", "-r", str(fps),
                         "-movflags", "+faststart", "-shortest", str(out_mp4)]
            else:
                ffcmd = ["ffmpeg", "-y", "-loop", "1", "-i", bg_path,
                         "-t", str(duration_s),
                         "-vf", _make_text_overlay_filter(script.replace("\n", " | ")[:120], w, h),
                         "-c:v", "libx264", "-preset", "medium", "-b:v", "3000k",
                         "-pix_fmt", "yuv420p", "-r", str(fps),
                         "-movflags", "+faststart", str(out_mp4)]
        try:
            result = subprocess.run(ffcmd, capture_output=True, text=True, timeout=300)
            success = out_mp4.exists() and out_mp4.stat().st_size > 10000
            if not success:
                logger.error(f"ffmpeg failed: {result.stderr[-300:]}")
        except subprocess.TimeoutExpired:
            logger.error("ffmpeg timed out")
            success = False

    # ── 4. Generate thumbnail ─────────────────────────────────
    if success:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(out_mp4),
            "-ss", "00:00:02", "-vframes", "1", str(thumb)
        ], capture_output=True, timeout=15)

    # ── 6. Write metadata ─────────────────────────────────────
    meta = {
        "topic": topic, "platform": platform, "duration_s": duration_s,
        "output": str(out_mp4) if success else None,
        "thumbnail": str(thumb) if thumb.exists() else None,
        "caption": caption_hook, "script": script,
        "success": success,
        "file_size_kb": round(out_mp4.stat().st_size / 1024, 1) if success and out_mp4.exists() else 0,
        "voiceover": has_vo,
        "voiceover_path": vo_path if has_vo else None,
        "engine": "moviepy" if (MOVIEPY_OK and success) else "ffmpeg",
        "generated_at": datetime.now().isoformat(),
    }
    (out_dir / "reel_metadata.json").write_text(json.dumps(meta, indent=2))
    logger.info(f"[MediaGen] {'SUCCESS' if success else 'FAILED'} {out_mp4.name} ({meta['file_size_kb']}KB)")

    # Copy final video to canonical trading output folder
    if success and out_mp4.exists():
        canonical_dir = _TRADING_DIRS.get(platform, _TRADING_TIKTOK)
        canonical_dest = canonical_dir / out_mp4.name
        try:
            import shutil as _shutil
            _shutil.copy2(str(out_mp4), str(canonical_dest))
            meta["canonical_output"] = str(canonical_dest)
            logger.info(f"[MediaGen] Canonical copy: {canonical_dest}")
        except Exception as _e:
            logger.warning(f"[MediaGen] Canonical copy failed: {_e}")

    return meta


# ── Diverse topic library — rotated to improve content variety on TikTok/Shorts ─
TRADING_TOPICS = [
    # Signal-based (existing core)
    "Gold BUY signal on XAUUSD — technical analysis & entry points",
    "Gold SELL signal on XAUUSD — key resistance levels & exit strategy",
    "Trading update: XAUUSD market analysis and what to watch next",
    # New high-engagement topic templates
    "3 signs gold is about to move big — XAUUSD setup to watch",
    "Why institutional traders watch THIS level on XAUUSD",
    "Bitcoin vs Gold: which wins in 2025? The data may surprise you",
    "The #1 mistake crypto traders make at market open",
    "How to read the fear & greed index for better trades",
    "Why trading during London open beats every other session",
    "XAUUSD: what 5000 support means for traders right now",
    "The signal that predicted the last 5 gold moves — here it is again",
    "Why your stop loss is too tight — and how to actually fix it",
    "Binance futures: 3 setups that actually work in 2025",
    # Additional variety
    "Gold breaks key resistance — what happens next on XAUUSD",
    "How to trade the XAUUSD news spike without getting wrecked",
    "Why most retail traders lose on gold — the real reason",
    "XAUUSD higher lows pattern — breakout imminent?",
    "Trading psychology: why you keep closing winners too early",
    "The 15-minute chart setup that finds gold reversals",
    "Risk/reward ratio: the trading rule that changes everything",
]


def generate_trading_content(symbol: str = "XAUUSD", signal: str = "BUY") -> dict:
    """Convenience: generate trading signal video for social media.
    Rotates through TRADING_TOPICS for variety; signal-keyed topics used when signal provided.
    """
    import random
    signal_topics = {
        "BUY":  f"Gold BUY signal on {symbol} — technical analysis & entry points",
        "SELL": f"Gold SELL signal on {symbol} — key resistance levels & exit strategy",
        "HOLD": f"Trading update: {symbol} market analysis and what to watch next",
    }
    if signal and signal in signal_topics:
        topic = signal_topics[signal]
    else:
        # Pick a random topic from the expanded library (not the first 3 signal topics)
        topic = random.choice(TRADING_TOPICS[3:])
    return generate_short(
        topic=topic,
        platform="tiktok",
        duration_s=30,
        search_query="gold trading charts forex"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing media generator...")
    result = generate_short(
        topic="Gold XAUUSD breakout — trading signal analysis",
        platform="tiktok",
        duration_s=20,
        search_query="gold trading"
    )
    print(json.dumps(result, indent=2))
