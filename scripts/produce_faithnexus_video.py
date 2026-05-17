#!/usr/bin/env python3
"""
FaithNexus Video Producer v2 — Autonomous biblical/Christian short-form video pipeline
======================================================================================
60-90 second videos with:
  - Full narration script (intro → context → verse → deep reflection → application → CTA)
  - edge-tts AriaNeural voiceover (slow, reverent)
  - Multiple Pexels background images as Ken Burns slideshow (zoompan + xfade crossfade)
  - Word-timed burned-in subtitles (3-4 words per line at video bottom)
  - Scripture reference overlay at top
  - FAITHNEXUS branding watermark
  - Auto-upload to GDrive Video Uploads/FaithNexus/

Usage:
  python3 scripts/produce_faithnexus_video.py --auto
  python3 scripts/produce_faithnexus_video.py --index 0
  python3 scripts/produce_faithnexus_video.py --verse "John 3:16"
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


def _load_env():
    env_file = _ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

PEXELS_KEY   = os.environ.get("PEXELS_API_KEY", "")
_FONT_BOLD   = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_FONT_ITALIC = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"
if not Path(_FONT_BOLD).exists():
    _FONT_BOLD   = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
    _FONT_ITALIC = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"

VW, VH = 1080, 1920     # 9:16 portrait
FPS    = 30
VOICE  = "en-US-AriaNeural"
RATE   = "-8%"           # slower for scripture reading

# ── Scripture library ─────────────────────────────────────────────────────────
# Each entry includes 4 Pexels image search queries (for the slideshow panels)
SCRIPTURES = [
    {
        "verse":   "John 3:16",
        "theme":   "hope",
        "text":    "For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life.",
        "images":  ["sunrise over ocean golden light", "cross silhouette sunset sky", "dove in flight clouds", "open bible light rays"],
    },
    {
        "verse":   "Psalm 23:1-3",
        "theme":   "peace",
        "text":    "The Lord is my shepherd, I lack nothing. He makes me lie down in green pastures, he leads me beside quiet waters, he refreshes my soul.",
        "images":  ["green meadow peaceful morning", "calm river valley mist", "shepherd field golden hour", "serene lake reflection sky"],
    },
    {
        "verse":   "Jeremiah 29:11",
        "theme":   "purpose",
        "text":    "For I know the plans I have for you, declares the Lord, plans to prosper you and not to harm you, plans to give you hope and a future.",
        "images":  ["mountain path sunrise fog", "open road horizon dawn", "seeds germinating soil light", "hands cupping light nature"],
    },
    {
        "verse":   "Philippians 4:13",
        "theme":   "strength",
        "text":    "I can do all this through him who gives me strength.",
        "images":  ["mountain peak summit clouds", "eagle soaring sky freedom", "waterfall power nature", "sunlight through forest trees"],
    },
    {
        "verse":   "Isaiah 40:31",
        "theme":   "renewal",
        "text":    "But those who hope in the Lord will renew their strength. They will soar on wings like eagles; they will run and not grow weary, they will walk and not be faint.",
        "images":  ["eagle flying clouds sunrise", "runner silhouette sunrise", "flowers blooming spring", "mountain sunrise panoramic"],
    },
    {
        "verse":   "Proverbs 3:5-6",
        "theme":   "trust",
        "text":    "Trust in the Lord with all your heart and lean not on your own understanding; in all your ways submit to him, and he will make your paths straight.",
        "images":  ["winding forest path morning light", "compass on map journey", "bridge over stream nature", "hands open surrender light"],
    },
    {
        "verse":   "Romans 8:28",
        "theme":   "goodness",
        "text":    "And we know that in all things God works for the good of those who love him, who have been called according to his purpose.",
        "images":  ["golden sunset horizon field", "wheat field light evening", "storm clouds clearing light", "rainbow after rain landscape"],
    },
    {
        "verse":   "Matthew 11:28",
        "theme":   "rest",
        "text":    "Come to me, all you who are weary and burdened, and I will give you rest.",
        "images":  ["calm ocean waves gentle", "peaceful hammock sunset", "still lake forest reflection", "soft morning light bedroom"],
    },
    {
        "verse":   "Psalm 46:10",
        "theme":   "stillness",
        "text":    "Be still, and know that I am God; I will be exalted among the nations, I will be exalted in the earth.",
        "images":  ["still mountain lake mirror", "silent forest mist morning", "candle flame dark peaceful", "snow landscape silence"],
    },
    {
        "verse":   "1 Corinthians 13:4-7",
        "theme":   "love",
        "text":    "Love is patient, love is kind. It does not envy, it does not boast, it is not proud. It does not dishonour others, it is not self-seeking. It always protects, always trusts, always hopes, always perseveres.",
        "images":  ["sunset couple silhouette", "flowers spring morning light", "heart rock nature love", "family hands together warm light"],
    },
]


# ── Full 60-90s narration script builder ─────────────────────────────────────

def build_full_narration(s: Dict) -> List[Dict]:
    """
    Build a 5-segment narration script targeting 60-90 seconds total.
    Returns list of {name, text} dicts in order.
    """
    verse = s["verse"]
    text  = s["text"]
    theme = s["theme"]

    # Theme-specific opening hooks
    hooks = {
        "hope":     "There is a love in this world so vast, so complete, that it changed everything.",
        "peace":    "In a world full of noise and rushing, there is a voice that speaks peace to your soul.",
        "purpose":  "Have you ever wondered if your life has a direction, a plan written before you were born?",
        "strength": "When you feel like you cannot take another step, there is a strength greater than your own.",
        "renewal":  "Every morning carries the promise of a new beginning. Your story is not finished yet.",
        "trust":    "When the way forward is unclear and the path seems uncertain, there is wisdom available to you.",
        "goodness": "Even in the hardest seasons, something greater is at work in the background of your life.",
        "rest":     "If life has left you exhausted and weary, there is an invitation waiting for you today.",
        "stillness":"The most powerful moments are often found in the quietest places.",
        "love":     "Of all the forces in creation, the most enduring and the most transforming is love.",
    }

    # Theme-specific reflections
    reflections = {
        "hope":     "These words from John chapter 3 verse 16 are perhaps the most well-known in all of Scripture. They tell us that the God who created the universe did not stand at a distance — He entered into it. He gave His Son. He gave everything. And this gift of eternal life is available to you, to me, to anyone who believes. That is the definition of extraordinary love.",
        "peace":    "King David wrote these words from Psalm 23 from a place of deep experience. He had known danger, loneliness, and fear. And yet he looked back and could say — through all of it, I lacked nothing. The shepherd was always there. The quiet waters were always leading somewhere. And that same shepherd is walking with you today.",
        "purpose":  "These words were written to a people in exile — people who had lost everything and wondered if God had forgotten them. And God's answer was this: I have not forgotten. I have a plan. Not a plan of harm, but of hope. A future. If you feel forgotten or lost today, receive this word as your own. God knows your name, and He has not abandoned your story.",
        "strength": "Paul wrote these words from a prison cell. Not from a mountaintop of success, but from chains. And still he wrote — I can do all things. Because the strength he was describing was not his own. It was sourced from somewhere beyond himself. Whatever you are facing today — the impossible, the exhausting, the overwhelming — this same strength is available to you.",
        "renewal":  "Isaiah wrote this as a promise to a weary nation. And it holds true for every weary soul. Those who wait on God do not simply cope — they soar. They run without fainting. There is a supernatural exchange available: your weakness for His strength. Your weariness for His energy. Your worn-out season for His renewal. That exchange is available to you right now.",
        "trust":    "Solomon wrote this as one of the most practical pieces of wisdom ever recorded. Not a formula for success — a posture of the heart. Lean not on your own understanding. That does not mean your mind does not matter. It means that there is a wisdom greater than any analysis, any strategy, any plan we can make. Surrender to it. Submit to it. And watch the paths become clear.",
        "goodness": "Romans 8:28 is not a promise that everything will be easy. It is a promise that nothing is wasted. Every hard thing, every confusing season, every door that closed — in the hands of God — is being woven into something good. You may not see it yet. But it is being worked out. Hold on. The tapestry is still being made.",
        "rest":     "Jesus spoke these words to people who were tired — tired from religion, from performance, from carrying things they were never meant to carry alone. And He says: come. Not perform. Not achieve. Just come. Lay it down. His yoke is easy. His burden is light. Whatever you have been carrying today, you do not have to carry it any further.",
        "stillness":"Psalm 46 was written in the middle of chaos — nations in uproar, kingdoms falling, the earth shaking. And in the middle of it all, God says: Be still. Know that I am God. The word still means to let go, to release your grip, to stop striving. It is a command and an invitation. In the stillness, you will find that He is there. He always was.",
        "love":     "First Corinthians 13 is often called the love chapter. But look at what love actually is in these verses. It is not a feeling — it is a set of choices. Patience. Kindness. Humility. Perseverance. These are not emotions that come naturally. They are fruit of something deeper — something planted in us by the God who is love. This is the love you are called to both receive and give.",
    }

    # Theme-specific application
    applications = {
        "hope":     "Take a moment today to receive this truth personally. Not as a distant theological idea — but as a word spoken directly to you. You are loved. You are not forgotten. And eternal life is not just about the afterlife — it begins right now, in relationship with the God who gave everything for you.",
        "peace":    "No matter what you are walking through today — the shepherd knows your name. He is leading you beside still waters, even when the road feels turbulent. Trust the process. Trust the shepherd. You will look back one day and say, through all of it, I lacked nothing.",
        "purpose":  "If you are in a waiting season, take heart. The plans God has for you are being written even now. The exile has an end. The wandering has a destination. Your next chapter is being prepared. Rest in that today.",
        "strength": "Whatever challenge is in front of you right now — bring it to God. Not in your strength, but in His. Ask for what you need. He is the source of strength that does not run out, the power that is made perfect in weakness. You are not alone in this.",
        "renewal":  "If you have been running on empty, today is the day to wait on God. To stop striving in your own strength. To receive the renewal that only He can give. Spread your wings. He will do the lifting.",
        "trust":    "Where in your life are you leaning on your own understanding instead of trusting God? Bring that to Him today. Acknowledge Him in it. And watch as He begins to make the path straight — in His time, and in His perfect way.",
        "goodness": "Whatever season you are in — trust the process. Trust the weaver. The threads that seem dark or tangled right now are part of something beautiful being made. Your story is still being written. And the author is good.",
        "rest":     "What are you carrying today that was never meant for you to carry alone? Lay it down. Come to Jesus just as you are. Weary, burdened, broken, tired — He says come. And He will give you rest.",
        "stillness":"Find a moment today to be still. To put down the phone, step away from the noise, and simply know that He is God. In that stillness, He will speak. He will restore. He will be found.",
        "love":     "Ask God today to grow this kind of love in you — patient, kind, humble, persevering. Not manufactured by willpower, but produced by relationship. Spend time with the one who is love, and you will begin to look like Him.",
    }

    cta = (
        "If this spoke to your heart today, share it with someone who needs to hear it. "
        "Follow FaithNexus for daily scripture, encouragement, and truth. "
        "New videos every day. Stay blessed and GOD loves you."
    )

    return [
        {"name": "hook",        "text": hooks.get(theme,        "There is a word for you today from the living God.")},
        {"name": "verse_intro", "text": f"From the book of {verse}:"},
        {"name": "verse_read",  "text": text},
        {"name": "reflection",  "text": reflections.get(theme,   "Let these words settle deep into your spirit today.")},
        {"name": "application", "text": applications.get(theme,  "Receive this word as your own today. Walk in it.")},
        {"name": "cta",         "text": cta},
    ]


# ── TTS generation ────────────────────────────────────────────────────────────

async def _tts_segment(text: str, out_path: str) -> Tuple[float, List[Dict]]:
    """Generate TTS for one segment. Returns (duration_s, word_timings)."""
    import edge_tts
    communicate   = edge_tts.Communicate(text, VOICE, rate=RATE)
    audio_chunks: List[bytes] = []
    word_timings: List[Dict]  = []

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
            word_timings.append({
                "text":  chunk.get("text", ""),
                "start": chunk["offset"] / 10_000_000,
                "end":   (chunk["offset"] + chunk.get("duration", 300_000)) / 10_000_000,
            })

    with open(out_path, "wb") as f:
        for c in audio_chunks: f.write(c)

    dur = _ffprobe_dur(out_path)
    return dur, word_timings


def _ffprobe_dur(path: str) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(path)],
            capture_output=True, text=True, timeout=15
        )
        for s in json.loads(r.stdout).get("streams", []):
            if "duration" in s:
                return float(s["duration"])
    except Exception:
        pass
    return 0.0


# ── Subtitle phrase builder ───────────────────────────────────────────────────

def _make_phrases(text: str, seg_start: float, seg_end: float) -> List[Dict]:
    """Split text into 3-4 word subtitle chunks and time them across the segment."""
    words   = text.split()
    chunks  = []
    current = []
    for w in words:
        current.append(w)
        if len(current) >= 4 or w.endswith((".", "!", "?", ";", ":")):
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))

    if not chunks:
        return []
    seg_dur   = seg_end - seg_start
    chunk_dur = seg_dur / len(chunks)
    result    = []
    for i, c in enumerate(chunks):
        result.append({
            "text":  c,
            "start": seg_start + i * chunk_dur,
            "end":   seg_start + (i + 1) * chunk_dur - 0.08,
        })
    return result


# ── Pexels image download ─────────────────────────────────────────────────────

def _dl_pexels_photo(query: str, out_path: str, idx: int = 0) -> bool:
    """Download a portrait photo from Pexels."""
    if not PEXELS_KEY:
        return False
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": query, "orientation": "portrait", "per_page": 10, "size": "large"},
            timeout=15,
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if not photos:
            return False
        photo = photos[min(idx, len(photos) - 1)]
        # Use 'large2x' for high-res, fallback to 'large'
        url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large")
        if not url:
            return False
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(8192): f.write(chunk)
        print(f"   Downloaded image: {Path(out_path).name} ({Path(out_path).stat().st_size//1024}KB)")
        return True
    except Exception as e:
        print(f"   Pexels image failed ({query}): {e}")
        return False


# ── ffmpeg text escaping ──────────────────────────────────────────────────────

def _esc(t: str) -> str:
    t = t.replace("\\", "\\\\")
    t = t.replace("'",  "’")   # smart apostrophe — avoids ffmpeg quote issue
    t = t.replace(":",  "\\:")
    t = t.replace(",",  "\\,")
    t = t.replace(";",  "\\;")
    return t


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def produce_video(scripture: Dict, out_root: Path) -> Optional[Dict]:
    verse     = scripture["verse"]
    theme     = scripture["theme"]
    text      = scripture["text"]
    img_queries = scripture["images"]    # 4 search queries for slideshow panels

    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
    verse_slug = re.sub(r"[^\w]", "_", verse)
    out_dir   = out_root / f"{verse_slug}_{theme}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  FaithNexus Video Producer v2")
    print(f"  Verse : {verse}")
    print(f"  Theme : {theme}")
    print(f"  Output: {out_dir}")
    print(f"{'='*60}")

    # ── 1. Build and speak narration segments ─────────────────────────────────
    segments = build_full_narration(scripture)
    print(f"\n[1/6] Generating voiceover ({len(segments)} segments)...")

    seg_audios:    List[Path]       = []
    seg_durations: List[float]      = []
    seg_timings:   List[List[Dict]] = []

    for seg in segments:
        ap  = out_dir / f"seg_{seg['name']}.mp3"
        print(f"   → {seg['name']}: \"{seg['text'][:70]}{'...' if len(seg['text'])>70 else ''}\"")
        dur, timings = await _tts_segment(seg["text"], str(ap))
        seg_audios.append(ap)
        seg_durations.append(dur)
        seg_timings.append(timings)
        print(f"      {dur:.2f}s")

    # ── 2. Concatenate all segments into one voiceover ────────────────────────
    print(f"\n[2/6] Concatenating voiceover...")
    vo_path   = out_dir / "voiceover.mp3"
    concat_f  = out_dir / "concat_list.txt"
    concat_f.write_text("\n".join(f"file '{ap.resolve()}'" for ap in seg_audios) + "\n")

    r = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat_f), "-c", "copy", str(vo_path)],
        capture_output=True, text=True, timeout=60
    )
    if r.returncode != 0:
        raise RuntimeError(f"Audio concat failed: {r.stderr[-400:]}")

    total_dur = _ffprobe_dur(str(vo_path))
    print(f"   Total voiceover duration: {total_dur:.2f}s")

    if total_dur < 55:
        print(f"   WARNING: video will be {total_dur:.1f}s — target is 60-90s")

    # ── 3. Build subtitle phrase timeline ────────────────────────────────────
    print(f"\n[3/6] Building subtitle timeline...")
    all_phrases: List[Dict] = []
    cursor = 0.0
    for i, seg in enumerate(segments):
        seg_end = cursor + seg_durations[i]
        # Show verse reference during verse_intro and start of verse_read
        if seg["name"] not in ("hook",):
            phrases = _make_phrases(seg["text"], cursor, seg_end)
            all_phrases.extend(phrases)
        cursor = seg_end

    print(f"   {len(all_phrases)} subtitle phrases across {total_dur:.1f}s")

    # Scripture reference: show from 0 until end of verse_read segment
    verse_ref_end = sum(seg_durations[:3]) + 1.0   # hook + verse_intro + verse_read

    # ── 4. Download 4 Pexels background images ───────────────────────────────
    print(f"\n[4/6] Downloading background images ({len(img_queries)} images)...")
    img_paths: List[Path] = []
    fallback_queries = [
        "nature light sunrise peaceful",
        "forest morning light fog",
        "ocean sunset golden",
        "mountains sky clouds",
    ]
    for i, query in enumerate(img_queries):
        img_path = out_dir / f"bg_{i:02d}.jpg"
        # Try requested query first, fallback if fails
        ok = _dl_pexels_photo(query, str(img_path), idx=i % 3)
        if not ok:
            ok = _dl_pexels_photo(fallback_queries[i % len(fallback_queries)], str(img_path), idx=0)
        if ok:
            img_paths.append(img_path)
        else:
            print(f"   Could not get image {i+1} — will duplicate earlier image")

    if not img_paths:
        raise RuntimeError("No Pexels images downloaded — check PEXELS_API_KEY")

    # Ensure we have exactly 4 images (duplicate if fewer)
    while len(img_paths) < 4:
        img_paths.append(img_paths[-1])

    # ── 5. Build slideshow with Ken Burns effect + xfade transitions ──────────
    print(f"\n[5/6] Assembling slideshow video...")

    # Each image gets equal time; crossfade 1s between panels
    n_images   = len(img_paths)
    xfade_dur  = 1.0        # 1s crossfade between images
    # Total video = voiceover + 1s tail
    video_dur  = total_dur + 1.0
    # Time per image (overlap by xfade_dur at boundaries)
    per_img    = video_dur / n_images + xfade_dur

    output_mp4 = out_dir / f"faithnexus_{verse_slug}.mp4"

    # Build ffmpeg filter_complex:
    #   For each image:
    #     - loop+scale to portrait 1080x1920
    #     - zoompan for gentle Ken Burns effect
    #     - pad to exact size
    #   xfade chain between all images
    #   dark overlay
    #   drawtext subtitles + watermark
    #   mix voiceover

    frames_per_img = int(per_img * FPS)

    # Each image: input → scale+crop → zoompan → segment video
    filter_parts: List[str] = []
    input_args: List[str]   = []

    # Input 0..N-1 = images, input N = voiceover audio
    for i, img in enumerate(img_paths):
        input_args += ["-loop", "1", "-t", f"{per_img:.3f}", "-i", str(img)]

    input_args += ["-i", str(vo_path)]
    vo_idx = n_images

    # Image processing filters
    for i in range(n_images):
        # Alternate zoompan directions for visual variety
        if i % 4 == 0:
            zoom_expr = f"min(zoom+0.0004,1.05)"
            x_expr    = "iw/2-(iw/zoom/2)"
            y_expr    = "ih/2-(ih/zoom/2)"
        elif i % 4 == 1:
            zoom_expr = f"min(zoom+0.0004,1.05)"
            x_expr    = "iw-iw/zoom"
            y_expr    = "0"
        elif i % 4 == 2:
            zoom_expr = f"if(eq(on,1),1.05,max(zoom-0.0004,1.0))"
            x_expr    = "iw/2-(iw/zoom/2)"
            y_expr    = "ih-ih/zoom"
        else:
            zoom_expr = f"min(zoom+0.0003,1.04)"
            x_expr    = "0"
            y_expr    = "ih/2-(ih/zoom/2)"

        filter_parts.append(
            f"[{i}:v]scale={VW*2}:{VH*2}:force_original_aspect_ratio=increase,"
            f"crop={VW*2}:{VH*2},"
            f"scale={VW}:{VH}:force_original_aspect_ratio=increase,"
            f"crop={VW}:{VH},"
            f"fps={FPS},"
            f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':"
            f"d={frames_per_img}:s={VW}x{VH}:fps={FPS},"
            f"trim=duration={per_img:.3f},setpts=PTS-STARTPTS[img{i}]"
        )

    # xfade chain: img0 + img1 → xf01, xf01 + img2 → xf012, ...
    if n_images == 1:
        filter_parts.append(f"[img0]null[slideshow]")
    else:
        # xfade offset: when image i ends (accounting for previous overlaps)
        # offset for xfade between img_i and img_{i+1}
        prev_out = "img0"
        for i in range(1, n_images):
            offset = per_img * i - xfade_dur * i
            out_label = f"xf{i}" if i < n_images - 1 else "slideshow"
            filter_parts.append(
                f"[{prev_out}][img{i}]xfade=transition=fade:duration={xfade_dur}:offset={offset:.3f}[{out_label}]"
            )
            prev_out = f"xf{i}"

    # Dark overlay + subtitles
    filter_parts.append(
        f"[slideshow]trim=duration={video_dur:.3f},setpts=PTS-STARTPTS[trimmed]"
    )
    filter_parts.append(
        f"color=black@0.45:size={VW}x{VH}:rate={FPS},trim=duration={video_dur:.3f}[darklayer]"
    )
    filter_parts.append(
        f"[trimmed][darklayer]overlay=0:0[dark]"
    )

    # Build drawtext filter chain
    dt_parts: List[str] = []

    # Scripture reference — large italic text at top (shown during first 3 segments)
    safe_verse = _esc(verse)
    dt_parts.append(
        f"drawtext=fontfile='{_FONT_BOLD}'"
        f":text='{safe_verse}'"
        f":fontcolor=white@0.95:fontsize=58"
        f":borderw=4:bordercolor=black@0.85"
        f":x=(w-text_w)/2:y=h*0.07"
        f":enable='between(t,0,{verse_ref_end:.2f})'"
    )

    # Subtitle phrases — lower third
    for p in all_phrases:
        safe_text = _esc(p["text"])
        dt_parts.append(
            f"drawtext=fontfile='{_FONT_BOLD}'"
            f":text='{safe_text}'"
            f":fontcolor=white:fontsize=50"
            f":borderw=3:bordercolor=black@0.9"
            f":x=(w-text_w)/2:y=h*0.82"
            f":enable='between(t,{p['start']:.3f},{p['end']:.3f})'"
        )

    # Watermark — bottom right, always visible
    dt_parts.append(
        f"drawtext=fontfile='{_FONT_ITALIC}'"
        f":text='@Faith_Nexus'"
        f":fontcolor=white@0.8:fontsize=34"
        f":borderw=2:bordercolor=black@0.7"
        f":x=w-text_w-25:y=h-text_h-35"
    )

    filter_parts.append(f"[dark]{'[dark]'.join(dt_parts[0].split('[dark]'))}[vout]".replace(
        f"[dark]{dt_parts[0]}", f"[dark]{dt_parts[0]}"
    ))

    # Actually build the drawtext chain correctly:
    # [dark] → dt1 → dt2 → ... → [vout]
    filter_parts[-1] = f"[dark]{','.join(dt_parts)}[vout]"

    filter_complex = ";".join(filter_parts)

    cmd = (
        ["ffmpeg", "-y"]
        + input_args
        + [
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", f"{vo_idx}:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            "-t", f"{video_dur:.3f}",
            "-r", str(FPS),
            "-movflags", "+faststart",
            str(output_mp4),
        ]
    )

    print(f"   ffmpeg: {n_images} images → {video_dur:.1f}s video...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        print(f"\n   ffmpeg stderr (last 1000 chars):\n{result.stderr[-1000:]}")
        raise RuntimeError(f"ffmpeg failed (exit {result.returncode})")

    if not output_mp4.exists():
        raise RuntimeError("ffmpeg ran but output file missing")

    fsize = output_mp4.stat().st_size
    print(f"   Output: {output_mp4}")
    print(f"   Size  : {fsize//1024}KB ({fsize//(1024*1024)}MB)")
    print(f"   Duration: {video_dur:.1f}s")

    # ── 6. Upload to GDrive ───────────────────────────────────────────────────
    print(f"\n[6/6] Uploading to GDrive...")
    gdrive_folder = "gdrive:HumanAI/videos/christian/"
    r2 = subprocess.run(
        ["rclone", "copy", str(output_mp4), gdrive_folder],
        capture_output=True, text=True, timeout=300
    )
    gdrive_ok = r2.returncode == 0
    print(f"   GDrive: {'OK ✓' if gdrive_ok else 'FAILED — ' + r2.stderr[-100:]}")

    # ── Mirror to canonical christian/ folder ────────────────────────────────
    import shutil as _shutil
    christian_dir = _ROOT / "data" / "media_output" / "christian"
    christian_dir.mkdir(parents=True, exist_ok=True)
    christian_dest = christian_dir / output_mp4.name
    try:
        # Keep largest file if same name already exists (dedup by size)
        if christian_dest.exists():
            existing_size = christian_dest.stat().st_size
            if fsize > existing_size:
                _shutil.copy2(str(output_mp4), str(christian_dest))
                print(f"   christian/ updated (larger: {fsize//1024}KB > {existing_size//1024}KB)")
            else:
                print(f"   christian/ kept existing (already largest)")
        else:
            _shutil.copy2(str(output_mp4), str(christian_dest))
            print(f"   christian/ mirrored: {christian_dest.name}")
    except Exception as _e:
        print(f"   christian/ mirror failed: {_e}", file=sys.stderr)

    # ── Metadata ──────────────────────────────────────────────────────────────
    meta = {
        "verse": verse, "theme": theme, "text": text,
        "output_mp4": str(output_mp4), "output_dir": str(out_dir),
        "canonical_output": str(christian_dest),
        "duration_s": round(video_dur, 1),
        "file_size_kb": fsize // 1024,
        "subtitle_phrases": len(all_phrases),
        "images_used": len(img_paths),
        "gdrive_uploaded": gdrive_ok,
        "gdrive_folder": gdrive_folder,
        "produced_at": datetime.now().isoformat(),
    }
    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2))

    # ── Obsidian log ─────────────────────────────────────────────────────────
    obsidian_dir = _ROOT / "data" / "obsidian" / "sessions"
    obsidian_dir.mkdir(parents=True, exist_ok=True)
    obs_file = obsidian_dir / f"{datetime.now().strftime('%Y-%m-%d')}-automode.md"
    with open(obs_file, "a") as f:
        f.write(f"\n## FaithNexus Video Produced — {datetime.now().strftime('%H:%M UTC')}\n")
        f.write(f"- **Verse**: {verse} ({theme})\n")
        f.write(f"- **Duration**: {video_dur:.1f}s | **Size**: {fsize//1024}KB\n")
        f.write(f"- **Subtitles**: {len(all_phrases)} phrases | **Images**: {len(img_paths)}\n")
        f.write(f"- **GDrive**: {'uploaded ✓' if gdrive_ok else 'failed'}\n")
        f.write(f"- **Path**: `{output_mp4}`\n\n---\n")

    print(f"\n{'='*60}")
    print(f"  SUCCESS")
    print(f"  {verse} · {theme} · {video_dur:.1f}s · {fsize//1024}KB")
    print(f"  GDrive: {'uploaded ✓' if gdrive_ok else 'NOT uploaded'}")
    print(f"{'='*60}\n")
    return meta


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="FaithNexus autonomous biblical video producer")
    p.add_argument("--auto",   action="store_true")
    p.add_argument("--index",  type=int,  help="Scripture index 0-9")
    p.add_argument("--verse",  type=str)
    p.add_argument("--theme",  type=str)
    p.add_argument("--output", type=str)
    args = p.parse_args()

    if args.verse:
        scripture = next((s for s in SCRIPTURES if args.verse.lower() in s["verse"].lower()), None)
        if not scripture:
            print(f"Verse '{args.verse}' not found in library. Using auto-select.")
            scripture = SCRIPTURES[datetime.now().weekday() % len(SCRIPTURES)]
    elif args.index is not None:
        scripture = SCRIPTURES[args.index % len(SCRIPTURES)]
    else:
        scripture = SCRIPTURES[datetime.now().weekday() % len(SCRIPTURES)]

    out_dir = Path(args.output) if args.output else (_ROOT / "data" / "media_output" / "faithnexus")
    out_dir.mkdir(parents=True, exist_ok=True)

    meta = asyncio.run(produce_video(scripture, out_dir))
    return 0 if meta else 1


if __name__ == "__main__":
    sys.exit(main())
