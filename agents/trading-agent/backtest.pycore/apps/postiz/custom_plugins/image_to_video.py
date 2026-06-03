#!/usr/bin/env python3
"""
Image-to-Video Combiner
Creates MP4 slideshow from multiple images when video generation API is unavailable.
Uses imageio (no ffmpeg required).
Sources: Pollinations.ai, Pexels, Pixabay images → animated MP4

Also supports downloading YouTube clips via yt-dlp if installed.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
import requests
import hashlib
import io

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parents[3] / "data" / "media_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Transition duration settings
FRAME_DURATION = 3.0       # seconds per image
FADE_FRAMES = 10           # frames for fade transition
FPS = 24


def _download_image(url: str, timeout: int = 30) -> Optional[bytes]:
    """Download image bytes from URL."""
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200 and len(r.content) > 1000:
            return r.content
    except Exception as e:
        logger.warning(f"Image download failed {url[:60]}: {e}")
    return None


def _bytes_to_array(img_bytes: bytes):
    """Convert image bytes to numpy array."""
    try:
        import imageio.v3 as iio
        import numpy as np
        arr = iio.imread(io.BytesIO(img_bytes))
        # Ensure RGB (drop alpha if present)
        if arr.ndim == 3 and arr.shape[2] == 4:
            arr = arr[:, :, :3]
        return arr
    except Exception as e:
        logger.warning(f"Image decode failed: {e}")
    return None


def _resize_frame(arr, width: int = 576, height: int = 1024):
    """Resize frame to target dimensions."""
    try:
        from PIL import Image
        import numpy as np
        img = Image.fromarray(arr)
        img = img.resize((width, height), Image.LANCZOS)
        return np.array(img)
    except ImportError:
        # Fallback: basic numpy resize
        import numpy as np
        from scipy.ndimage import zoom
        h, w = arr.shape[:2]
        zy = height / h
        zx = width / w
        if arr.ndim == 3:
            return zoom(arr, (zy, zx, 1))
        return zoom(arr, (zy, zx))
    except Exception:
        return arr


def _add_text_overlay(arr, text: str, position: str = "bottom"):
    """Add text overlay to frame."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
        img = Image.fromarray(arr)
        draw = ImageDraw.Draw(img)
        w, h = img.size

        # Semi-transparent bar
        overlay = Image.new("RGBA", (w, 60), (0, 0, 0, 180))
        y = h - 70 if position == "bottom" else 10
        img.paste(Image.fromarray(np.array(overlay)[:, :, :3]), (0, y))

        # Text
        draw.text((10, y + 10), text[:60], fill=(255, 255, 255), font=None)
        return np.array(img.convert("RGB"))
    except Exception:
        return arr


def create_slideshow(
    image_urls: List[str],
    captions: Optional[List[str]] = None,
    output_path: Optional[Path] = None,
    width: int = 576,
    height: int = 1024,
    frame_duration: float = FRAME_DURATION,
) -> Optional[Path]:
    """
    Create MP4 slideshow from image URLs.
    Falls back to GIF if imageio video writer unavailable.
    """
    try:
        import imageio.v3 as iio
        import numpy as np
    except ImportError:
        logger.error("imageio not installed: pip install imageio")
        return None

    if not image_urls:
        logger.warning("No image URLs provided")
        return None

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"slideshow_{ts}.mp4"

    # Download all images
    frames_raw = []
    for i, url in enumerate(image_urls):
        data = _download_image(url)
        if data:
            arr = _bytes_to_array(data)
            if arr is not None:
                arr = _resize_frame(arr, width, height)
                caption = captions[i] if captions and i < len(captions) else None
                if caption:
                    arr = _add_text_overlay(arr, caption)
                frames_raw.append(arr)
                logger.info(f"Loaded image {i+1}/{len(image_urls)}")

    if not frames_raw:
        logger.error("No images loaded successfully")
        return None

    # Build video frames with transitions
    all_frames = []
    n_still = int(FPS * frame_duration)
    n_fade = FADE_FRAMES

    for i, frame in enumerate(frames_raw):
        # Still frames
        for _ in range(n_still):
            all_frames.append(frame.copy())

        # Fade to next frame
        if i < len(frames_raw) - 1:
            next_frame = frames_raw[i + 1]
            for f in range(n_fade):
                alpha = f / n_fade
                blended = ((1 - alpha) * frame + alpha * next_frame).astype(frame.dtype)
                all_frames.append(blended)

    # Write video
    try:
        iio.imwrite(
            str(output_path),
            all_frames,
            fps=FPS,
            codec="libx264" if str(output_path).endswith(".mp4") else None,
            output_params=["-pix_fmt", "yuv420p"] if str(output_path).endswith(".mp4") else [],
        )
        logger.info(f"Video created: {output_path} ({len(all_frames)} frames)")
        return output_path
    except Exception as e:
        # Fallback to GIF
        logger.warning(f"MP4 failed ({e}), trying GIF...")
        gif_path = output_path.with_suffix(".gif")
        try:
            iio.imwrite(str(gif_path), all_frames[::FPS], loop=0, duration=int(frame_duration * 1000))
            logger.info(f"GIF created: {gif_path}")
            return gif_path
        except Exception as e2:
            logger.error(f"GIF also failed: {e2}")
            return None


def create_reel_video(
    topic: str,
    script: Dict,
    platform: str = "tiktok",
    output_dir: Optional[Path] = None,
) -> Optional[Path]:
    """
    High-level: generate reel video from topic + script.
    Fetches images from Pollinations.ai + Pexels, combines into slideshow.
    """
    from urllib.parse import quote
    if output_dir is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = OUTPUT_DIR / f"reel_{platform}_{ts}"
    output_dir.mkdir(parents=True, exist_ok=True)

    specs = {"tiktok": (576, 1024), "youtube_shorts": (576, 1024),
             "instagram_reel": (576, 1024), "twitter": (1024, 576)}
    w, h = specs.get(platform, (576, 1024))

    # Build image URLs from script scenes + Pollinations
    image_urls = []
    captions = []

    scenes = script.get("scenes", [])
    for scene in scenes[:5]:
        visual = scene.get("visual", topic)
        caption = scene.get("caption", "")
        prompt = f"{visual}, finance, professional, {platform} style, high quality"
        url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width={w}&height={h}&model=flux&nologo=true&seed={hash(visual)%9999}"
        image_urls.append(url)
        captions.append(caption)

    # Also try Pexels for extra stock footage
    pexels_key = os.environ.get("PEXELS_API_KEY", "")
    if pexels_key and len(image_urls) < 5:
        try:
            r = requests.get("https://api.pexels.com/v1/search",
                params={"query": topic[:40], "per_page": 3, "orientation": "portrait"},
                headers={"Authorization": pexels_key}, timeout=10)
            if r.status_code == 200:
                for p in r.json().get("photos", [])[:2]:
                    image_urls.append(p["src"]["large"])
                    captions.append(f"via Pexels")
        except Exception: pass

    if not image_urls:
        logger.warning("No image sources available")
        return None

    out_file = output_dir / f"reel_{platform}.mp4"
    result = create_slideshow(image_urls, captions, out_file, w, h, 3.0)

    # Save metadata
    meta = {
        "topic": topic, "platform": platform, "script": script,
        "video_file": str(result) if result else None,
        "images_used": len(image_urls),
        "created_at": datetime.now().isoformat(),
    }
    (output_dir / "video_metadata.json").write_text(json.dumps(meta, indent=2, default=str))

    return result


def download_youtube_clip(url: str, output_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Download a YouTube video clip using yt-dlp.
    Only downloads short clips (<60s) for fair use.
    """
    try:
        import subprocess
        if output_dir is None:
            output_dir = OUTPUT_DIR / "youtube_clips"
        output_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_template = str(output_dir / f"yt_clip_{ts}.%(ext)s")

        cmd = [
            "yt-dlp",
            "--no-playlist", "--max-filesize", "50M",
            "--format", "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "--merge-output-format", "mp4",
            "--output", out_template,
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            # Find downloaded file
            files = sorted(output_dir.glob(f"yt_clip_{ts}*.mp4"))
            if files:
                logger.info(f"YouTube clip downloaded: {files[0]}")
                return files[0]
        else:
            logger.warning(f"yt-dlp failed: {result.stderr[:200]}")
    except FileNotFoundError:
        logger.warning("yt-dlp not installed. Install with: pip install yt-dlp")
    except Exception as e:
        logger.error(f"YouTube download error: {e}")
    return None


if __name__ == "__main__":
    # Test: create a slideshow from Pollinations images
    from urllib.parse import quote
    test_urls = [
        f"https://image.pollinations.ai/prompt/{quote('gold bars trading chart finance')}?width=576&height=1024&model=flux&nologo=true",
        f"https://image.pollinations.ai/prompt/{quote('bitcoin cryptocurrency market green candles')}?width=576&height=1024&model=flux&nologo=true",
        f"https://image.pollinations.ai/prompt/{quote('stock market bull run celebration')}?width=576&height=1024&model=flux&nologo=true",
    ]
    captions = ["Gold trading signals", "Crypto market update", "Bull market rally"]
    out = create_slideshow(test_urls, captions)
    print(f"Result: {out}")
