#!/usr/bin/env python3
"""
researcher_agent.py — GPT Researcher integration for Human-AI swarm.

Runs PARALLEL to the DeepSeek browser agent. Use for:
- Deep market research (XAUUSD, crypto, macro)
- Technology research (new trading strategies, agent frameworks)
- Cited multi-source research reports

DeepSeek browser agent: interactive, web browsing, social scraping
GPT Researcher: parallel source aggregation, 20+ sources, cited reports
"""

from __future__ import annotations
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env
_env = _PROJECT_ROOT / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

# GPT Researcher uses OPENAI_API_KEY by default, but we route via OpenRouter
# Set the env vars it needs
_OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
_LLM_PROVIDER = os.environ.get("GPT_RESEARCHER_LLM", "openai")  # can be "google" etc

# Point gpt-researcher to OpenRouter endpoint
if _OPENROUTER_KEY and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = _OPENROUTER_KEY
    os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"

_LOG_DIR = _PROJECT_ROOT / "data" / "logs"
_RESEARCH_DIR = _PROJECT_ROOT / "data" / "obsidian" / "knowledge" / "research"


def _log(msg: str):
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(_LOG_DIR / "researcher.log", "a") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[RESEARCHER] {msg}")


async def research_async(query: str, report_type: str = "research_report") -> str:
    """
    Run GPT Researcher async and return the report text.

    report_type options:
      - research_report: comprehensive multi-source report
      - outline_report: outline only (faster)
      - resource_report: just sources/links
      - custom_report: custom format
    """
    try:
        from gpt_researcher import GPTResearcher
        researcher = GPTResearcher(query=query, report_type=report_type)
        await researcher.conduct_research()
        report = await researcher.write_report()
        return report
    except ImportError:
        return f"[ERROR] gpt-researcher not installed. Run: pip install gpt-researcher"
    except Exception as e:
        _log(f"Research error: {e}")
        return f"[ERROR] Research failed: {e}"


def research(query: str, save_to: str = "", report_type: str = "research_report") -> str:
    """
    Synchronous wrapper for research_async.

    Args:
        query: Research question
        save_to: Optional path to save the report (relative to project root or absolute)
        report_type: research_report | outline_report | resource_report

    Returns:
        Report text
    """
    _log(f"Starting research: {query[:80]}...")

    try:
        report = asyncio.run(research_async(query, report_type))
    except Exception as e:
        _log(f"Async error: {e}")
        report = f"[ERROR] {e}"

    if save_to and report and not report.startswith("[ERROR]"):
        if save_to.startswith("/"):
            out_path = Path(save_to)
        else:
            out_path = _PROJECT_ROOT / save_to
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            f"# Research Report\n\n**Query:** {query}\n\n**Date:** {datetime.now().isoformat()}\n\n---\n\n{report}\n"
        )
        _log(f"Report saved to: {out_path}")

    _log(f"Research complete: {len(report)} chars")
    return report


def research_and_vault(query: str, filename: str = "", agent: str = "pai") -> str:
    """
    Research a topic and save to Obsidian vault knowledge/research/.
    Also logs the action to the agent's vault log.
    """
    from core.integrations.vault_logger import vault_log

    if not filename:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        slug = query[:40].lower().replace(" ", "_").replace("/", "_")
        filename = f"research_{ts}_{slug}.md"

    save_path = str(_RESEARCH_DIR / filename)
    report = research(query, save_to=save_path)

    vault_log(agent, "RESEARCH", f"GPT Researcher: {query[:60]}",
              data={"filename": filename, "chars": len(report), "query": query})

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GPT Researcher — parallel to DeepSeek browser agent")
    parser.add_argument("query", nargs="?", default="XAUUSD gold trading signal analysis 2026")
    parser.add_argument("--save", default="", help="Save report to path")
    parser.add_argument("--vault", action="store_true", help="Save to Obsidian vault knowledge/research/")
    parser.add_argument("--agent", default="pai", help="Agent name for vault logging")
    parser.add_argument("--type", default="research_report",
                        choices=["research_report", "outline_report", "resource_report"])
    args = parser.parse_args()

    if args.vault:
        result = research_and_vault(args.query, agent=args.agent)
    else:
        result = research(args.query, save_to=args.save, report_type=args.type)

    print("\n" + "=" * 60)
    print(result[:2000] + ("..." if len(result) > 2000 else ""))
