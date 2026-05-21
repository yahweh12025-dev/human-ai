#!/usr/bin/env python3
"""
Social Media Agent
Unified agent for autonomous social media content creation and publishing.
Integrates with Postiz for multi-platform publishing, OpenRouter for LLM content generation,
and the swarm scheduling infrastructure for autonomous operation.
"""

import json
import logging
import os
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml
import requests

# Project imports
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.social.postiz_connector import PostizConnector
from agents.social.content_pipeline import ContentPipeline
from agents.social.analytics_tracker import AnalyticsTracker
from core.apps.postiz.custom_plugins.topic_manager import TopicManager, TopicCategory
from core.apps.postiz.custom_plugins.media_generator import MediaGenerationPipeline
from agents.social.media_generator import generate_short as _generate_short_video
import subprocess as _subprocess
from core.agent_communication_protocol import (
    AgentCommunicationProtocol,
    MessageType,
    MessagePriority,
)

logger = logging.getLogger(__name__)

# Supported platforms and their character/format constraints
PLATFORM_SPECS = {
    "twitter": {
        "max_chars": 280,
        "supports_media": True,
        "supports_threads": True,
        "hashtag_limit": 5,
        "tone": "punchy, concise, engagement-driven",
    },
    "instagram": {
        "max_chars": 2200,
        "supports_media": True,
        "supports_threads": False,
        "hashtag_limit": 30,
        "tone": "visual storytelling, lifestyle-oriented, hashtag-rich",
    },
    "youtube": {
        "max_chars": 5000,
        "supports_media": True,
        "supports_threads": False,
        "hashtag_limit": 15,
        "tone": "informative, long-form description, SEO-optimized",
    },
    "tiktok": {
        "max_chars": 2200,
        "supports_media": True,
        "supports_threads": False,
        "hashtag_limit": 10,
        "tone": "trendy, casual, hook-driven, short attention span",
    },
}


class SocialMediaAgent:
    """
    Autonomous social media agent that generates content via LLM,
    adapts per platform, schedules via cron config, and publishes through Postiz.
    Can be triggered by the OpenClaw gateway or run in auto-mode.
    """

    AGENT_ID = "SocialMediaAgent"

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Social Media Agent.

        Args:
            config_path: Path to social_cron.yaml. Defaults to project config.
        """
        self.project_root = Path(__file__).resolve().parent.parent
        self.config_path = config_path or str(self.project_root / "core" / "config" / "social_cron.yaml")

        # Load environment configuration
        self.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.postiz_api_url = os.environ.get("POSTIZ_API_URL", "http://localhost:5000")
        self.postiz_api_key = os.environ.get("POSTIZ_API_KEY", "")

        if not self.openrouter_api_key:
            logger.warning("OPENROUTER_API_KEY not set - LLM content generation will fail")
        if not self.postiz_api_key:
            logger.warning("POSTIZ_API_KEY not set - publishing will fail")

        # Initialize sub-components
        self.postiz = PostizConnector(
            api_url=self.postiz_api_url,
            api_key=self.postiz_api_key,
        )
        self.pipeline = ContentPipeline(
            openrouter_api_key=self.openrouter_api_key,
            postiz_connector=self.postiz,
        )
        self.analytics = AnalyticsTracker(project_root=str(self.project_root))
        self.topic_manager = TopicManager()
        self.media_pipeline = MediaGenerationPipeline()

        # Load schedule config
        self.schedule_config = self._load_schedule_config()

        # Agent communication
        self.protocol = AgentCommunicationProtocol(data_dir=str(self.project_root))
        self._register_agent()

        # Auto-mode state
        self._auto_mode_running = False
        self._auto_mode_thread: Optional[threading.Thread] = None
        self._post_history: List[Dict[str, Any]] = []
        self._last_post_times: Dict[str, datetime] = {}

        logger.info(
            f"SocialMediaAgent initialized | Postiz: {self.postiz_api_url} | "
            f"Platforms: {list(PLATFORM_SPECS.keys())}"
        )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def _load_schedule_config(self) -> Dict[str, Any]:
        """Load the social_cron.yaml scheduling configuration."""
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded schedule config from {self.config_path}")
            return config or {}
        except FileNotFoundError:
            logger.error(f"Schedule config not found: {self.config_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse schedule config: {e}")
            return {}

    def _register_agent(self):
        """Register this agent with the communication protocol."""
        try:
            self.protocol.register_agent(
                agent_id=self.AGENT_ID,
                capabilities=[
                    "social_media_publishing",
                    "content_generation",
                    "analytics_tracking",
                    "multi_platform",
                ],
                endpoint=f"agent://{self.AGENT_ID}",
            )
            logger.info("Agent registered with communication protocol")
        except Exception as e:
            logger.warning(f"Failed to register agent with protocol: {e}")

    # ------------------------------------------------------------------
    # LLM Content Generation via OpenRouter
    # ------------------------------------------------------------------

    def generate_content(
        self,
        topic: str,
        platform: str,
        style: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate social media content using OpenRouter LLM API.

        Args:
            topic: The content topic/theme.
            platform: Target platform (twitter, instagram, youtube, tiktok).
            style: Optional style override.
            context: Additional context for content generation.

        Returns:
            Generated content string optimized for the platform.
        """
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is not set")

        spec = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["twitter"])
        tone = style or spec["tone"]
        max_chars = spec["max_chars"]
        hashtag_limit = spec["hashtag_limit"]

        system_prompt = (
            "You are a professional social media content creator for a trading and crypto community. "
            "You create engaging, authentic content that drives engagement without being spammy. "
            "Never use fake data. If you reference numbers, use realistic placeholders. "
            "Always match the platform's native style and format."
        )

        user_prompt = (
            f"Create a single social media post for {platform.upper()} about: {topic}\n\n"
            f"Requirements:\n"
            f"- Maximum {max_chars} characters\n"
            f"- Tone: {tone}\n"
            f"- Maximum {hashtag_limit} hashtags\n"
            f"- Do NOT use markdown formatting\n"
            f"- Do NOT include platform name in the post\n"
            f"- Make it feel native to {platform}\n"
        )

        if platform == "twitter":
            user_prompt += "- Keep it punchy, ideally under 240 chars to allow retweet commentary\n"
            user_prompt += "- Use 1-3 relevant hashtags maximum\n"
        elif platform == "instagram":
            user_prompt += "- Start with a hook line, then provide value\n"
            user_prompt += "- End with a call-to-action\n"
            user_prompt += "- Place hashtags at the end, separated by a line break\n"
        elif platform == "youtube":
            user_prompt += "- Write a video description with timestamps placeholder\n"
            user_prompt += "- Include SEO keywords naturally\n"
            user_prompt += "- Add a subscribe CTA\n"
        elif platform == "tiktok":
            user_prompt += "- Start with a strong hook (first 3 seconds equivalent)\n"
            user_prompt += "- Use trending language and casual tone\n"
            user_prompt += "- Include relevant trending hashtags\n"

        if context:
            user_prompt += f"\nAdditional context: {json.dumps(context)}\n"

        user_prompt += "\nReturn ONLY the post content, nothing else."

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://human-ai.trading",
                    "X-Title": "Human-AI Social Agent",
                },
                json={
                    "model": "meta-llama/llama-3.3-70b-instruct:free",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 1024,
                    "temperature": 0.8,
                },
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()

            # Enforce character limit
            if len(content) > max_chars:
                content = content[:max_chars - 3] + "..."
                logger.warning(f"Content truncated to {max_chars} chars for {platform}")

            logger.info(f"Generated {platform} content ({len(content)} chars): {content[:60]}...")
            return content

        except requests.exceptions.Timeout:
            logger.error("OpenRouter API timeout during content generation")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter API request failed: {e}")
            raise
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse OpenRouter response: {e}")
            raise ValueError(f"Invalid response from OpenRouter: {e}")

    # ------------------------------------------------------------------
    # Multi-Platform Publishing
    # ------------------------------------------------------------------

    def publish_to_platform(
        self,
        content: str,
        platform: str,
        scheduled_time: Optional[datetime] = None,
        media_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Publish content to a specific platform via Postiz.

        Args:
            content: The content text to publish.
            platform: Target platform identifier.
            scheduled_time: Optional future scheduling time.
            media_ids: Optional media attachments.

        Returns:
            Postiz API response with post ID and status.
        """
        if platform not in PLATFORM_SPECS:
            raise ValueError(f"Unsupported platform: {platform}. Supported: {list(PLATFORM_SPECS.keys())}")

        try:
            result = self.postiz.publish_content(
                content=content,
                platforms=[platform],
                scheduled_time=scheduled_time,
                media_ids=media_ids,
            )

            # Track the post
            post_record = {
                "platform": platform,
                "content": content,
                "published_at": datetime.now().isoformat(),
                "scheduled_at": scheduled_time.isoformat() if scheduled_time else None,
                "post_id": result.get("id", result.get("post_id")),
                "status": "scheduled" if scheduled_time else "published",
            }
            self._post_history.append(post_record)
            self._last_post_times[platform] = datetime.now()

            # Report to analytics tracker
            self.analytics.track_post(post_record)

            logger.info(f"Published to {platform}: {content[:50]}...")
            return result

        except Exception as e:
            logger.error(f"Failed to publish to {platform}: {e}")
            raise

    def publish_multi_platform(
        self,
        topic: str,
        platforms: Optional[List[str]] = None,
        scheduled_time: Optional[datetime] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate and publish content across multiple platforms.

        Args:
            topic: Content topic/theme.
            platforms: List of target platforms. Defaults to all supported.
            scheduled_time: Optional scheduling time.
            context: Additional context for generation.

        Returns:
            Dictionary mapping platform to publish result.
        """
        platforms = platforms or list(PLATFORM_SPECS.keys())
        results = {}

        # Generate media assets for video platforms
        video_platforms = [p for p in platforms if p in ("tiktok", "youtube", "youtube_shorts", "instagram")]
        if video_platforms:
            try:
                media_results = self.media_pipeline.generate_for_platform(topic, video_platforms)
                logger.info(f"Media generated for {video_platforms}")
            except Exception as e:
                logger.warning(f"MediaGenerationPipeline skipped: {e}")
                media_results = {}

            # Also produce real ffmpeg-based short videos via the new pipeline
            short_video_results = {}
            for vp in video_platforms:
                platform_key = vp if vp in ("tiktok", "youtube_shorts", "instagram_reel") else "tiktok"
                try:
                    vr = _generate_short_video(topic, platform_key, duration_s=30)
                    if vr.get("success"):
                        short_video_results[vp] = vr
                        logger.info(f"Short video generated for {vp}: {vr['output']} ({vr['file_size_kb']}KB)")
                    else:
                        logger.warning(f"Short video generation failed for {vp}")
                except Exception as ve:
                    logger.warning(f"Short video generation error for {vp}: {ve}")
        else:
            media_results = {}
            short_video_results = {}

        for platform in platforms:
            try:
                content = self.generate_content(
                    topic=topic,
                    platform=platform,
                    context=context,
                )
                # Attach media if available
                if platform in media_results.get("platforms", {}):
                    content["media"] = media_results["platforms"][platform]

                # Attach short video if available
                video_asset = short_video_results.get(platform)
                media_ids_for_platform = media_ids
                if video_asset and video_asset.get("output"):
                    logger.info(f"Attaching video asset to {platform} post: {video_asset['output']}")

                result = self.publish_to_platform(
                    content=content,
                    platform=platform,
                    scheduled_time=scheduled_time,
                    media_ids=media_ids_for_platform,
                )
                results[platform] = {
                    "status": "success",
                    "result": result,
                    "content": content,
                    "video_asset": video_asset,
                }
            except Exception as e:
                logger.error(f"Failed for {platform}: {e}")
                results[platform] = {"status": "error", "error": str(e)}

        return results

    # ------------------------------------------------------------------
    # Schedule-Based Operations
    # ------------------------------------------------------------------

    def get_active_schedules(self) -> List[Dict[str, Any]]:
        """Get all enabled schedules from social_cron.yaml."""
        schedules = self.schedule_config.get("schedules", {})
        active = []
        for name, config in schedules.items():
            if config.get("enabled", False):
                active.append({"name": name, **config})
        return active

    def should_post_now(self, schedule_name: str) -> bool:
        """
        Determine if a scheduled post should fire now based on cron expression and blackout periods.

        Args:
            schedule_name: Name of the schedule to check.

        Returns:
            True if the schedule should fire now.
        """
        schedules = self.schedule_config.get("schedules", {})
        schedule = schedules.get(schedule_name)
        if not schedule or not schedule.get("enabled", False):
            return False

        # Check holidays
        holidays = self.schedule_config.get("holidays", [])
        today_str = datetime.now().strftime("%Y-%m-%d")
        if today_str in holidays:
            logger.info(f"Skipping {schedule_name} - holiday: {today_str}")
            return False

        # Check blackout periods
        blackouts = self.schedule_config.get("blackout_periods", [])
        now = datetime.now()
        for blackout in blackouts:
            start_hour = int(blackout["start"].split(":")[0])
            end_hour = int(blackout["end"].split(":")[0])
            day_of_week = str(now.weekday() + 1)  # 1=Monday in the config
            if day_of_week in blackout.get("days", []):
                current_hour = now.hour
                if start_hour > end_hour:  # Crosses midnight
                    if current_hour >= start_hour or current_hour < end_hour:
                        logger.info(f"Skipping {schedule_name} - blackout period")
                        return False
                else:
                    if start_hour <= current_hour < end_hour:
                        logger.info(f"Skipping {schedule_name} - blackout period")
                        return False

        # Check global rate limit
        global_settings = self.schedule_config.get("global_settings", {})
        max_per_hour = global_settings.get("max_posts_per_hour", 10)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_posts = [
            p for p in self._post_history
            if datetime.fromisoformat(p["published_at"]) > one_hour_ago
        ]
        if len(recent_posts) >= max_per_hour:
            logger.warning(f"Rate limit reached: {len(recent_posts)}/{max_per_hour} posts/hour")
            return False

        # Check throttle for this specific schedule
        payload = schedule.get("payload", {})
        throttle = payload.get("throttle")
        if throttle:
            recent_for_schedule = [
                p for p in self._post_history
                if datetime.fromisoformat(p["published_at"]) > one_hour_ago
                and p.get("schedule_name") == schedule_name
            ]
            if len(recent_for_schedule) >= throttle:
                logger.info(f"Throttle limit for {schedule_name}: {len(recent_for_schedule)}/{throttle}")
                return False

        return True

    def execute_scheduled_post(self, schedule_name: str) -> Optional[Dict[str, Any]]:
        """
        Execute a scheduled post based on its configuration.

        Args:
            schedule_name: Name of the schedule from social_cron.yaml.

        Returns:
            Publishing result or None if skipped.
        """
        schedules = self.schedule_config.get("schedules", {})
        schedule = schedules.get(schedule_name)
        if not schedule:
            logger.error(f"Schedule not found: {schedule_name}")
            return None

        if not self.should_post_now(schedule_name):
            return None

        payload = schedule.get("payload", {})
        topic_category = payload.get("topic_category", "MARKET_ANALYSIS")
        template = payload.get("template", "")
        priority = payload.get("priority", "medium")

        # Map schedule topic category to TopicCategory enum
        try:
            category = TopicCategory(topic_category.lower())
        except ValueError:
            category = TopicCategory.MARKET_ANALYSIS

        # Use topic manager to select appropriate content topic
        topic_data = self.topic_manager.select_topic(preferred_category=category)
        topic_title = topic_data.get("title", topic_category)

        # Generate and publish to all platforms
        context = {
            "schedule": schedule_name,
            "template": template,
            "priority": priority,
            "category": topic_category,
        }

        results = self.publish_multi_platform(
            topic=f"{topic_title} - {topic_category.replace('_', ' ').title()}",
            context=context,
        )

        # Record schedule execution
        for platform, result in results.items():
            if result.get("status") == "success":
                self._post_history[-1]["schedule_name"] = schedule_name

        return results

    # ------------------------------------------------------------------
    # Auto Mode (Autonomous Operation)
    # ------------------------------------------------------------------

    def start_auto_mode(self, interval_seconds: int = 300):
        """
        Start autonomous content creation mode.
        The agent will check schedules and generate content on its own.

        Args:
            interval_seconds: Seconds between schedule checks (default 5 min).
        """
        if self._auto_mode_running:
            logger.warning("Auto mode already running")
            return

        self._auto_mode_running = True
        self._auto_mode_thread = threading.Thread(
            target=self._auto_mode_loop,
            args=(interval_seconds,),
            daemon=True,
            name="SocialMediaAgent-AutoMode",
        )
        self._auto_mode_thread.start()
        logger.info(f"Auto mode started (interval: {interval_seconds}s)")

    def stop_auto_mode(self):
        """Stop autonomous content creation mode."""
        self._auto_mode_running = False
        if self._auto_mode_thread and self._auto_mode_thread.is_alive():
            self._auto_mode_thread.join(timeout=10)
        logger.info("Auto mode stopped")

    def _auto_mode_loop(self, interval_seconds: int):
        """Main auto-mode execution loop."""
        logger.info("Auto mode loop started")

        while self._auto_mode_running:
            try:
                # Check for gateway messages (OpenClaw triggers)
                self._process_gateway_messages()

                # Execute any due schedules
                active_schedules = self.get_active_schedules()
                for schedule in active_schedules:
                    schedule_name = schedule["name"]
                    if self.should_post_now(schedule_name):
                        logger.info(f"Auto-executing schedule: {schedule_name}")
                        try:
                            self.execute_scheduled_post(schedule_name)
                        except Exception as e:
                            logger.error(f"Schedule execution failed ({schedule_name}): {e}")

                # Report analytics
                self.analytics.report_summary()

            except Exception as e:
                logger.error(f"Auto mode loop error: {e}")

            # Wait for next cycle
            for _ in range(interval_seconds):
                if not self._auto_mode_running:
                    break
                time.sleep(1)

        logger.info("Auto mode loop ended")

    # ------------------------------------------------------------------
    # Gateway Integration (OpenClaw Triggers)
    # ------------------------------------------------------------------

    def _process_gateway_messages(self):
        """Process incoming messages from the OpenClaw gateway."""
        try:
            messages = self.protocol.receive_message(self.AGENT_ID)
            for msg in messages:
                self._handle_gateway_message(msg)
                self.protocol.acknowledge_message(msg["message_id"], self.AGENT_ID)
        except Exception as e:
            logger.debug(f"No gateway messages or protocol error: {e}")

    def _handle_gateway_message(self, message: Dict[str, Any]):
        """
        Handle a message from the gateway.

        Supported task types:
        - publish: Generate and publish content
        - schedule: Create calendar entries
        - analytics: Return analytics data
        - status: Return agent status
        """
        content = message.get("content", {})
        task_type = content.get("task_type", "publish")
        sender = message.get("sender", "unknown")

        logger.info(f"Processing gateway message from {sender}: {task_type}")

        if task_type == "publish":
            topic = content.get("topic", "Market Update")
            platforms = content.get("platforms")
            result = self.publish_multi_platform(topic=topic, platforms=platforms)
            self._send_response(sender, message["message_id"], result)

        elif task_type == "schedule":
            topic = content.get("topic", "Market Update")
            platforms = content.get("platforms")
            schedule_time = content.get("scheduled_time")
            if schedule_time:
                schedule_time = datetime.fromisoformat(schedule_time)
            result = self.publish_multi_platform(
                topic=topic, platforms=platforms, scheduled_time=schedule_time
            )
            self._send_response(sender, message["message_id"], result)

        elif task_type == "create_video":
            # Trigger trading short video via produce_video.py
            signal  = content.get("signal")          # BUY / SELL / None
            topic   = content.get("topic", "Gold trading signal XAUUSD")
            platform = content.get("platform", "tiktok")
            duration = int(content.get("duration", 30))
            script_root = Path(__file__).resolve().parents[1] / "scripts" / "produce_video.py"
            cmd = [sys.executable, str(script_root), "--platform", platform, "--duration", str(duration)]
            if signal:
                cmd += ["--signal", signal.upper()]
            else:
                cmd += ["--topic", topic]
            try:
                proc = _subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                result = {"success": proc.returncode == 0, "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-500:]}
                logger.info(f"create_video result: {result['success']} | {proc.stdout[-200:]}")
            except Exception as exc:
                result = {"success": False, "error": str(exc)}
            self._send_response(sender, message["message_id"], result)

        elif task_type == "faithnexus_video":
            # Trigger FaithNexus scripture video via produce_faithnexus_video.py
            verse = content.get("verse")             # e.g. "John 3:16" or None → auto
            script_root = Path(__file__).resolve().parents[1] / "scripts" / "produce_faithnexus_video.py"
            cmd = [sys.executable, str(script_root)]
            if verse:
                cmd += ["--verse", verse]
            else:
                cmd += ["--auto"]
            try:
                proc = _subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                result = {"success": proc.returncode == 0, "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-500:]}
                logger.info(f"faithnexus_video result: {result['success']} | {proc.stdout[-200:]}")
            except Exception as exc:
                result = {"success": False, "error": str(exc)}
            self._send_response(sender, message["message_id"], result)

        elif task_type == "analytics":
            report = self.analytics.get_summary_report()
            self._send_response(sender, message["message_id"], report)

        elif task_type == "status":
            status = self.get_status()
            self._send_response(sender, message["message_id"], status)

        else:
            logger.warning(f"Unknown task type from gateway: {task_type}")

    def _send_response(self, recipient: str, ref_message_id: str, data: Any):
        """Send a response back through the communication protocol."""
        try:
            self.protocol.send_message(
                sender=self.AGENT_ID,
                recipient=recipient,
                message_type=MessageType.TASK_RESPONSE,
                content={
                    "reference_message_id": ref_message_id,
                    "result": data,
                    "timestamp": datetime.now().isoformat(),
                },
                priority=MessagePriority.MEDIUM,
            )
        except Exception as e:
            logger.error(f"Failed to send response to {recipient}: {e}")

    # ------------------------------------------------------------------
    # Content Pipeline Integration
    # ------------------------------------------------------------------

    def create_content_calendar(
        self,
        days_ahead: int = 7,
        platforms: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate a full content calendar using the pipeline.

        Args:
            days_ahead: Number of days to plan ahead.
            platforms: Target platforms.

        Returns:
            List of calendar entries ready for scheduling.
        """
        platforms = platforms or list(PLATFORM_SPECS.keys())
        return self.pipeline.generate_content_calendar(
            days_ahead=days_ahead,
            platforms=platforms,
            topic_manager=self.topic_manager,
        )

    def queue_calendar_to_postiz(self, calendar: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Push an entire content calendar to Postiz for batch scheduling.

        Args:
            calendar: List of calendar entries from create_content_calendar.

        Returns:
            Postiz batch scheduling response.
        """
        return self.pipeline.queue_to_postiz(calendar)

    # ------------------------------------------------------------------
    # Status & Reporting
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "agent_id": self.AGENT_ID,
            "auto_mode": self._auto_mode_running,
            "posts_published": len(self._post_history),
            "last_post_times": {
                k: v.isoformat() for k, v in self._last_post_times.items()
            },
            "active_schedules": len(self.get_active_schedules()),
            "supported_platforms": list(PLATFORM_SPECS.keys()),
            "postiz_url": self.postiz_api_url,
            "timestamp": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Auto Mode Controller Integration
    # ------------------------------------------------------------------

    def execute_task(self, task: Dict[str, Any]) -> bool:
        """
        Execute a task from the auto_mode_controller.

        Args:
            task: Task dictionary from unified_tasks.json.

        Returns:
            True if task was executed successfully.
        """
        task_desc = task.get("task", "").lower()
        logger.info(f"Executing social media task: {task.get('id', 'unknown')}")

        try:
            if "publish" in task_desc or "post" in task_desc:
                topic = task.get("payload", {}).get("topic", "Trading Update")
                platforms = task.get("payload", {}).get("platforms")
                result = self.publish_multi_platform(topic=topic, platforms=platforms)
                return any(r.get("status") == "success" for r in result.values())

            elif "calendar" in task_desc or "schedule" in task_desc:
                days = task.get("payload", {}).get("days_ahead", 7)
                calendar = self.create_content_calendar(days_ahead=days)
                self.queue_calendar_to_postiz(calendar)
                return True

            elif "analytics" in task_desc or "report" in task_desc:
                self.analytics.report_summary()
                return True

            elif "auto" in task_desc:
                interval = task.get("payload", {}).get("interval", 300)
                self.start_auto_mode(interval_seconds=interval)
                return True

            else:
                # Default: treat as a publish request
                result = self.publish_multi_platform(topic=task_desc)
                return any(r.get("status") == "success" for r in result.values())

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return False


# ---------------------------------------------------------------------------
# Entry Points
# ---------------------------------------------------------------------------


def main():
    """Main entry point for standalone execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    agent = SocialMediaAgent()
    status = agent.get_status()
    logger.info(f"Agent status: {json.dumps(status, indent=2)}")

    import argparse
    parser = argparse.ArgumentParser(description="Social Media Agent")
    parser.add_argument("--auto", action="store_true", help="Start autonomous mode")
    parser.add_argument("--interval", type=int, default=300, help="Auto mode interval seconds")
    parser.add_argument("--topic", type=str, help="Override topic for immediate post")
    parser.add_argument("--platforms", nargs="+", default=None,
                        help="Target platforms (twitter instagram tiktok youtube)")
    parser.add_argument("--media-only", action="store_true", help="Generate media without publishing")
    parser.add_argument("--set-topic", type=str, help="Set default topic for future posts")
    args = parser.parse_args()

    if args.set_topic:
        topic_file = Path(agent.project_root) / "configs" / "social_topic.txt"
        topic_file.write_text(args.set_topic)
        print(f"Default topic set to: {args.set_topic}")

    if args.topic:
        if args.media_only:
            # Generate media only
            result = agent.media_pipeline.generate_for_platform(
                args.topic, args.platforms or ["tiktok", "youtube_shorts"]
            )
            print(json.dumps(result, indent=2, default=str))
        else:
            # Immediate post with topic override
            result = agent.publish_multi_platform(
                topic=args.topic,
                platforms=args.platforms,
            )
            print(json.dumps(result, indent=2, default=str))

    elif args.auto:
        logger.info(f"Starting auto mode with {args.interval}s interval")
        agent.start_auto_mode(interval_seconds=args.interval)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            agent.stop_auto_mode()
            logger.info("Shutdown complete")
    else:
        # Single execution mode - run all active schedules once
        active = agent.get_active_schedules()
        logger.info(f"Active schedules: {len(active)}")
        for schedule in active:
            name = schedule["name"]
            if agent.should_post_now(name):
                logger.info(f"Executing: {name}")
                agent.execute_scheduled_post(name)


if __name__ == "__main__":
    main()
