#!/usr/bin/env python3
"""
Analytics Tracker
Tracks published content performance, reports to the swarm queue,
and integrates with the verification engagement monitor.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class AnalyticsTracker:
    """
    Tracks social media post performance across platforms,
    reports analytics to the swarm queue for cross-agent visibility,
    and integrates with the verification engagement monitor.
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize the Analytics Tracker.

        Args:
            project_root: Project root directory. Defaults to auto-detection.
        """
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parent.parent

        # Data files
        self._data_dir = self.project_root / "data" / "social_analytics"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._posts_file = self._data_dir / "tracked_posts.json"
        self._metrics_file = self._data_dir / "performance_metrics.json"
        self._reports_file = self._data_dir / "analytics_reports.json"

        # Swarm queue file (matches project convention from unified_improvement_workflow)
        self._swarm_queue_file = self.project_root / "swarm" / "social_analytics.jsonl"
        self._swarm_queue_file.parent.mkdir(parents=True, exist_ok=True)

        # In-memory state
        self._tracked_posts: List[Dict[str, Any]] = []
        self._metrics: Dict[str, Any] = {
            "total_posts": 0,
            "by_platform": {},
            "by_category": {},
            "engagement_totals": {
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "impressions": 0,
                "clicks": 0,
            },
        }

        # Load persisted state
        self._load_state()

        logger.info(f"AnalyticsTracker initialized | Tracking {len(self._tracked_posts)} posts")

    # ------------------------------------------------------------------
    # State Persistence
    # ------------------------------------------------------------------

    def _load_state(self):
        """Load persisted analytics state from disk."""
        try:
            if self._posts_file.exists():
                with open(self._posts_file, "r") as f:
                    data = json.load(f)
                self._tracked_posts = data.get("posts", [])
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load tracked posts: {e}")

        try:
            if self._metrics_file.exists():
                with open(self._metrics_file, "r") as f:
                    self._metrics = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load metrics: {e}")

    def _save_state(self):
        """Persist analytics state to disk."""
        try:
            with open(self._posts_file, "w") as f:
                json.dump(
                    {"posts": self._tracked_posts, "last_updated": datetime.now().isoformat()},
                    f,
                    indent=2,
                )
            with open(self._metrics_file, "w") as f:
                json.dump(self._metrics, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save analytics state: {e}")

    # ------------------------------------------------------------------
    # Post Tracking
    # ------------------------------------------------------------------

    def track_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Track a newly published post for analytics monitoring.

        Args:
            post_data: Dictionary with post details:
                - platform: str
                - content: str
                - post_id: str (from Postiz)
                - published_at: str (ISO datetime)
                - schedule_name: str (optional)
                - category: str (optional)

        Returns:
            Tracking record with assigned tracking ID.
        """
        tracking_record = {
            "tracking_id": f"track_{int(time.time())}_{post_data.get('platform', 'unknown')}",
            "post_id": post_data.get("post_id"),
            "platform": post_data.get("platform", "unknown"),
            "content": post_data.get("content", ""),
            "content_preview": post_data.get("content", "")[:100],
            "published_at": post_data.get("published_at", datetime.now().isoformat()),
            "schedule_name": post_data.get("schedule_name"),
            "category": post_data.get("category"),
            "status": post_data.get("status", "published"),
            "tracked_at": datetime.now().isoformat(),
            "engagement": {
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "impressions": 0,
                "clicks": 0,
                "saves": 0,
            },
            "last_checked": None,
            "performance_score": 0.0,
        }

        self._tracked_posts.append(tracking_record)

        # Update aggregate metrics
        self._metrics["total_posts"] += 1
        platform = tracking_record["platform"]
        if platform not in self._metrics["by_platform"]:
            self._metrics["by_platform"][platform] = {"count": 0, "engagement": 0}
        self._metrics["by_platform"][platform]["count"] += 1

        category = tracking_record.get("category", "uncategorized")
        if category not in self._metrics["by_category"]:
            self._metrics["by_category"][category] = {"count": 0, "engagement": 0}
        self._metrics["by_category"][category]["count"] += 1

        self._save_state()
        logger.info(f"Tracking post: {tracking_record['tracking_id']} on {platform}")
        return tracking_record

    def update_engagement(
        self,
        tracking_id: str,
        engagement_data: Dict[str, int],
    ) -> Optional[Dict[str, Any]]:
        """
        Update engagement metrics for a tracked post.

        Args:
            tracking_id: The tracking ID of the post.
            engagement_data: Dictionary with engagement metrics:
                - likes, comments, shares, impressions, clicks, saves

        Returns:
            Updated tracking record or None if not found.
        """
        for post in self._tracked_posts:
            if post["tracking_id"] == tracking_id:
                # Calculate deltas
                old_engagement = post["engagement"]
                deltas = {}
                for key, new_val in engagement_data.items():
                    if key in old_engagement:
                        deltas[key] = new_val - old_engagement[key]
                        old_engagement[key] = new_val

                # Update global totals
                for key, delta in deltas.items():
                    if delta > 0 and key in self._metrics["engagement_totals"]:
                        self._metrics["engagement_totals"][key] += delta

                # Update platform engagement
                platform = post["platform"]
                total_engagement = sum(old_engagement.values())
                if platform in self._metrics["by_platform"]:
                    self._metrics["by_platform"][platform]["engagement"] = sum(
                        p["engagement"].get("likes", 0) + p["engagement"].get("comments", 0)
                        + p["engagement"].get("shares", 0)
                        for p in self._tracked_posts
                        if p["platform"] == platform
                    )

                # Calculate performance score
                post["performance_score"] = self._calculate_performance_score(post)
                post["last_checked"] = datetime.now().isoformat()

                self._save_state()
                logger.info(
                    f"Updated engagement for {tracking_id}: "
                    f"score={post['performance_score']:.2f}"
                )
                return post

        logger.warning(f"Post not found: {tracking_id}")
        return None

    def _calculate_performance_score(self, post: Dict[str, Any]) -> float:
        """
        Calculate a normalized performance score for a post.
        Score considers engagement relative to impressions and time since posting.

        Args:
            post: Tracked post record.

        Returns:
            Performance score from 0.0 to 100.0.
        """
        engagement = post.get("engagement", {})
        impressions = max(engagement.get("impressions", 1), 1)
        likes = engagement.get("likes", 0)
        comments = engagement.get("comments", 0)
        shares = engagement.get("shares", 0)
        clicks = engagement.get("clicks", 0)
        saves = engagement.get("saves", 0)

        # Weighted engagement rate
        weighted_engagement = (
            likes * 1.0
            + comments * 3.0  # Comments are high-value
            + shares * 5.0    # Shares/retweets are highest value
            + clicks * 2.0
            + saves * 4.0     # Saves indicate strong content
        )

        # Engagement rate as percentage of impressions
        engagement_rate = (weighted_engagement / impressions) * 100

        # Time decay factor - newer posts get less penalty
        published_at = datetime.fromisoformat(post.get("published_at", datetime.now().isoformat()))
        hours_since_post = max((datetime.now() - published_at).total_seconds() / 3600, 1)

        # Score: engagement rate with time normalization
        # Posts with high engagement rate relative to their age score higher
        if hours_since_post < 24:
            time_factor = 1.0  # No penalty for first 24 hours
        elif hours_since_post < 72:
            time_factor = 0.8
        else:
            time_factor = 0.6

        score = min(engagement_rate * time_factor, 100.0)
        return round(score, 2)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_summary_report(
        self,
        period_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Generate a summary analytics report.

        Args:
            period_hours: Hours to look back for the report.

        Returns:
            Summary report dictionary.
        """
        cutoff = datetime.now() - timedelta(hours=period_hours)
        cutoff_iso = cutoff.isoformat()

        # Filter posts within period
        period_posts = [
            p for p in self._tracked_posts
            if p.get("published_at", "") >= cutoff_iso
        ]

        # Calculate period metrics
        period_engagement = {
            "likes": 0, "comments": 0, "shares": 0,
            "impressions": 0, "clicks": 0, "saves": 0,
        }
        for post in period_posts:
            eng = post.get("engagement", {})
            for key in period_engagement:
                period_engagement[key] += eng.get(key, 0)

        # Best performing posts
        scored_posts = sorted(
            period_posts,
            key=lambda p: p.get("performance_score", 0),
            reverse=True,
        )
        top_posts = scored_posts[:5]

        # Platform breakdown
        platform_breakdown = {}
        for post in period_posts:
            platform = post.get("platform", "unknown")
            if platform not in platform_breakdown:
                platform_breakdown[platform] = {"count": 0, "avg_score": 0, "total_engagement": 0}
            platform_breakdown[platform]["count"] += 1
            platform_breakdown[platform]["total_engagement"] += sum(
                post.get("engagement", {}).values()
            )

        # Calculate averages
        for platform, data in platform_breakdown.items():
            platform_posts = [p for p in period_posts if p.get("platform") == platform]
            if platform_posts:
                data["avg_score"] = round(
                    sum(p.get("performance_score", 0) for p in platform_posts) / len(platform_posts),
                    2,
                )

        report = {
            "report_id": f"report_{int(time.time())}",
            "period_hours": period_hours,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_posts": len(period_posts),
                "total_engagement": period_engagement,
                "average_score": round(
                    sum(p.get("performance_score", 0) for p in period_posts) / max(len(period_posts), 1),
                    2,
                ),
            },
            "platform_breakdown": platform_breakdown,
            "top_posts": [
                {
                    "tracking_id": p["tracking_id"],
                    "platform": p["platform"],
                    "content_preview": p.get("content_preview", ""),
                    "score": p.get("performance_score", 0),
                    "engagement": p.get("engagement", {}),
                }
                for p in top_posts
            ],
            "all_time_metrics": self._metrics,
        }

        # Save report
        self._save_report(report)
        return report

    def _save_report(self, report: Dict[str, Any]):
        """Save a report to disk."""
        try:
            reports = []
            if self._reports_file.exists():
                with open(self._reports_file, "r") as f:
                    data = json.load(f)
                reports = data.get("reports", [])

            reports.append(report)
            # Keep last 100 reports
            reports = reports[-100:]

            with open(self._reports_file, "w") as f:
                json.dump({"reports": reports, "last_updated": datetime.now().isoformat()}, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save report: {e}")

    def report_summary(self):
        """Generate and log a summary report. Convenience method for auto-mode."""
        report = self.get_summary_report()
        logger.info(
            f"Analytics Summary | Posts: {report['summary']['total_posts']} | "
            f"Avg Score: {report['summary']['average_score']} | "
            f"Engagement: {report['summary']['total_engagement']}"
        )
        return report

    # ------------------------------------------------------------------
    # Swarm Queue Integration
    # ------------------------------------------------------------------

    def push_to_swarm_queue(self, data: Optional[Dict[str, Any]] = None):
        """
        Push analytics data to the swarm queue for cross-agent visibility.
        Other agents can read this to understand social media performance.

        Args:
            data: Data to push. If None, generates a summary report.
        """
        if data is None:
            data = self.get_summary_report()

        swarm_entry = {
            "type": "social_analytics",
            "agent": "SocialMediaAgent",
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        try:
            with open(self._swarm_queue_file, "a") as f:
                f.write(json.dumps(swarm_entry) + "\n")
            logger.info("Pushed analytics to swarm queue")
        except IOError as e:
            logger.error(f"Failed to push to swarm queue: {e}")

    def push_post_event(self, event_type: str, post_data: Dict[str, Any]):
        """
        Push a post event to swarm queue (published, high_engagement, viral, etc.)

        Args:
            event_type: Type of event (published, high_engagement, viral, failed).
            post_data: Post data associated with the event.
        """
        event = {
            "type": "social_post_event",
            "event": event_type,
            "agent": "SocialMediaAgent",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "tracking_id": post_data.get("tracking_id"),
                "platform": post_data.get("platform"),
                "content_preview": post_data.get("content_preview", post_data.get("content", "")[:100]),
                "performance_score": post_data.get("performance_score", 0),
                "engagement": post_data.get("engagement", {}),
            },
        }

        try:
            with open(self._swarm_queue_file, "a") as f:
                f.write(json.dumps(event) + "\n")
            logger.debug(f"Pushed {event_type} event to swarm queue")
        except IOError as e:
            logger.error(f"Failed to push event to swarm queue: {e}")

    # ------------------------------------------------------------------
    # Engagement Monitor Integration
    # ------------------------------------------------------------------

    def check_high_performers(self, threshold_score: float = 50.0) -> List[Dict[str, Any]]:
        """
        Identify high-performing posts that exceed the threshold.
        Reports them to the swarm queue for attention.

        Args:
            threshold_score: Minimum performance score to flag.

        Returns:
            List of high-performing post records.
        """
        high_performers = [
            p for p in self._tracked_posts
            if p.get("performance_score", 0) >= threshold_score
        ]

        for post in high_performers:
            # Only report if not already reported
            if not post.get("_reported_high"):
                self.push_post_event("high_engagement", post)
                post["_reported_high"] = True

        if high_performers:
            logger.info(f"Found {len(high_performers)} high-performing posts (score >= {threshold_score})")
            self._save_state()

        return high_performers

    def check_underperformers(self, threshold_score: float = 5.0, min_age_hours: int = 6) -> List[Dict[str, Any]]:
        """
        Identify underperforming posts that may need attention.

        Args:
            threshold_score: Maximum score to flag as underperforming.
            min_age_hours: Minimum post age before flagging (avoid flagging new posts).

        Returns:
            List of underperforming post records.
        """
        cutoff = datetime.now() - timedelta(hours=min_age_hours)
        underperformers = [
            p for p in self._tracked_posts
            if p.get("performance_score", 0) <= threshold_score
            and p.get("published_at", "") <= cutoff.isoformat()
            and not p.get("_reported_under")
        ]

        for post in underperformers:
            post["_reported_under"] = True

        if underperformers:
            logger.info(f"Found {len(underperformers)} underperforming posts (score <= {threshold_score})")
            self._save_state()

        return underperformers

    def correlate_with_verification(self) -> Dict[str, Any]:
        """
        Correlate post performance with verification engagement monitor data.
        Integrates with social/verification_engagement_monitor.py output.

        Returns:
            Correlation analysis dictionary.
        """
        verification_data_file = self.project_root / "data" / "verification_engagement.json"

        verification_data = {}
        if verification_data_file.exists():
            try:
                with open(verification_data_file, "r") as f:
                    verification_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load verification engagement data: {e}")

        # Correlation analysis
        correlation = {
            "timestamp": datetime.now().isoformat(),
            "total_tracked_posts": len(self._tracked_posts),
            "verification_data_available": bool(verification_data),
            "platform_performance": {},
            "category_performance": {},
        }

        # Aggregate by platform
        for post in self._tracked_posts:
            platform = post.get("platform", "unknown")
            if platform not in correlation["platform_performance"]:
                correlation["platform_performance"][platform] = {
                    "posts": 0,
                    "avg_score": 0,
                    "total_engagement": 0,
                    "scores": [],
                }
            pdata = correlation["platform_performance"][platform]
            pdata["posts"] += 1
            pdata["scores"].append(post.get("performance_score", 0))
            pdata["total_engagement"] += sum(post.get("engagement", {}).values())

        # Calculate averages
        for platform, data in correlation["platform_performance"].items():
            scores = data.pop("scores")
            data["avg_score"] = round(sum(scores) / max(len(scores), 1), 2)
            data["max_score"] = max(scores) if scores else 0
            data["min_score"] = min(scores) if scores else 0

        # Aggregate by category
        for post in self._tracked_posts:
            category = post.get("category", "uncategorized")
            if category not in correlation["category_performance"]:
                correlation["category_performance"][category] = {
                    "posts": 0,
                    "avg_score": 0,
                    "scores": [],
                }
            cdata = correlation["category_performance"][category]
            cdata["posts"] += 1
            cdata["scores"].append(post.get("performance_score", 0))

        for category, data in correlation["category_performance"].items():
            scores = data.pop("scores")
            data["avg_score"] = round(sum(scores) / max(len(scores), 1), 2)

        # Push correlation to swarm
        self.push_to_swarm_queue(correlation)

        return correlation

    # ------------------------------------------------------------------
    # Bulk Operations
    # ------------------------------------------------------------------

    def fetch_all_post_analytics(self, postiz_connector) -> int:
        """
        Fetch latest analytics for all tracked posts from Postiz.

        Args:
            postiz_connector: PostizConnector instance.

        Returns:
            Number of posts updated.
        """
        updated = 0
        for post in self._tracked_posts:
            post_id = post.get("post_id")
            if not post_id:
                continue

            try:
                analytics = postiz_connector.get_analytics(post_id)
                if analytics:
                    engagement_data = {
                        "likes": analytics.get("likes", 0),
                        "comments": analytics.get("comments", 0),
                        "shares": analytics.get("shares", analytics.get("retweets", 0)),
                        "impressions": analytics.get("impressions", analytics.get("views", 0)),
                        "clicks": analytics.get("clicks", analytics.get("link_clicks", 0)),
                        "saves": analytics.get("saves", analytics.get("bookmarks", 0)),
                    }
                    self.update_engagement(post["tracking_id"], engagement_data)
                    updated += 1
            except Exception as e:
                logger.debug(f"Failed to fetch analytics for {post_id}: {e}")

        if updated:
            # Check for high/low performers after update
            self.check_high_performers()
            self.check_underperformers()

        logger.info(f"Updated analytics for {updated}/{len(self._tracked_posts)} posts")
        return updated

    def get_best_posting_times(self) -> Dict[str, List[int]]:
        """
        Analyze post performance to determine best posting times per platform.

        Returns:
            Dictionary mapping platform to list of best hours (0-23).
        """
        platform_hours: Dict[str, Dict[int, List[float]]] = {}

        for post in self._tracked_posts:
            platform = post.get("platform", "unknown")
            published_at = post.get("published_at")
            score = post.get("performance_score", 0)

            if not published_at:
                continue

            try:
                hour = datetime.fromisoformat(published_at).hour
            except (ValueError, TypeError):
                continue

            if platform not in platform_hours:
                platform_hours[platform] = {}
            if hour not in platform_hours[platform]:
                platform_hours[platform][hour] = []
            platform_hours[platform][hour].append(score)

        # Find top 3 hours per platform by average score
        best_times: Dict[str, List[int]] = {}
        for platform, hours_data in platform_hours.items():
            hour_averages = [
                (hour, sum(scores) / len(scores))
                for hour, scores in hours_data.items()
                if len(scores) >= 2  # Minimum sample size
            ]
            hour_averages.sort(key=lambda x: x[1], reverse=True)
            best_times[platform] = [h for h, _ in hour_averages[:3]]

        return best_times


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    """Standalone analytics execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    tracker = AnalyticsTracker()

    # Generate report
    report = tracker.get_summary_report()
    logger.info(f"Report: {json.dumps(report, indent=2)}")

    # Push to swarm
    tracker.push_to_swarm_queue()

    # Run correlation analysis
    correlation = tracker.correlate_with_verification()
    logger.info(f"Correlation: {json.dumps(correlation, indent=2)}")


if __name__ == "__main__":
    main()
