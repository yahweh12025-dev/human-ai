"""
OUTCOME JOURNAL SKILL
Purpose: To provide clear, transparent logging of the outcomes of agent tasks and features for effective human-AI collaboration and auditability.
This skill focuses on WHAT was achieved, not HOW it was decided (which is covered by the master log).
Action: Automatically appends the outcome of a completed task, feature implementation, or significant event to OUTCOME_LOG.md in the repo root.
"""
import os
from datetime import datetime
from pathlib import Path

# --- Configuration ---
PROJECT_ROOT = Path("/home/ubuntu/human-ai")
OUTCOME_LOG = PROJECT_ROOT / "OUTCOME_LOG.md"

def _init_log():
    """Ensures the outcome log exists with a header."""
    if not OUTCOME_LOG.exists():
        OUTCOME_LOG.write_text("# OUTCOME LOG\n\n*An immutable, append-only log of the outcomes of completed tasks, features, and events for transparency and human-AI collaboration.*\n\n---\n\n")

def log_outcome(agent_name: str, task_or_feature: str, outcome: str, details: str = ""):
    """
    Logs the outcome of a task or feature to the outcome log.
    Args:
        agent_name (str): The name of the agent or system responsible (e.g., "Hermes", "OpenClaw Autopilot", "Linter-Fixer").
        task_or_feature (str): A clear description of the task or feature that was completed (e.g., "Implemented Perplexity Browser Integration", "Fixed syntax error in repo_reviewer_agent.py").
        outcome (str): The result (e.g., "SUCCESS", "FAILURE", "PARTIAL_SUCCESS").
        details (str): Optional additional context or details about the outcome.
    """
    _init_log()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"## [{timestamp}] {agent_name} - OUTCOME: {task_or_feature}\n"
    log_entry += f"**Result**: {outcome}\n"
    if details:
        log_entry += f"**Details**: {details}\n"
    log_entry += f"\n---\n\n"
    with open(OUTCOME_LOG, "a") as f:
        f.write(log_entry)

# --- Example Usage (for testing) ---
if __name__ == "__main__":
    log_outcome(
        agent_name="Hermes",
        task_or_feature="Integrated GenericAgent into AntFarm Orchestration",
        outcome="SUCCESS"
    )
    log_outcome(
        agent_name="OpenClaw Autopilot",
        task_or_feature="Fixed path-resilience in autopilot script",
        outcome="SUCCESS",
        details="Updated script to dynamically locate triage/test scripts in root and scripts_archive/."
    )
    print(f"Outcome log written to {OUTCOME_LOG}")