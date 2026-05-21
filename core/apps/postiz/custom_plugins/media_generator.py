#!/usr/bin/env python3
"""
Multi-Platform Media Generator
Generates images and short videos/reels for TikTok and YouTube Shorts
using SiliconFlow API (image) and NVIDIA NIM (LLM captions/scripts)
"""

import json
import logging
import os
import time
import hashlib
import requests
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MEDIA_OUTPUT_DIR = Path(__file__).resolve().parents[3] / "data" / "media_output"
MEDIA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# SiliconFlow image generation models
SILICONFLOW_IMAGE_MODELS = {
    "fast": "black-forest-labs/FLUX.1-schnell",
    "quality": "black-forest-labs/FLUX.1-dev",
    "anime": "enhanceaiteam/Flux-Uncensored",
    "default": "black-forest-labs/FLUX.1-schnell",
}

# Platform-specific dimensions
PLATFORM_SPECS = {
    "tiktok": {"width": 1080, "height": 1920, "aspect": "9:16", "duration_sec": 15},
    "youtube_shorts": {"width": 1080, "height": 1920, "aspect": "9:16", "duration_sec": 60},
    "youtube_thumbnail": {"width": 1280, "height": 720, "aspect": "16:9", "duration_sec": 0},
    "instagram_reel": {"width": 1080, "height": 1920, "aspect": "9:16", "duration_sec": 30},
    "twitter": {"width": 1200, "height": 675, "aspect": "16:9", "duration_sec": 0},
}


class SiliconFlowImageGen:
    """Generate images via SiliconFlow API"""

    BASE_URL = "https://api.siliconflow.cn/v1"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("SILICONFLOW_API_KEY", "")
        if not self.api_key:
            logger.warning("SILICONFLOW_API_KEY not set - image generation unavailable")

    def generate(
        self,
        prompt: str,
        platform: str = "tiktok",
        model: str = "default",
        negative_prompt: str = "blurry, low quality, text, watermark",
    ) -> Optional[Dict]:
        """Generate image for platform dimensions"""
        if not self.api_key:
            return self._placeholder(prompt, platform)

        spec = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["tiktok"])
        model_id = SILICONFLOW_IMAGE_MODELS.get(model, SILICONFLOW_IMAGE_MODELS["default"])

        # SiliconFlow supports specific sizes; map to nearest supported
        supported_sizes = {
            "tiktok": "576x1024",
            "youtube_shorts": "576x1024",
            "instagram_reel": "576x1024",
            "youtube_thumbnail": "1024x576",
            "twitter": "1024x576",
        }
        image_size = supported_sizes.get(platform, "1024x1024")

        payload = {
            "model": model_id,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "image_size": image_size,
            "batch_size": 1,
            "num_inference_steps": 4,
        }

        try:
            resp = requests.post(
                f"{self.BASE_URL}/images/generations",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()

            image_url = (data.get("images") or data.get("data") or [{}])[0].get("url")
            if image_url:
                img_data = requests.get(image_url, timeout=30).content
                fname = self._save_image(img_data, prompt, platform)
                return {
                    "status": "success",
                    "file": str(fname),
                    "url": image_url,
                    "platform": platform,
                    "model": model_id,
                    "prompt": prompt,
                    "timestamp": datetime.now().isoformat(),
                }
        except Exception as e:
            logger.warning(f"SiliconFlow failed ({e}), falling back to Pollinations.ai")

        # Fallback: Pollinations.ai (completely free, no key)
        return self._pollinations_generate(prompt, platform)

    def _pollinations_generate(self, prompt: str, platform: str) -> Dict:
        """Free fallback via Pollinations.ai (no API key needed)"""
        from urllib.parse import quote
        spec = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["tiktok"])
        supported = {"tiktok": "576x1024", "youtube_shorts": "576x1024",
                     "instagram_reel": "576x1024", "youtube_thumbnail": "1024x576",
                     "twitter": "1024x576"}
        dims = supported.get(platform, "1024x1024").split("x")
        w, h = dims[0], dims[1]

        enhanced = f"{prompt}, professional finance content, high quality, sharp, 4k"
        url = f"https://image.pollinations.ai/prompt/{quote(enhanced)}?width={w}&height={h}&model=flux&nologo=true&seed={hash(prompt)%99999}"
        try:
            resp = requests.get(url, timeout=45)
            if resp.status_code == 200 and "image" in resp.headers.get("content-type", ""):
                path = self._save_image(resp.content, prompt, platform)
                return {"status": "success", "source": "pollinations", "file": str(path),
                        "url": url, "platform": platform, "prompt": prompt,
                        "timestamp": datetime.now().isoformat()}
        except Exception as e:
            logger.error(f"Pollinations fallback failed: {e}")

        return {"status": "placeholder", "platform": platform, "prompt": prompt,
                "note": "Both SiliconFlow and Pollinations failed", "timestamp": datetime.now().isoformat()}

    def _save_image(self, data: bytes, prompt: str, platform: str) -> Path:
        slug = hashlib.md5(prompt.encode()).hexdigest()[:8]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = MEDIA_OUTPUT_DIR / f"img_{platform}_{ts}_{slug}.jpg"
        path.write_bytes(data)
        logger.info(f"Image saved: {path} ({len(data)} bytes)")
        return path


class NVIDIAVideoScriptGen:
    """Generate video scripts/captions via NVIDIA NIM free API"""

    BASE_URL = "https://integrate.api.nvidia.com/v1"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY", "")

    def generate_script(self, topic: str, platform: str, duration_sec: int = 15) -> Dict:
        """Generate video script with hooks, captions, hashtags"""
        if not self.api_key:
            return self._fallback_script(topic, platform, duration_sec)

        prompt = f"""Return ONLY valid JSON (no explanation, no markdown) for a viral {platform} video script about: {topic}

Duration: {duration_sec} seconds. Output format:
{{"hook":"...","scenes":[{{"timestamp":"0-3s","visual":"...","caption":"..."}}],"cta":"...","hashtags":["#tag1","#tag2"],"voiceover":"..."}}"""

        try:
            resp = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "nvidia/nemotron-3-super-120b-a12b",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 1000,
                },
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]

            # Extract JSON from response
            try:
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    script = json.loads(content[start:end])
                else:
                    script = {"voiceover": content, "hashtags": [f"#{topic.replace(' ', '')}"], "hook": content[:50]}
            except json.JSONDecodeError:
                script = {"voiceover": content, "hashtags": [], "hook": content[:50]}

            script["platform"] = platform
            script["topic"] = topic
            script["timestamp"] = datetime.now().isoformat()
            return script

        except Exception as e:
            logger.error(f"NVIDIA script gen failed: {e}")
            return self._fallback_script(topic, platform, duration_sec)

    def _fallback_script(self, topic: str, platform: str, duration_sec: int) -> Dict:
        return {
            "hook": f"🔥 {topic} - You NEED to know this!",
            "scenes": [
                {"timestamp": "0-3s", "visual": "Eye-catching graphic", "caption": f"About {topic}"},
                {"timestamp": "3-10s", "visual": "Key information", "caption": "Here's what matters..."},
                {"timestamp": f"10-{duration_sec}s", "visual": "Call to action", "caption": "Follow for more!"},
            ],
            "cta": "Follow for daily trading insights!",
            "hashtags": [f"#{topic.replace(' ', '')}", "#trading", "#finance", "#investing", "#crypto"],
            "voiceover": f"Today we're talking about {topic}. This is what every trader needs to know...",
            "platform": platform,
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "note": "Fallback script - NVIDIA API key not configured",
        }


class VideoSlideGenerator:
    """
    Generates video content as image slide sequences for TikTok/YouTube Shorts.
    Creates multiple frames that can be assembled into a video.
    """

    def __init__(self, image_gen: SiliconFlowImageGen, script_gen: NVIDIAVideoScriptGen):
        self.image_gen = image_gen
        self.script_gen = script_gen

    def create_reel(self, topic: str, platform: str = "tiktok") -> Dict:
        """
        Create a complete reel/short video package:
        - Script with scenes
        - Cover image
        - Per-scene images
        - Metadata JSON
        """
        spec = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["tiktok"])
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        reel_dir = MEDIA_OUTPUT_DIR / f"reel_{platform}_{ts}"
        reel_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Creating {platform} reel about: {topic}")

        # Step 1: Generate script
        script = self.script_gen.generate_script(topic, platform, spec["duration_sec"])

        # Step 2: Generate cover image
        cover_prompt = f"Viral {platform} thumbnail, {topic}, professional financial content, bold text space, {spec['aspect']} aspect ratio"
        cover = self.image_gen.generate(cover_prompt, platform)

        # Step 3: Generate scene images (max 3 to avoid rate limits)
        scene_images = []
        for i, scene in enumerate(script.get("scenes", [])[:3]):
            visual_prompt = f"{scene.get('visual', topic)}, {platform} style, {spec['aspect']}, high quality"
            img = self.image_gen.generate(visual_prompt, platform)
            scene_images.append({"scene": i + 1, "caption": scene.get("caption", ""), "image": img})
            time.sleep(0.5)  # Rate limit courtesy pause

        # Step 4: Save reel package
        reel_meta = {
            "reel_id": f"reel_{platform}_{ts}",
            "platform": platform,
            "topic": topic,
            "spec": spec,
            "script": script,
            "cover_image": cover,
            "scenes": scene_images,
            "hashtags": script.get("hashtags", []),
            "hook": script.get("hook", ""),
            "cta": script.get("cta", ""),
            "created_at": datetime.now().isoformat(),
            "ready_to_publish": True,
        }

        meta_file = reel_dir / "reel_metadata.json"
        meta_file.write_text(json.dumps(reel_meta, indent=2, default=str))

        # Also save caption/script file
        caption_file = reel_dir / "caption.txt"
        caption = f"{script.get('hook', topic)}\n\n{script.get('voiceover', '')}\n\n{' '.join(script.get('hashtags', []))}"
        caption_file.write_text(caption)

        logger.info(f"Reel package created: {reel_dir}")
        return reel_meta


class PixabayMediaFetcher:
    """Fetch royalty-free photos and videos via Pixabay API"""

    BASE_URL = "https://pixabay.com/api"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("PIXABAY_API_KEY", "")

    def search_photos(self, query: str, per_page: int = 5) -> List[Dict]:
        if not self.api_key: return []
        try:
            r = requests.get(f"{self.BASE_URL}/", params={"key": self.api_key, "q": query,
                "per_page": per_page, "orientation": "vertical", "safesearch": "true"}, timeout=10)
            if r.status_code == 200:
                return [{"id": h["id"], "url": h.get("largeImageURL", h.get("webformatURL")),
                         "thumb": h.get("webformatURL"), "tags": h.get("tags")} for h in r.json().get("hits", [])]
        except Exception as e:
            logger.warning(f"Pixabay photo search failed: {e}")
        return []

    def search_videos(self, query: str, per_page: int = 3) -> List[Dict]:
        if not self.api_key: return []
        try:
            r = requests.get(f"{self.BASE_URL}/videos/", params={"key": self.api_key, "q": query,
                "per_page": per_page, "video_type": "film"}, timeout=10)
            if r.status_code == 200:
                results = []
                for v in r.json().get("hits", []):
                    vids = v.get("videos", {})
                    best = vids.get("large") or vids.get("medium") or {}
                    results.append({"id": v["id"], "duration": v.get("duration"),
                                   "url": best.get("url", ""), "tags": v.get("tags")})
                return results
        except Exception as e:
            logger.warning(f"Pixabay video search failed: {e}")
        return []


class PexelsMediaFetcher:
    """Fetch royalty-free photos and video clips via Pexels API"""

    BASE_URL = "https://api.pexels.com"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("PEXELS_API_KEY", "")

    def search_photos(self, query: str, per_page: int = 5) -> List[Dict]:
        if not self.api_key:
            return []
        try:
            r = requests.get(f"{self.BASE_URL}/v1/search",
                           params={"query": query, "per_page": per_page, "orientation": "portrait"},
                           headers={"Authorization": self.api_key}, timeout=10)
            if r.status_code == 200:
                return [{"id": p["id"], "url": p["src"]["large"], "thumb": p["src"]["medium"],
                         "photographer": p["photographer"]} for p in r.json().get("photos", [])]
        except Exception as e:
            logger.warning(f"Pexels photo search failed: {e}")
        return []

    def search_videos(self, query: str, per_page: int = 3) -> List[Dict]:
        if not self.api_key:
            return []
        try:
            r = requests.get(f"{self.BASE_URL}/videos/search",
                           params={"query": query, "per_page": per_page, "orientation": "portrait"},
                           headers={"Authorization": self.api_key}, timeout=10)
            if r.status_code == 200:
                results = []
                for v in r.json().get("videos", []):
                    # Get best quality portrait video file
                    files = sorted(v.get("video_files", []),
                                  key=lambda f: f.get("height", 0), reverse=True)
                    portrait = [f for f in files if f.get("height", 0) >= f.get("width", 1)]
                    best = portrait[0] if portrait else (files[0] if files else {})
                    results.append({
                        "id": v["id"], "duration": v.get("duration"),
                        "url": best.get("link", ""), "width": best.get("width"),
                        "height": best.get("height"),
                    })
                return results
        except Exception as e:
            logger.warning(f"Pexels video search failed: {e}")
        return []

    def download_video_clip(self, video_url: str, output_dir: Path) -> Optional[Path]:
        if not video_url:
            return None
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = output_dir / f"clip_{ts}.mp4"
            r = requests.get(video_url, timeout=60, stream=True)
            if r.status_code == 200:
                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        f.write(chunk)
                logger.info(f"Video clip saved: {path} ({path.stat().st_size // 1024}KB)")
                return path
        except Exception as e:
            logger.error(f"Video download failed: {e}")
        return None


class MediaGenerationPipeline:
    """
    Unified pipeline: topic → script → images → Pexels video clips → reel package
    Sources: SiliconFlow (primary) → Pollinations.ai (fallback) → Pexels (stock)
    """

    def __init__(self):
        self.image_gen = SiliconFlowImageGen()
        self.script_gen = NVIDIAVideoScriptGen()
        self.video_gen = VideoSlideGenerator(self.image_gen, self.script_gen)
        self.pexels = PexelsMediaFetcher()
        self.pixabay = PixabayMediaFetcher()

    def generate_for_platform(self, topic: str, platforms: List[str] = None) -> Dict:
        """Generate media assets for one or more platforms"""
        if platforms is None:
            platforms = ["tiktok", "youtube_shorts"]

        # Fetch stock media from both Pexels and Pixabay
        search_terms = topic.replace("$", "").replace(":", "").split("-")[0].strip()[:50]
        pexels_photos = self.pexels.search_photos(search_terms, per_page=3)
        pexels_videos = self.pexels.search_videos(search_terms, per_page=2)
        # Merge Pixabay as additional source
        pexels_photos += self.pixabay.search_photos(search_terms, per_page=2)
        if not pexels_videos:
            pexels_videos = self.pixabay.search_videos(search_terms, per_page=2)

        results = {}
        for platform in platforms:
            logger.info(f"Generating content for {platform}: {topic}")
            if platform in ("tiktok", "youtube_shorts", "instagram_reel"):
                reel = self.video_gen.create_reel(topic, platform)
                # Attach Pexels clips if available
                reel["pexels_stock_photos"] = pexels_photos
                reel["pexels_stock_videos"] = pexels_videos
                if pexels_videos and platform == "tiktok":
                    clip_dir = MEDIA_OUTPUT_DIR / f"reel_{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    clip_dir.mkdir(exist_ok=True)
                    dl = self.pexels.download_video_clip(pexels_videos[0].get("url", ""), clip_dir)
                    if dl:
                        reel["downloaded_clip"] = str(dl)
                results[platform] = reel
            else:
                prompt = f"{topic}, professional financial content, {PLATFORM_SPECS.get(platform, {}).get('aspect', '16:9')}"
                results[platform] = {
                    "platform": platform,
                    "topic": topic,
                    "image": self.image_gen.generate(prompt, platform),
                    "script": self.script_gen.generate_script(topic, platform, 0),
                    "pexels_photos": pexels_photos,
                    "timestamp": datetime.now().isoformat(),
                }

        return {
            "topic": topic,
            "platforms": results,
            "generated_at": datetime.now().isoformat(),
            "output_dir": str(MEDIA_OUTPUT_DIR),
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate social media content")
    parser.add_argument("--topic", default="Gold trading signals for today", help="Content topic")
    parser.add_argument("--platforms", nargs="+", default=["tiktok", "youtube_shorts"])
    args = parser.parse_args()

    pipeline = MediaGenerationPipeline()
    result = pipeline.generate_for_platform(args.topic, args.platforms)
    print(json.dumps(result, indent=2, default=str))
