#!/usr/bin/env python3
"""
Development Tracker Utility
Provides structured logging for swarm development activities and progress tracking.
Outputs JSON lines for easy parsing and includes helper methods for tracking task progress.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List
from enum import Enum

# Import the SwarmLogger
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.utils.swarm_logger import get_logger, LogLevel


class ActivityType(Enum):
    """Types of development activities that can be logged."""
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    TASK_PROGRESS = "task_progress"
    CODE_COMMIT = "code_commit"
    DESIGN_DECISION = "design_decision"
    BUG_FIX = "bug_fix"
    REFACTOR = "refactor"
    REVIEW = "review"
    MEETING = "meeting"
    RESEARCH = "research"
    EXPERIMENT = "experiment"
    DEPLOYMENT = "deployment"
    INTEGRATION = "integration"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    OTHER = "other"


class DevelopmentTracker:
    def __init__(self, source: str = "development_tracker", base_dir: Optional[str] = None):
        """
        Initialize a DevelopmentTracker for logging swarm development activities.

        Args:
            source: Identifier for the source of logs (e.g., 'developer_agent', 'researcher')
            base_dir: Base directory of the human-ai repository (default: parent of this file's parent)
        """
        self.source = source
        self.logger = get_logger(source)
        if base_dir is None:
            # Default to the human-ai directory (assuming this file is in human-ai/core/utils/)
            self.base_dir = Path(__file__).parent.parent.parent
        else:
            self.base_dir = Path(base_dir)
        self.todo_path = self.base_dir / "infrastructure/configs/todo.json"

    def _log_activity(self, activity_type: ActivityType, message: str, task_id: Optional[str] = None, **kwargs):
        """Internal method to log a development activity with optional structured data."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": self.source,
            "level": LogLevel.INFO.value,
            "message": message,
            "activity_type": activity_type.value,
        }
        if task_id:
            log_entry["task_id"] = task_id
        # Add any extra fields provided
        if kwargs:
            log_entry["data"] = kwargs

        # Output as JSON line for machine parsing
        json_line = json.dumps(log_entry)
        self.logger.output_stream.write(json_line + "\n")
        self.logger.output_stream.flush()

    def log_task_start(self, task_id: str, description: str, **kwargs):
        """Log the start of a development task."""
        self._log_activity(
            ActivityType.TASK_START,
            f"Starting task: {description}",
            task_id=task_id,
            **kwargs
        )

    def log_task_complete(self, task_id: str, description: str, **kwargs):
        """Log the completion of a development task."""
        self._log_activity(
            ActivityType.TASK_COMPLETE,
            f"Completed task: {description}",
            task_id=task_id,
            **kwargs
        )

    def log_task_progress(self, task_id: str, description: str, progress_percent: Optional[float] = None, **kwargs):
        """Log progress on a development task."""
        self._log_activity(
            ActivityType.TASK_PROGRESS,
            f"Task progress: {description}",
            task_id=task_id,
            progress_percent=progress_percent,
            **kwargs
        )

    def log_code_commit(self, task_id: str, commit_hash: str, message: str, **kwargs):
        """Log a code commit related to a task."""
        self._log_activity(
            ActivityType.CODE_COMMIT,
            f"Code commit: {message}",
            task_id=task_id,
            commit_hash=commit_hash,
            **kwargs
        )

    def log_design_decision(self, task_id: str, decision: str, rationale: str, **kwargs):
        """Log a design decision."""
        self._log_activity(
            ActivityType.DESIGN_DECISION,
            f"Design decision: {decision}",
            task_id=task_id,
            rationale=rationale,
            **kwargs
        )

    def log_bug_fix(self, task_id: str, bug_description: str, fix_description: str, **kwargs):
        """Log a bug fix."""
        self._log_activity(
            ActivityType.BUG_FIX,
            f"Bug fix: {fix_description}",
            task_id=task_id,
            bug_description=bug_description,
            fix_description=fix_description,
            **kwargs
        )

    def log_refactor(self, task_id: str, description: str, **kwargs):
        """Log a refactoring activity."""
        self._log_activity(
            ActivityType.REFACTOR,
            f"Refactoring: {description}",
            task_id=task_id,
            **kwargs
        )

    def log_review(self, task_id: str, review_type: str, findings: str, **kwargs):
        """Log a code or design review."""
        self._log_activity(
            ActivityType.REVIEW,
            f"Review ({review_type}): {findings}",
            task_id=task_id,
            review_type=review_type,
            findings=findings,
            **kwargs
        )

    def log_meeting(self, topic: str, attendees: Optional[List[str]] = None, **kwargs):
        """Log a development meeting."""
        self._log_activity(
            ActivityType.MEETING,
            f"Meeting: {topic}",
            attendees=attendees or [],
            **kwargs
        )

    def log_research(self, topic: str, findings: str, **kwargs):
        """Log research activity."""
        self._log_activity(
            ActivityType.RESEARCH,
            f"Research: {topic}",
            findings=findings,
            **kwargs
        )

    def log_experiment(self, experiment_name: str, hypothesis: str, result: str, **kwargs):
        """Log an experiment."""
        self._log_activity(
            ActivityType.EXPERIMENT,
            f"Experiment: {experiment_name}",
            hypothesis=hypothesis,
            result=result,
            **kwargs
        )

    def log_deployment(self, service: str, version: str, environment: str, **kwargs):
        """Log a deployment."""
        self._log_activity(
            ActivityType.DEPLOYMENT,
            f"Deployment: {service} v{version} to {environment}",
            service=service,
            version=version,
            environment=environment,
            **kwargs
        )

    def log_integration(self, component_a: str, component_b: str, description: str, **kwargs):
        """Log an integration between components."""
        self._log_activity(
            ActivityType.INTEGRATION,
            f"Integration: {component_a} <-> {component_b}",
            description=description,
            component_a=component_a,
            component_b=component_b,
            **kwargs
        )

    def log_testing(self, test_type: str, coverage: Optional[float] = None, passed: Optional[bool] = None, **kwargs):
        """Log testing activity."""
        self._log_activity(
            ActivityType.TESTING,
            f"Testing: {test_type}",
            test_type=test_type,
            coverage=coverage,
            passed=passed,
            **kwargs
        )

    def log_documentation(self, document: str, description: str, **kwargs):
        """Log documentation work."""
        self._log_activity(
            ActivityType.DOCUMENTATION,
            f"Documentation: {document}",
            description=description,
            **kwargs
        )

    def log_other(self, description: str, **kwargs):
        """Log an activity that doesn't fit other categories."""
        self._log_activity(
            ActivityType.OTHER,
            description,
            **kwargs
        )

    # Progress tracking methods
    def update_task_status_in_todo(self, task_id: str, new_status: str, note: Optional[str] = None) -> bool:
        """
        Update the status of a task in todo.json.
        Valid statuses: 'pending', 'in_progress', 'completed', 'archived'

        Returns True if successful, False otherwise.
        """
        try:
            if not self.todo_path.exists():
                self.logger.error("Todo file not found", path=str(self.todo_path))
                return False

            with open(self.todo_path, 'r') as f:
                data = json.load(f)

            # Valid status sections
            valid_sections = ["pending", "in_progress", "completed", "archived"]
            if new_status not in valid_sections:
                self.logger.error("Invalid status", status=new_status, valid_statuses=valid_sections)
                return False

            # Find the task in any section
            task_found = False
            task_data = None
            original_section = None

            for section in valid_sections:
                if section not in data:
                    continue
                for i, task in enumerate(data[section]):
                    if isinstance(task, dict) and task.get("id") == task_id:
                        task_data = task
                        original_section = section
                        # Remove from current section
                        data[section].pop(i)
                        task_found = True
                        break
                if task_found:
                    break

            if not task_found:
                self.logger.error("Task not found in todo.json", task_id=task_id)
                return False

            # Update the task
            if task_data is None:
                return False
            task_data["status"] = new_status
            if note:
                if "notes" not in task_data:
                    task_data["notes"] = []
                task_data["notes"].append({
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "note": note
                })

            # Add to the new section
            if new_status not in data:
                data[new_status] = []
            data[new_status].append(task_data)

            # Write back
            with open(self.todo_path, 'w') as f:
                json.dump(data, f, indent=2)

            self.logger.info(
                f"Updated task status in todo.json",
                task_id=task_id,
                original_section=original_section,
                new_section=new_status,
                note=note
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to update task status: {e}", error=str(e), task_id=task_id)
            return False

    def get_todo_progress(self) -> Dict[str, int]:
        """
        Get progress counts from todo.json.

        Returns a dictionary with counts for each status.
        """
        try:
            if not self.todo_path.exists():
                self.logger.warning("Todo file not found", path=str(self.todo_path))
                return {"completed": 0, "in_progress": 0, "pending": 0, "archived": 0}

            with open(self.todo_path, 'r') as f:
                data = json.load(f)

            progress = {}
            for section in ["completed", "in_progress", "pending", "archived"]:
                count = len(data.get(section, []))
                # Only count dict items (some sections might have strings in archived)
                if section == "archived":
                    count = len([item for item in data.get(section, []) if isinstance(item, dict)])
                progress[section] = count

            return progress
        except Exception as e:
            self.logger.error(f"Failed to read todo progress: {e}", error=str(e))
            return {"completed": 0, "in_progress": 0, "pending": 0, "archived": 0}

    def log_todo_progress(self):
        """Log the current todo progress as a development activity."""
        progress = self.get_todo_progress()
        self.logger.info(
            "Todo progress update",
            activity_type=ActivityType.TASK_PROGRESS.value,
            **progress
        )

    def calculate_velocity_metrics(self, days: int = 7) -> Dict[str, Any]:
        """
        Calculate development velocity metrics from the logs.
        This is a simplified version that reads the log files (if they exist) and counts activities.

        For a more accurate metric, we would need to parse log files with timestamps.
        Since we don't have a centralized log file, we'll return placeholder metrics.

        Returns a dictionary with velocity metrics.
        """
        # Placeholder implementation - in a real system, we would parse log files
        # For now, we'll return based on todo.json completion counts over time
        # We don't have historical completion timestamps, so we'll just return current state
        progress = self.get_todo_progress()
        return {
            "completed_tasks_total": progress["completed"],
            "in_progress_tasks": progress["in_progress"],
            "pending_tasks": progress["pending"],
            "archived_tasks": progress["archived"],
            "velocity_note": "Velocity calculation requires historical log parsing; this is a placeholder."
        }

    def log_velocity_metrics(self, days: int = 7):
        """Log velocity metrics as a development activity."""
        metrics = self.calculate_velocity_metrics(days=days)
        self.logger.info(
            "Development velocity metrics",
            activity_type=ActivityType.TASK_PROGRESS.value,
            **metrics
        )


# Convenience function to get a tracker instance
def get_development_tracker(source: str = "development_tracker") -> DevelopmentTracker:
    """Get a DevelopmentTracker instance for the given source."""
    return DevelopmentTracker(source)


if __name__ == "__main__":
    # Example usage
    tracker = get_development_tracker("dev_tracker_demo")
    tracker.log_task_start("demo-001", "Create development tracker utility")
    tracker.log_task_progress("demo-001", "Implemented basic logging", progress_percent=50)
    tracker.log_code_commit("demo-001", "abc123", "Initial commit of development tracker")
    tracker.log_task_complete("demo-001", "Create development tracker utility")
    tracker.log_todo_progress()
    tracker.log_velocity_metrics()