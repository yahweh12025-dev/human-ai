"""
PAI Agent — agents/pai_agent.py
================================
Wraps Daniel Miessler's Personal AI Infrastructure (PAI) Life OS system so
that automode.py can invoke PAI skills as first-class tasks within the
human-ai swarm.

PAI is a Claude Code skill/hook system already installed at:
  ~/.claude/skills/<SkillName>/     — 45+ skills (Research, ExtractWisdom, etc.)
  ~/.claude/hooks/                  — lifecycle hooks (session, prompt guard, etc.)
  ~/.claude/PAI/                    — ALGORITHM, MEMORY, USER data

This module provides:
  - PAIAgent.execute_task()   — task-dict interface matching automode.py
  - invoke_pai_skill()        — low-level skill invocation via `claude` CLI
  - PAI_SKILL_MAP             — canonical skill name → description registry
  - Preconfigured convenience wrappers for the most useful PAI skills

API Key:
  PAI itself does not require NVIDIA_API_KEY — it runs entirely through the
  Claude API/subscription. The NVIDIA_API_KEY from .env is available in the
  environment for any PAI skill that might use NIM-hosted models (e.g. USMetrics
  economic analysis, or any future Nemotron-based skill).

  Keys are ALWAYS read from environment — never hardcoded.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ── Path setup ────────────────────────────────────────────────────────────────

_PROJECT_ROOT  = Path(__file__).resolve().parents[1]
_PAI_DIR       = Path.home() / ".opencode" / "PAI"
_SKILLS_DIR    = Path.home() / ".opencode" / "skills"
_LOG_DIR       = _PROJECT_ROOT / "data" / "logs"

# Load .env keys into the environment if not already present
_DOT_ENV = _PROJECT_ROOT / ".env"
if _DOT_ENV.exists():
    for _line in _DOT_ENV.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _, _val = _line.partition("=")
            if _key not in os.environ:
                os.environ[_key] = _val.strip()

# ── PAI skill registry ────────────────────────────────────────────────────────
# Curated subset of the 45 PAI skills relevant to the human-ai swarm.
# Full list: ~/.claude/skills/

PAI_SKILL_MAP: Dict[str, str] = {
    # Research & Intelligence
    "Research":         "Multi-depth research: Quick / Standard / Extensive / Deep Investigation",
    "ExtractWisdom":    "Content-adaptive wisdom extraction from articles, videos, podcasts",
    "ExtractAlpha":     "Extract highest-signal insights from research material",
    "ContextSearch":    "2-phase prior PAI work search across sessions",
    # Analysis & Thinking
    "FirstPrinciples":  "Physics-style deconstruct/challenge/rebuild reasoning",
    "SystemsThinking":  "Causal loops, archetypes, Meadows leverage points",
    "RootCauseAnalysis":"5-Whys, Fishbone, Postmortem, FaultTree analysis",
    "ApertureOscillation": "Tactical/strategic scope oscillation for design decisions",
    "IterativeDepth":   "Multi-angle exploration across lens rotations",
    # Strategy & Goals
    "Telos":            "Life OS: read/update goals, beliefs, wisdom, challenges",
    "ISA":              "Ideal State Artifact — articulate done criteria for any project",
    "Council":          "Multi-agent debate with visible transcripts",
    "RedTeam":          "32-agent adversarial stress-test",
    # Content & Creation
    "Ideate":           "9-phase evolutionary idea generation engine",
    "BeCreative":       "Verbalized Sampling divergent ideation",
    "WriteStory":       "Story writing assistance",
    "Fabric":           "240+ specialized prompt patterns (extract_wisdom, summarize, etc.)",
    # Security & Audit
    "WorldThreatModel": "11-horizon world threat model stress-test",
    "Evals":            "AI agent evaluation: code/model/human grader scoring",
    # Utility
    "Knowledge":        "Archive ideas, people, companies, research to MEMORY/KNOWLEDGE/",
    "Delegate":         "Parallelise work via 6 patterns: subagents, worktrees, teams",
    "PAIUpgrade":       "Upgrade PAI to latest version",
}

# Skills that can benefit from NVIDIA_API_KEY (NIM-hosted inference)
_NVIDIA_AWARE_SKILLS = {"USMetrics", "Research", "ExtractWisdom"}


# ── Logging helper ────────────────────────────────────────────────────────────

def _pai_log(msg: str) -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = _LOG_DIR / "pai_agent.log"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_file, "a") as fh:
            fh.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


# ── Status helpers ────────────────────────────────────────────────────────────

def is_pai_installed() -> bool:
    """Return True if PAI skills are present in ~/.claude/skills/.

    The legacy PAI runtime directory (~/.claude/PAI/ALGORITHM) is optional;
    what matters is that the skill directories exist in ~/.claude/skills/.
    """
    # Primary check: core skills present
    core_skills = ("Research", "ExtractWisdom", "RootCauseAnalysis")
    if all((_SKILLS_DIR / s / "SKILL.md").exists() for s in core_skills):
        return True
    # Fallback: legacy PAI ALGORITHM dir
    return (_PAI_DIR / "ALGORITHM").exists()


def skill_installed(skill_name: str) -> bool:
    """Check if a named PAI skill is present in ~/.claude/skills/."""
    return (_SKILLS_DIR / skill_name / "SKILL.md").exists()


def list_installed_skills() -> List[str]:
    """Return sorted list of all PAI skills installed in ~/.claude/skills/."""
    if not _SKILLS_DIR.exists():
        return []
    return sorted(
        p.name for p in _SKILLS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith("gsd-")
    )


# ── Core invocation ───────────────────────────────────────────────────────────

def invoke_pai_skill(
    skill_name: str,
    workflow: str = "",
    context: str = "",
    pow_file: Optional[str] = None,
    timeout: int = 300,
    dry_run: bool = False,
) -> dict:
    """
    Invoke a PAI skill via the `claude` CLI subprocess.

    PAI skills are Claude Code Skill tool invocations. This function
    constructs an equivalent prompt and passes it to the `claude` CLI so
    that the skill executes inside a headless Claude Code session.

    Args:
        skill_name: Key from PAI_SKILL_MAP (e.g. "Research", "ExtractWisdom").
        workflow:   Optional workflow within the skill (e.g. "QuickResearch").
        context:    Topic / instructions passed to the skill.
        pow_file:   Optional path (relative to project root) for output.
        timeout:    Subprocess timeout in seconds.
        dry_run:    If True, return the command that *would* run.

    Returns:
        dict: skill, success, output, error, command, duration_s
    """
    result: dict = {
        "skill":      skill_name,
        "workflow":   workflow,
        "success":    False,
        "output":     "",
        "error":      "",
        "command":    "",
        "duration_s": 0.0,
    }

    # Build the prompt
    prompt_parts = [f"Invoke the {skill_name} PAI skill."]
    if workflow:
        prompt_parts.append(f"Use the {workflow} workflow.")
    if context:
        prompt_parts.append(context)
    if pow_file:
        prompt_parts.append(f"Save your output to {pow_file}.")
    prompt = " ".join(prompt_parts)

    # Locate `claude` CLI
    claude_bin = (
        subprocess.run(["which", "claude"], capture_output=True, text=True).stdout.strip()
        or "claude"
    )

    cmd = [
        claude_bin,
        "--print",
        "--dangerously-skip-permissions",
        "--add-dir", str(_PROJECT_ROOT),   # grant tool access to project root
        "--prompt", prompt,
    ]
    result["command"] = " ".join(cmd)

    # Pass NVIDIA_API_KEY and OPENROUTER_API_KEY through env if present
    run_env = {**os.environ}
    for _key in ("NVIDIA_API_KEY", "NVIDIA_MODEL", "OPENROUTER_API_KEY"):
        val = os.getenv(_key)
        if val:
            run_env[_key] = val

    _pai_log(
        f"[INVOKE] {skill_name}/{workflow or 'default'} | "
        f"context={context[:60]} | dry_run={dry_run}"
    )

    if dry_run:
        result["success"] = True
        result["output"]  = f"[dry-run] would run: {result['command']}"
        return result

    if not is_pai_installed():
        result["error"] = (
            "PAI not found at ~/.claude/PAI/. "
            "Install via: curl -sSL https://ourpai.ai/install.sh | bash"
        )
        _pai_log(f"[ERROR] PAI not installed")
        return result

    start = datetime.now()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(_PROJECT_ROOT),
            env=run_env,
        )
        result["duration_s"] = (datetime.now() - start).total_seconds()
        result["output"]  = proc.stdout.strip()
        result["error"]   = proc.stderr.strip()
        result["success"] = proc.returncode == 0

        _pai_log(
            f"[DONE] {skill_name} | rc={proc.returncode} | "
            f"duration={result['duration_s']:.1f}s"
        )

        if pow_file and result["success"]:
            _write_pow(pow_file, skill_name, workflow, context, result["output"])

    except subprocess.TimeoutExpired:
        result["duration_s"] = float(timeout)
        result["error"] = f"PAI skill timed out after {timeout}s"
        _pai_log(f"[TIMEOUT] {skill_name} after {timeout}s")
    except FileNotFoundError:
        result["error"] = f"Claude CLI not found: {claude_bin}"
        _pai_log(f"[ERROR] Claude CLI not found: {claude_bin}")
    except Exception as exc:
        result["error"] = str(exc)
        _pai_log(f"[EXCEPTION] {skill_name}: {exc}")

    return result


def _write_pow(
    pow_file: str,
    skill_name: str,
    workflow: str,
    context: str,
    output: str,
) -> None:
    path = _PROJECT_ROOT / pow_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# PAI Skill POW — {skill_name}\n\n"
        f"**Date:** {datetime.now().isoformat()}\n"
        f"**Skill:** {skill_name}\n"
        f"**Workflow:** {workflow or 'default'}\n"
        f"**Context:** {context}\n\n"
        f"## Output\n\n{output}\n"
    )


# ── PAIAgent class — task-dict interface for automode.py ─────────────────────

class PAIAgent:
    """
    Wraps PAI skill invocation in the task-dict interface used by automode.py.

    Task dict shape:
        {
            "id":       str,
            "task":     str,         # freeform description; may include skill hint
            "agent":    "pai",
            "priority": int,
            "pow_file": str | None,  # optional output path
            "pai_skill":    str | None,  # override skill selection
            "pai_workflow": str | None,  # override workflow
        }
    """

    # Keyword → PAI skill heuristic routing table
    SKILL_HINTS: Dict[str, str] = {
        "research":          "Research",
        "investigate":       "Research",
        "extract wisdom":    "ExtractWisdom",
        "extract insights":  "ExtractWisdom",
        "root cause":        "RootCauseAnalysis",
        "why did":           "RootCauseAnalysis",
        "5 whys":            "RootCauseAnalysis",
        "systems thinking":  "SystemsThinking",
        "threat model":      "WorldThreatModel",
        "world model":       "WorldThreatModel",
        "ideate":            "Ideate",
        "brainstorm":        "BeCreative",
        "first principles":  "FirstPrinciples",
        "red team":          "RedTeam",
        "knowledge":         "Knowledge",
        "archive":           "Knowledge",
        "telos":             "Telos",
        "goal":              "Telos",
        "ideal state":       "ISA",
        "isa":               "ISA",
        "debate":            "Council",
        "council":           "Council",
        "evals":             "Evals",
        "evaluate":          "Evals",
        "fabric":            "Fabric",
    }

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = project_root or _PROJECT_ROOT

    def _select_skill(self, task: Dict) -> tuple[str, str]:
        """
        Choose the best PAI skill and workflow for a given task dict.
        Returns (skill_name, workflow).
        """
        # Explicit override wins
        if task.get("pai_skill"):
            return task["pai_skill"], task.get("pai_workflow", "")

        task_text = task.get("task", "").lower()

        for kw, skill in self.SKILL_HINTS.items():
            if kw in task_text:
                return skill, ""

        # Default: general-purpose research
        return "Research", "QuickResearch"

    def execute_task(self, task: Dict) -> bool:
        """
        Execute a PAI task. Returns True on success.
        Matches the interface expected by automode._execute_*() handlers.
        """
        task_id   = task.get("id", "unknown")
        task_desc = task.get("task", "")
        pow_file  = task.get("pow_file")

        skill_name, workflow = self._select_skill(task)

        _pai_log(
            f"[TASK] {task_id} | skill={skill_name} | workflow={workflow} | "
            f"desc={task_desc[:80]}"
        )

        result = invoke_pai_skill(
            skill_name=skill_name,
            workflow=workflow,
            context=task_desc,
            pow_file=pow_file,
        )

        if result["success"]:
            _pai_log(f"[TASK DONE] {task_id} via PAI/{skill_name}")
        else:
            _pai_log(
                f"[TASK FAIL] {task_id} via PAI/{skill_name}: {result['error'][:120]}"
            )

        return result["success"]


# ── Convenience wrappers ──────────────────────────────────────────────────────

def pai_research(
    topic: str,
    depth: str = "standard",
    pow_file: Optional[str] = None,
) -> dict:
    """Run a PAI Research skill query at the specified depth."""
    workflow_map = {
        "quick":      "QuickResearch",
        "standard":   "",
        "extensive":  "ExtensiveResearch",
        "deep":       "DeepInvestigation",
    }
    workflow = workflow_map.get(depth.lower(), "")
    return invoke_pai_skill("Research", workflow=workflow, context=topic, pow_file=pow_file)


def pai_extract_wisdom(content_or_url: str, pow_file: Optional[str] = None) -> dict:
    """Run PAI ExtractWisdom on a URL or inline content."""
    return invoke_pai_skill(
        "ExtractWisdom", context=content_or_url, pow_file=pow_file
    )


def pai_root_cause(
    incident_description: str, pow_file: Optional[str] = None
) -> dict:
    """Run PAI RootCauseAnalysis on an incident description."""
    return invoke_pai_skill(
        "RootCauseAnalysis",
        workflow="FiveWhys",
        context=incident_description,
        pow_file=pow_file,
    )


def pai_world_threat_model(
    idea_or_strategy: str, pow_file: Optional[str] = None
) -> dict:
    """Run PAI WorldThreatModel against an idea or strategy."""
    return invoke_pai_skill(
        "WorldThreatModel",
        workflow="TestIdea",
        context=idea_or_strategy,
        pow_file=pow_file,
    )


# ── CLI / smoke-test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PAI agent smoke-test")
    parser.add_argument("skill", nargs="?", default="Research",
                        help="PAI skill to invoke (default: Research)")
    parser.add_argument("--workflow", default="", help="Skill workflow")
    parser.add_argument("--context", default="What are the top AI trading advances in 2025?",
                        help="Context/topic")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print command without executing")
    args = parser.parse_args()

    print(f"PAI installed:          {is_pai_installed()}")
    print(f"Total installed skills: {len(list_installed_skills())}")
    print(f"NVIDIA_API_KEY present: {bool(os.getenv('NVIDIA_API_KEY'))}")
    print()

    r = invoke_pai_skill(
        args.skill,
        workflow=args.workflow,
        context=args.context,
        dry_run=args.dry_run,
    )
    print(json.dumps(r, indent=2))
