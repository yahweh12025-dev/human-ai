#!/usr/bin/env python3
"""
Content Pipeline
Takes topic/theme inputs, generates platform-optimized content via LLM,
creates content calendar entries, and queues posts for Postiz publishing.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests

logger = logging.getLogger(__name__)

# Platform-specific generation parameters
PLATFORM_CONFIGS = {
    "twitter": {
        "max_chars": 280,
        "format": "short_form",
        "hashtag_style": "inline",
        "max_hashtags": 3,
        "cta_style": "none_or_subtle",
        "media_preference": "optional",
    },
    "instagram": {
        "max_chars": 2200,
        "format": "story_format",
        "hashtag_style": "block_at_end",
        "max_hashtags": 20,
        "cta_style": "strong_cta",
        "media_preference": "required",
    },
    "youtube": {
        "max_chars": 5000,
        "format": "description",
        "hashtag_style": "seo_tags",
        "max_hashtags": 15,
        "cta_style": "subscribe_cta",
        "media_preference": "thumbnail",
    },
    "tiktok": {
        "max_chars": 2200,
        "format": "hook_first",
        "hashtag_style": "trending",
        "max_hashtags": 8,
        "cta_style": "engagement",
        "media_preference": "required",
    },
}


class ContentPipeline:
    """
    End-to-end content pipeline from topic to published post.
    Generates platform-optimized content, manages calendar entries,
    and queues posts for Postiz publishing.
    """

    def __init__(
        self,
        openrouter_api_key: Optional[str] = None,
        postiz_connector=None,
        project_root: Optional[str] = None,
    ):
        """
        Initialize the Content Pipeline.

        Args:
            openrouter_api_key: API key for OpenRouter LLM access.
            postiz_connector: PostizConnector instance for publishing.
            project_root: Project root directory path.
        """
        self.openrouter_api_key = openrouter_api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.postiz = postiz_connector
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parent.parent

        # Pipeline state
        self._queue: List[Dict[str, Any]] = []
        self._calendar: List[Dict[str, Any]] = []
        self._generation_history: List[Dict[str, Any]] = []

        # Queue persistence file
        self._queue_file = self.project_root / "data" / "social_post_queue.json"
        self._calendar_file = self.project_root / "data" / "social_content_calendar.json"

        # Ensure data directory exists
        self._queue_file.parent.mkdir(parents=True, exist_ok=True)

        # Load persisted queue if exists
        self._load_persisted_state()

        logger.info("ContentPipeline initialized")

    # ------------------------------------------------------------------
    # State Persistence
    # ------------------------------------------------------------------

    def _load_persisted_state(self):
        """Load persisted queue and calendar from disk."""
        try:
            if self._queue_file.exists():
                with open(self._queue_file, "r") as f:
                    data = json.load(f)
                self._queue = data.get("queue", [])
                logger.info(f"Loaded {len(self._queue)} queued posts from disk")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load queue state: {e}")
            self._queue = []

        try:
            if self._calendar_file.exists():
                with open(self._calendar_file, "r") as f:
                    data = json.load(f)
                self._calendar = data.get("calendar", [])
                logger.info(f"Loaded {len(self._calendar)} calendar entries from disk")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load calendar state: {e}")
            self._calendar = []

    def _persist_state(self):
        """Persist current queue and calendar to disk."""
        try:
            with open(self._queue_file, "w") as f:
                json.dump(
                    {"queue": self._queue, "last_updated": datetime.now().isoformat()},
                    f,
                    indent=2,
                )
            with open(self._calendar_file, "w") as f:
                json.dump(
                    {"calendar": self._calendar, "last_updated": datetime.now().isoformat()},
                    f,
                    indent=2,
                )
        except IOError as e:
            logger.error(f"Failed to persist pipeline state: {e}")

    # ------------------------------------------------------------------
    # Content Generation
    # ------------------------------------------------------------------

    def generate_for_platform(
        self,
        topic: str,
        platform: str,
        style: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate content optimized for a specific platform.

        Args:
            topic: The content topic or theme.
            platform: Target platform (twitter, instagram, youtube, tiktok).
            style: Optional style override.
            additional_context: Extra context for generation.

        Returns:
            Dictionary with generated content and metadata.
        """
        if platform not in PLATFORM_CONFIGS:
            raise ValueError(f"Unsupported platform: {platform}")

        config = PLATFORM_CONFIGS[platform]
        content_text = self._call_llm(topic, platform, config, style, additional_context)

        result = {
            "id": f"content_{platform}_{int(time.time())}",
            "topic": topic,
            "platform": platform,
            "content": content_text,
            "char_count": len(content_text),
            "max_chars": config["max_chars"],
            "generated_at": datetime.now().isoformat(),
            "status": "generated",
        }

        self._generation_history.append(result)
        logger.info(f"Generated {platform} content: {len(content_text)} chars")
        return result

    def generate_multi_platform(
        self,
        topic: str,
        platforms: Optional[List[str]] = None,
        style: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate content for multiple platforms from a single topic.

        Args:
            topic: Content topic.
            platforms: Target platforms. Defaults to all.
            additional_context: Extra context.

        Returns:
            List of generated content dictionaries, one per platform.
        """
        platforms = platforms or list(PLATFORM_CONFIGS.keys())
        results = []

        for platform in platforms:
            try:
                result = self.generate_for_platform(
                    topic=topic,
                    platform=platform,
                    style=style,
                    additional_context=additional_context,
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Generation failed for {platform}: {e}")
                results.append({
                    "platform": platform,
                    "topic": topic,
                    "status": "error",
                    "error": str(e),
                    "generated_at": datetime.now().isoformat(),
                })

        return results

    def _call_llm(
        self,
        topic: str,
        platform: str,
        config: Dict[str, Any],
        style: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Call OpenRouter LLM API to generate platform-optimized content.

        Args:
            topic: Content topic.
            platform: Target platform.
            config: Platform configuration.
            style: Style override.
            additional_context: Extra generation context.

        Returns:
            Generated content string.
        """
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")

        max_chars = config["max_chars"]
        format_type = config["format"]
        hashtag_style = config["hashtag_style"]
        max_hashtags = config["max_hashtags"]
        cta_style = config["cta_style"]

        system_prompt = (
            "You are a professional social media content creator specializing in trading, "
            "crypto, and financial markets content. You create authentic, engaging posts that "
            "feel native to each platform. Never fabricate specific data points - use general "
            "language when you don't have real numbers. Match the platform culture exactly."
        )

        user_prompt = self._build_generation_prompt(
            topic=topic,
            platform=platform,
            max_chars=max_chars,
            format_type=format_type,
            hashtag_style=hashtag_style,
            max_hashtags=max_hashtags,
            cta_style=cta_style,
            style=style,
            additional_context=additional_context,
        )

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://human-ai.trading",
                    "X-Title": "Human-AI Content Pipeline",
                },
                json={
                    "model": "anthropic/claude-sonnet-4-20250514",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 1024,
                    "temperature": 0.85,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Enforce character limit
            if len(content) > max_chars:
                # Try to truncate at a natural break point
                truncated = content[:max_chars]
                last_newline = truncated.rfind("\n")
                last_period = truncated.rfind(".")
                last_space = truncated.rfind(" ")

                # Pick best truncation point
                cut_point = max(last_newline, last_period, last_space)
                if cut_point > max_chars * 0.7:
                    content = truncated[:cut_point + 1].rstrip()
                else:
                    content = truncated[:max_chars - 3] + "..."

                logger.warning(f"Truncated {platform} content from {len(data['choices'][0]['message']['content'])} to {len(content)} chars")

            return content

        except requests.exceptions.Timeout:
            logger.error("OpenRouter API timeout")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter API error: {e}")
            raise
        except (KeyError, IndexError) as e:
            logger.error(f"Invalid OpenRouter response structure: {e}")
            raise ValueError(f"Bad LLM response: {e}")

    def _build_generation_prompt(
        self,
        topic: str,
        platform: str,
        max_chars: int,
        format_type: str,
        hashtag_style: str,
        max_hashtags: int,
        cta_style: str,
        style: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the generation prompt for the LLM."""
        prompt_parts = [
            f"Create a {platform.upper()} post about: {topic}",
            "",
            "FORMAT REQUIREMENTS:",
            f"- Maximum {max_chars} characters total",
            f"- Content format: {format_type}",
            f"- Hashtag style: {hashtag_style}",
            f"- Maximum hashtags: {max_hashtags}",
            f"- Call-to-action style: {cta_style}",
        ]

        if style:
            prompt_parts.append(f"- Custom style: {style}")

        # Platform-specific instructions
        if platform == "twitter":
            prompt_parts.extend([
                "",
                "TWITTER RULES:",
                "- Be concise and punchy",
                "- Use 1-3 hashtags maximum, integrated naturally",
                "- Aim for under 240 chars to allow quote-tweet space",
                "- Thread hooks are powerful: make people want to engage",
                "- Use line breaks for readability",
            ])
        elif platform == "instagram":
            prompt_parts.extend([
                "",
                "INSTAGRAM RULES:",
                "- Start with an attention-grabbing first line (this shows in feed)",
                "- Use line breaks and emojis for visual structure",
                "- Tell a micro-story or share a valuable insight",
                "- End with a clear call-to-action (save, share, comment, follow)",
                "- Place hashtags after two line breaks at the end",
                "- Mix popular and niche hashtags",
            ])
        elif platform == "youtube":
            prompt_parts.extend([
                "",
                "YOUTUBE RULES:",
                "- Write a compelling video description",
                "- First 2 lines are crucial (shown before 'Show more')",
                "- Include natural SEO keywords",
                "- Add a timestamps section placeholder: [TIMESTAMPS]",
                "- Include subscribe CTA and social links placeholder",
                "- End with relevant tags/hashtags",
            ])
        elif platform == "tiktok":
            prompt_parts.extend([
                "",
                "TIKTOK RULES:",
                "- Hook in the first line (captures scroll attention)",
                "- Ultra casual, conversational tone",
                "- Use trending language and references",
                "- Keep it short and impactful",
                "- Add 3-5 trending/relevant hashtags",
                "- Include a POV or 'storytime' angle if appropriate",
            ])

        if additional_context:
            prompt_parts.extend([
                "",
                f"ADDITIONAL CONTEXT: {json.dumps(additional_context)}",
            ])

        prompt_parts.extend([
            "",
            "OUTPUT: Return ONLY the final post content. No explanations, no markdown, no labels.",
        ])

        return "\n".join(prompt_parts)

    # ------------------------------------------------------------------
    # Content Calendar
    # ------------------------------------------------------------------

    def generate_content_calendar(
        self,
        days_ahead: int = 7,
        platforms: Optional[List[str]] = None,
        topic_manager=None,
        posts_per_day: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Generate a full content calendar for future publishing.

        Args:
            days_ahead: Number of days to plan.
            platforms: Target platforms per entry.
            topic_manager: TopicManager instance for topic selection.
            posts_per_day: Number of posts per day to plan.

        Returns:
            List of calendar entry dictionaries.
        """
        platforms = platforms or list(PLATFORM_CONFIGS.keys())
        calendar = []
        now = datetime.now()

        for day_offset in range(days_ahead):
            target_date = now + timedelta(days=day_offset)
            day_of_week = target_date.weekday()

            # Adjust posts per day based on day type
            day_posts = posts_per_day
            if day_of_week in (5, 6):  # Weekend
                day_posts = max(1, posts_per_day - 1)
            elif day_of_week == 0:  # Monday - start of week
                day_posts = posts_per_day + 1

            # Optimal posting hours per platform
            posting_hours = {
                "twitter": [9, 12, 17],
                "instagram": [8, 11, 19],
                "youtube": [10, 14, 18],
                "tiktok": [7, 12, 19, 22],
            }

            for post_idx in range(day_posts):
                # Select topic
                if topic_manager:
                    topic_data = topic_manager.select_topic()
                    topic = topic_data.get("title", "Market Update")
                    category = topic_data.get("category")
                    if hasattr(category, "value"):
                        category = category.value
                else:
                    topic = "Daily Market Update"
                    category = "market_analysis"

                # Distribute across platforms round-robin style
                platform = platforms[post_idx % len(platforms)]

                # Pick optimal hour
                available_hours = posting_hours.get(platform, [9, 12, 17])
                hour = available_hours[post_idx % len(available_hours)]

                scheduled_time = target_date.replace(
                    hour=hour, minute=0, second=0, microsecond=0
                )

                # Skip past times
                if scheduled_time <= now:
                    continue

                entry = {
                    "id": f"cal_{target_date.strftime('%Y%m%d')}_{post_idx}_{platform}",
                    "topic": topic,
                    "category": category,
                    "platform": platform,
                    "scheduled_time": scheduled_time.isoformat(),
                    "status": "planned",
                    "created_at": now.isoformat(),
                    "content": None,  # Generated on demand or pre-generated
                }

                calendar.append(entry)

        self._calendar = calendar
        self._persist_state()

        logger.info(f"Generated content calendar: {len(calendar)} entries over {days_ahead} days")
        return calendar

    def pre_generate_calendar_content(
        self, calendar: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Pre-generate content for all calendar entries.
        Useful for review before publishing.

        Args:
            calendar: Calendar entries to generate for. Uses internal calendar if None.

        Returns:
            Calendar entries with generated content populated.
        """
        calendar = calendar or self._calendar
        generated = []

        for entry in calendar:
            if entry.get("content"):
                generated.append(entry)
                continue

            try:
                result = self.generate_for_platform(
                    topic=entry["topic"],
                    platform=entry["platform"],
                )
                entry["content"] = result["content"]
                entry["status"] = "content_ready"
                generated.append(entry)
            except Exception as e:
                logger.error(f"Pre-generation failed for {entry['id']}: {e}")
                entry["status"] = "generation_failed"
                entry["error"] = str(e)
                generated.append(entry)

        self._calendar = generated
        self._persist_state()
        return generated

    # ------------------------------------------------------------------
    # Post Queue Management
    # ------------------------------------------------------------------

    def add_to_queue(
        self,
        content: str,
        platform: str,
        scheduled_time: Optional[datetime] = None,
        topic: Optional[str] = None,
        priority: str = "medium",
    ) -> Dict[str, Any]:
        """
        Add a post to the publishing queue.

        Args:
            content: Post content text.
            platform: Target platform.
            scheduled_time: When to publish.
            topic: Original topic for reference.
            priority: Post priority (low, medium, high).

        Returns:
            Queue entry dictionary.
        """
        entry = {
            "id": f"queue_{platform}_{int(time.time())}",
            "content": content,
            "platform": platform,
            "topic": topic,
            "priority": priority,
            "scheduled_time": scheduled_time.isoformat() if scheduled_time else None,
            "queued_at": datetime.now().isoformat(),
            "status": "queued",
        }

        self._queue.append(entry)
        self._persist_state()

        logger.info(f"Added to queue: {entry['id']} ({platform})")
        return entry

    def process_queue(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Process queued posts - publish those that are due.

        Args:
            limit: Maximum number of posts to process in one batch.

        Returns:
            List of processed entries with results.
        """
        if not self.postiz:
            logger.error("No PostizConnector configured - cannot process queue")
            return []

        now = datetime.now()
        results = []
        processed_count = 0

        # Sort by priority then time
        priority_map = {"high": 0, "medium": 1, "low": 2}
        ready_posts = [
            p for p in self._queue
            if p["status"] == "queued"
            and (
                p["scheduled_time"] is None
                or datetime.fromisoformat(p["scheduled_time"]) <= now
            )
        ]
        ready_posts.sort(key=lambda p: (priority_map.get(p["priority"], 1), p["queued_at"]))

        for post in ready_posts[:limit]:
            try:
                result = self.postiz.publish_content(
                    content=post["content"],
                    platforms=[post["platform"]],
                    scheduled_time=None,  # Publish immediately (already due)
                )
                post["status"] = "published"
                post["published_at"] = datetime.now().isoformat()
                post["postiz_response"] = result
                results.append(post)
                processed_count += 1
                logger.info(f"Published from queue: {post['id']}")

            except Exception as e:
                post["status"] = "failed"
                post["error"] = str(e)
                post["failed_at"] = datetime.now().isoformat()
                results.append(post)
                logger.error(f"Queue publish failed for {post['id']}: {e}")

        # Remove published/failed items from active queue
        self._queue = [p for p in self._queue if p["status"] == "queued"]
        self._persist_state()

        logger.info(f"Processed {processed_count}/{len(ready_posts)} queued posts")
        return results

    def queue_to_postiz(self, calendar: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Push calendar entries to Postiz for batch scheduling.

        Args:
            calendar: Calendar entries (must have content populated).

        Returns:
            Batch scheduling result from Postiz.
        """
        if not self.postiz:
            raise ValueError("PostizConnector not configured")

        # Filter entries that have content ready
        ready_entries = [
            e for e in calendar
            if e.get("content") and e.get("status") in ("content_ready", "planned")
        ]

        if not ready_entries:
            logger.warning("No entries with content ready for Postiz scheduling")
            return {"status": "empty", "scheduled": 0}

        # Format for Postiz batch API
        batch_posts = []
        for entry in ready_entries:
            post_data = {
                "content": entry["content"],
                "platforms": [entry["platform"]],
                "scheduled_at": entry.get("scheduled_time"),
            }
            batch_posts.append(post_data)

        try:
            result = self.postiz.schedule_content_calendar(batch_posts)
            # Update entry statuses
            for entry in ready_entries:
                entry["status"] = "scheduled_in_postiz"
                entry["pushed_at"] = datetime.now().isoformat()

            self._persist_state()
            logger.info(f"Pushed {len(batch_posts)} entries to Postiz batch schedule")
            return {"status": "success", "scheduled": len(batch_posts), "postiz_response": result}

        except Exception as e:
            logger.error(f"Postiz batch scheduling failed: {e}")
            return {"status": "error", "error": str(e), "scheduled": 0}

    # ------------------------------------------------------------------
    # Pipeline Orchestration
    # ------------------------------------------------------------------

    def run_full_pipeline(
        self,
        topic: str,
        platforms: Optional[List[str]] = None,
        publish_immediately: bool = False,
        scheduled_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Run the complete pipeline: generate -> queue -> optionally publish.

        Args:
            topic: Content topic.
            platforms: Target platforms.
            publish_immediately: If True, publish now instead of queuing.
            scheduled_time: Schedule for future publishing.

        Returns:
            Pipeline execution result.
        """
        platforms = platforms or list(PLATFORM_CONFIGS.keys())
        results = {"topic": topic, "platforms": {}, "timestamp": datetime.now().isoformat()}

        for platform in platforms:
            try:
                # Generate
                generated = self.generate_for_platform(topic=topic, platform=platform)
                content = generated["content"]

                if publish_immediately and self.postiz:
                    # Publish directly
                    pub_result = self.postiz.publish_content(
                        content=content,
                        platforms=[platform],
                    )
                    results["platforms"][platform] = {
                        "status": "published",
                        "content": content,
                        "result": pub_result,
                    }
                else:
                    # Add to queue
                    queue_entry = self.add_to_queue(
                        content=content,
                        platform=platform,
                        scheduled_time=scheduled_time,
                        topic=topic,
                    )
                    results["platforms"][platform] = {
                        "status": "queued",
                        "content": content,
                        "queue_id": queue_entry["id"],
                    }

            except Exception as e:
                logger.error(f"Pipeline failed for {platform}: {e}")
                results["platforms"][platform] = {"status": "error", "error": str(e)}

        return results

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "queue_size": len(self._queue),
            "calendar_entries": len(self._calendar),
            "generation_count": len(self._generation_history),
            "queued_by_platform": self._count_by_platform(self._queue),
            "calendar_by_platform": self._count_by_platform(self._calendar),
            "last_updated": datetime.now().isoformat(),
        }

    def _count_by_platform(self, items: List[Dict]) -> Dict[str, int]:
        """Count items by platform."""
        counts: Dict[str, int] = {}
        for item in items:
            platform = item.get("platform", "unknown")
            counts[platform] = counts.get(platform, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    """Standalone pipeline execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    pipeline = ContentPipeline()
    status = pipeline.get_pipeline_status()
    logger.info(f"Pipeline status: {json.dumps(status, indent=2)}")

    # Example: generate a content calendar
    calendar = pipeline.generate_content_calendar(days_ahead=3, posts_per_day=2)
    logger.info(f"Generated {len(calendar)} calendar entries")

    for entry in calendar[:5]:
        logger.info(f"  {entry['scheduled_time']} | {entry['platform']} | {entry['topic']}")


if __name__ == "__main__":
    main()
