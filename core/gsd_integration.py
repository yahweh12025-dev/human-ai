"""
GSD Integration — core/gsd_integration.py
==========================================
Exposes GSD (Get Shit Done) skill invocation as a Python function so that
automode.py and other orchestration code can trigger GSD workflows
programmatically via subprocess.

GSD is a meta-prompting system installed at:
  ~/.opencode/get-shit-done/            — runtime workflows
  ~/.opencode/skills/gsd-*/            — individual skill modules

This module does NOT require Node/Bun at import time. Subprocesses are only
spawned when invoke_gsd_skill() is called.

Usage from automode:
    from core.gsd_integration import invoke_gsd_skill, GSD_SKILL_MAP
    result = invoke_gsd_skill("gsd-plan-phase", context="Improve EA signal logic")
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_GSD_INSTALL_DIR = Path.home() / ".opencode" / "get-shit-done"
_GSD_SKILLS_DIR  = Path.home() / ".opencode" / "skills"
_LOG_DIR         = _PROJECT_ROOT / "data" / "logs"

# ── GSD skill name → human description mapping ────────────────────────────────
# Subset relevant to the human-ai swarm. Full list: ~/.opencode/skills/gsd-*/

GSD_SKILL_MAP: dict[str, str] = {
    # Planning
    "gsd-plan-phase":        "Create detailed phase plan (PLAN.md) with verification loop",
    "gsd-discuss-phase":     "Gather phase context through adaptive questioning before planning",
    "gsd-spec-phase":        "Clarify WHAT a phase delivers with ambiguity scoring",
    "gsd-ai-integration-phase": "Generate AI-SPEC.md design contract for AI-system phases",
    # Execution
    "gsd-execute-phase":     "Execute all plans in a phase with wave-based parallelisation",
    "gsd-fast":              "Execute a trivial task inline — no subagents, no planning overhead",
    "gsd-quick":             "Execute a quick task with GSD guarantees but skip optional agents",
    # Review / Quality
    "gsd-code-review":       "Review source files changed during a phase",
    "gsd-audit-fix":         "Autonomous audit-to-fix pipeline — find issues, classify, fix, test, commit",
    "gsd-validate-phase":    "Retroactively audit and fill Nyquist validation gaps",
    "gsd-verify-work":       "Validate built features through conversational UAT",
    "gsd-review":            "Request cross-AI peer review of phase plans",
    # Milestones & progress
    "gsd-progress":          "Check progress, advance workflow, or dispatch freeform intent",
    "gsd-stats":             "Display project statistics",
    "gsd-complete-milestone":"Archive completed milestone and prepare for next version",
    # Context & documentation
    "gsd-docs-update":       "Generate or update project documentation verified against codebase",
    "gsd-map-codebase":      "Analyse codebase with parallel mapper agents",
    "gsd-graphify":          "Build, query, and inspect the project knowledge graph",
    # Debug / recovery
    "gsd-debug":             "Systematic debugging with persistent state across context resets",
    "gsd-forensics":         "Post-mortem investigation for failed GSD workflows",
    "gsd-resume-work":       "Resume work from previous session with full context restoration",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gsd_log(msg: str) -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = _LOG_DIR / "gsd_integration.log"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_file, "a") as fh:
            fh.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def is_gsd_installed() -> bool:
    """Return True if GSD runtime is present in ~/.opencode/get-shit-done/."""
    return (_GSD_INSTALL_DIR / "VERSION").exists()


def list_available_skills() -> list[str]:
    """Return sorted list of gsd-* skill names installed in ~/.opencode/skills/."""
    if not _GSD_SKILLS_DIR.exists():
        return []
    return sorted(
        p.name for p in _GSD_SKILLS_DIR.iterdir()
        if p.is_dir() and p.name.startswith("gsd-")
    )


def skill_exists(skill_name: str) -> bool:
    """Check whether a named GSD skill directory is present."""
    skill_dir = _GSD_SKILLS_DIR / skill_name
    return skill_dir.is_dir() and (skill_dir / "SKILL.md").exists()


# ── Main invocation function ──────────────────────────────────────────────────

def invoke_gsd_skill(
    skill_name: str,
    context: str = "",
    pow_file: Optional[str] = None,
    timeout: int = 300,
    dry_run: bool = False,
) -> dict:
    """
    Invoke a GSD skill by name using the `claude` CLI subprocess.

    GSD skills are Claude Code slash-commands. This function synthesises an
    equivalent prompt and passes it to the `claude` CLI so that the skill
    executes inside a headless Claude Code session.

    Args:
        skill_name: A key from GSD_SKILL_MAP (e.g. "gsd-plan-phase").
        context:    Additional context/instructions to pass to the skill.
        pow_file:   Optional path (relative to project root) where the skill
                    should write its proof-of-work output.
        timeout:    Subprocess timeout in seconds (default 300).
        dry_run:    If True, return the command that *would* be run without
                    actually executing it.

    Returns:
        dict with keys: skill, success, output, error, command, duration_s
    """
    if not skill_name.startswith("gsd-"):
        skill_name = f"gsd-{skill_name}"

    result: dict = {
        "skill":      skill_name,
        "success":    False,
        "output":     "",
        "error":      "",
        "command":    "",
        "duration_s": 0.0,
    }

    # Build the prompt that maps to /<skill_name> in Claude Code
    description = GSD_SKILL_MAP.get(skill_name, skill_name)
    prompt_parts = [f"/{skill_name}"]
    if context:
        prompt_parts.append(context)
    if pow_file:
        prompt_parts.append(f"Output results to {pow_file}")

    prompt = "\n".join(prompt_parts)

    # Locate the `claude` CLI
    claude_bin = subprocess.run(
        ["which", "claude"], capture_output=True, text=True
    ).stdout.strip() or "claude"

    cmd = [
        claude_bin,
        "--print",               # non-interactive output
        "--dangerously-skip-permissions",  # headless / CI mode
        "--add-dir", str(_PROJECT_ROOT),   # grant tool access to project root
        "--prompt", prompt,
    ]

    result["command"] = " ".join(cmd)

    _gsd_log(f"[INVOKE] {skill_name} | context={context[:60]} | dry_run={dry_run}")

    if dry_run:
        result["success"] = True
        result["output"]  = f"[dry-run] would run: {result['command']}"
        _gsd_log(f"[DRY-RUN] {skill_name}")
        return result

    if not is_gsd_installed():
        msg = (
            "GSD runtime not found at ~/.opencode/get-shit-done/. "
        )
        result["error"] = msg
        _gsd_log(f"[ERROR] GSD not installed — {msg}")
        return result

    start = datetime.now()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(_PROJECT_ROOT),
            env={**os.environ, "GSD_SKILL": skill_name},
        )
        result["duration_s"] = (datetime.now() - start).total_seconds()
        result["output"] = proc.stdout.strip()
        result["error"]  = proc.stderr.strip()
        result["success"] = proc.returncode == 0

        _gsd_log(
            f"[DONE] {skill_name} | rc={proc.returncode} | "
            f"duration={result['duration_s']:.1f}s | "
            f"output_len={len(result['output'])}"
        )

        # Optionally write a simple proof-of-work file
        if pow_file and result["success"]:
            _write_pow(pow_file, skill_name, context, result["output"])

    except subprocess.TimeoutExpired:
        result["duration_s"] = timeout
        result["error"] = f"Skill timed out after {timeout}s"
        _gsd_log(f"[TIMEOUT] {skill_name} after {timeout}s")
    except FileNotFoundError:
        result["error"] = f"Claude CLI not found at: {claude_bin}"
        _gsd_log(f"[ERROR] Claude CLI not found: {claude_bin}")
    except Exception as exc:
        result["error"] = str(exc)
        _gsd_log(f"[EXCEPTION] {skill_name}: {exc}")

    return result


def _write_pow(pow_file: str, skill_name: str, context: str, output: str) -> None:
    """Write a markdown proof-of-work file for a completed GSD skill run."""
    path = _PROJECT_ROOT / pow_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# GSD Skill POW — {skill_name}\n\n"
        f"**Date:** {datetime.now().isoformat()}\n"
        f"**Skill:** {skill_name}\n"
        f"**Context:** {context}\n\n"
        f"## Output\n\n{output}\n"
    )


# ── Convenience wrappers ──────────────────────────────────────────────────────

def gsd_plan_phase(phase_description: str, pow_file: Optional[str] = None) -> dict:
    """Ask GSD to plan a new phase from a description."""
    return invoke_gsd_skill("gsd-plan-phase", context=phase_description, pow_file=pow_file)


def gsd_code_review(file_glob: str = "", pow_file: Optional[str] = None) -> dict:
    """Run GSD code review over recently changed files."""
    ctx = f"Review files matching: {file_glob}" if file_glob else ""
    return invoke_gsd_skill("gsd-code-review", context=ctx, pow_file=pow_file)


def gsd_audit_fix(target: str = "", pow_file: Optional[str] = None) -> dict:
    """Run GSD autonomous audit-to-fix pipeline."""
    return invoke_gsd_skill("gsd-audit-fix", context=target, pow_file=pow_file)


def gsd_progress(intent: str = "", pow_file: Optional[str] = None) -> dict:
    """Check GSD project progress or dispatch a freeform intent."""
    return invoke_gsd_skill("gsd-progress", context=intent, pow_file=pow_file)


# ── CLI / smoke-test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GSD skill integration smoke-test")
    parser.add_argument("skill", nargs="?", default="gsd-progress",
                        help="GSD skill to invoke (default: gsd-progress)")
    parser.add_argument("--context", default="", help="Additional context")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print command without executing")
    args = parser.parse_args()

    print(f"GSD installed: {is_gsd_installed()}")
    print(f"Available GSD skills: {len(list_available_skills())}")
    print()

    r = invoke_gsd_skill(args.skill, context=args.context, dry_run=args.dry_run)
    print(json.dumps(r, indent=2))
