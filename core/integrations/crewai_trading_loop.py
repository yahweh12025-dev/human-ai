"""
CrewAI-based trading improvement loop — mirrors the Human-AI swarm's
Hermes -> OpenCode -> PiDev review pipeline as a formal CrewAI Crew.

crewAI (~22k stars): https://github.com/crewAIInc/crewAI

Architecture:
  - Hermes Agent  : Architect — strategy design, improvement proposals
  - OpenCode Agent: Implementer — code analysis and refactoring tasks
  - PiDev Agent   : Guardian — security audit, verification, risk assessment

This Crew mirrors the existing automode loop but provides structured
multi-agent task delegation with built-in peer review and output chaining.

Usage:
    from core.integrations.crewai_trading_loop import TradingImprovementCrew

    crew = TradingImprovementCrew()
    result = crew.run_improvement_cycle(
        focus="EA v9 XAUUSD drawdown management",
        code_snippet="..."
    )
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import BaseTool
    CREWAI_OK = True
    logger.info("crewai import: OK (v%s)", __import__("crewai").__version__)
except ImportError:
    CREWAI_OK = False
    logger.warning("crewai not installed — run: pip install crewai")
    # Define stubs so the module is importable
    Agent = Task = Crew = Process = None  # type: ignore
    BaseTool = object  # type: ignore


def _build_llm(provider: str = "openrouter", model: str = "openai/gpt-4o-mini"):
    """Build an LLM instance for CrewAI agents using available provider."""
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    if provider == "openrouter" and openrouter_key:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model,
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.2,
            )
        except ImportError:
            logger.warning("langchain_openai not available, trying groq")

    if groq_key:
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_key, temperature=0.2)
        except ImportError:
            pass

    # CrewAI also supports its own LLM wrapper
    if openrouter_key:
        try:
            from crewai import LLM
            return LLM(
                model=f"openrouter/{model}",
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1",
            )
        except (ImportError, Exception):
            pass

    return None  # Agents will use OPENAI_API_KEY env var by default


class TradingImprovementCrew:
    """
    A CrewAI Crew that replicates the Human-AI swarm's
    Hermes -> OpenCode -> PiDev improvement loop.

    Roles:
      - Hermes (Architect): Identifies trading strategy improvement opportunities
      - OpenCode (Implementer): Proposes concrete code changes
      - PiDev (Guardian): Audits changes for safety, correctness, and risk compliance
    """

    def __init__(
        self,
        llm_provider: str = "openrouter",
        model: str = "openai/gpt-4o-mini",
        verbose: bool = False,
    ):
        if not CREWAI_OK:
            raise RuntimeError(
                "crewai not installed. Run: pip install crewai"
            )
        self.verbose = verbose
        self.llm = _build_llm(llm_provider, model)
        self._crew: Optional[Crew] = None

    def _make_agents(self) -> tuple:
        """Instantiate the three core swarm agents as CrewAI Agents."""
        common = {"llm": self.llm, "verbose": self.verbose, "allow_delegation": False}

        hermes = Agent(
            role="Hermes — Trading Strategy Architect",
            goal=(
                "Identify high-impact improvements to the trading swarm's EA v9 and "
                "Binance v7 strategies. Propose specific, measurable changes that improve "
                "risk-adjusted returns while maintaining prop-firm compliance "
                "(3% daily / 5% max drawdown / 0.05L hard cap)."
            ),
            backstory=(
                "You are Hermes, the senior architect of the Human-AI trading swarm. "
                "You have deep expertise in metals trading (XAUUSD/XAGUSD), crypto scalping "
                "(BTC/ETH/BNB/SOL), and multi-agent system design. You think in terms of "
                "systems, edge cases, and risk-adjusted returns."
            ),
            **common,
        )

        opencode = Agent(
            role="OpenCode — Trading Implementation Engine",
            goal=(
                "Translate improvement proposals from Hermes into precise, production-ready "
                "Python code changes. Provide exact diffs, new function signatures, and "
                "integration points with the existing EA v9 / Binance v7 codebase."
            ),
            backstory=(
                "You are OpenCode, the implementation engine of the Human-AI swarm. "
                "You excel at Python refactoring, algorithmic trading patterns, and "
                "writing clean, testable code. You never break existing functionality "
                "without a migration path."
            ),
            **common,
        )

        pidev = Agent(
            role="PiDev — Security Guardian & Risk Auditor",
            goal=(
                "Audit every proposed code change for: (1) security vulnerabilities, "
                "(2) prop-firm compliance violations, (3) logic errors that could cause "
                "runaway losses, (4) missing circuit breakers. Approve or reject with "
                "detailed justification."
            ),
            backstory=(
                "You are PiDev, the guardian of the Human-AI swarm. You perform rigorous "
                "code review with a trading-risk lens. You know the dead-man switch logic, "
                "the 3%/5% drawdown limits, and the 0.05L hard cap. You flag anything that "
                "could cause unexpected losses or API abuse."
            ),
            **common,
        )

        return hermes, opencode, pidev

    def _make_tasks(
        self,
        hermes: "Agent",
        opencode: "Agent",
        pidev: "Agent",
        focus: str,
        code_snippet: str = "",
    ) -> list:
        """Build the three-stage task chain."""
        snippet_block = f"\n\nCode under review:\n```python\n{code_snippet}\n```" if code_snippet else ""

        task_hermes = Task(
            description=(
                f"Analyze the following trading improvement focus area and produce a "
                f"structured improvement proposal.\n\nFocus: {focus}{snippet_block}\n\n"
                "Your output must include:\n"
                "1. Root cause analysis (what is suboptimal and why)\n"
                "2. Proposed improvement (specific, actionable)\n"
                "3. Expected impact on Sharpe ratio / drawdown / win rate\n"
                "4. Dependencies or risks of the change\n"
                "5. Priority (HIGH / MEDIUM / LOW)"
            ),
            expected_output=(
                "A structured improvement proposal with root cause, proposed change, "
                "impact estimate, dependencies, and priority level."
            ),
            agent=hermes,
        )

        task_opencode = Task(
            description=(
                "Based on Hermes' improvement proposal, implement the change as Python code.\n\n"
                "Your output must include:\n"
                "1. The exact Python code change (diff format preferred)\n"
                "2. New function/class signatures if applicable\n"
                "3. Integration notes (which files to modify)\n"
                "4. Unit test sketch for the new behavior\n"
                "5. Rollback instructions if the change needs reverting"
            ),
            expected_output=(
                "Python code implementation with diff, integration notes, test sketch, "
                "and rollback instructions."
            ),
            agent=opencode,
            context=[task_hermes],
        )

        task_pidev = Task(
            description=(
                "Audit the code change proposed by OpenCode.\n\n"
                "Check for:\n"
                "1. Security issues (injection, secret leakage, API key exposure)\n"
                "2. Prop-firm compliance (drawdown limits, position size caps)\n"
                "3. Logic errors or off-by-one errors in risk calculations\n"
                "4. Missing circuit breakers or error handlers\n"
                "5. Performance regressions\n\n"
                "Output: APPROVED / APPROVED_WITH_CONDITIONS / REJECTED with full justification."
            ),
            expected_output=(
                "Audit verdict (APPROVED / APPROVED_WITH_CONDITIONS / REJECTED) with "
                "detailed finding list and required changes if conditional."
            ),
            agent=pidev,
            context=[task_hermes, task_opencode],
        )

        return [task_hermes, task_opencode, task_pidev]

    def run_improvement_cycle(
        self,
        focus: str,
        code_snippet: str = "",
        process: str = "sequential",
    ) -> dict:
        """
        Run the full Hermes -> OpenCode -> PiDev improvement cycle.

        Args:
            focus: Description of the trading area to improve
            code_snippet: Optional Python code block to analyze
            process: "sequential" (default) or "hierarchical"

        Returns:
            dict with crew output and individual agent results
        """
        hermes, opencode, pidev = self._make_agents()
        tasks = self._make_tasks(hermes, opencode, pidev, focus, code_snippet)

        crew_process = Process.sequential if process == "sequential" else Process.hierarchical

        crew = Crew(
            agents=[hermes, opencode, pidev],
            tasks=tasks,
            process=crew_process,
            verbose=self.verbose,
        )

        try:
            result = crew.kickoff()
            return {
                "status": "success",
                "focus": focus,
                "process": process,
                "output": str(result),
                "tasks_output": [str(t.output) for t in tasks if hasattr(t, "output") and t.output],
                "source": "crewai-trading-loop",
            }
        except Exception as exc:
            logger.error("CrewAI improvement cycle error: %s", exc)
            return {
                "status": "error",
                "focus": focus,
                "error": str(exc),
                "source": "crewai-trading-loop",
            }

    def run_code_review(self, code: str, file_path: str = "unknown") -> dict:
        """
        Shortcut: run only PiDev code review (single-agent task).

        Useful for quick security/compliance audits without the full improvement cycle.
        """
        if not CREWAI_OK:
            return {"error": "crewai not installed"}

        _, _, pidev = self._make_agents()

        review_task = Task(
            description=(
                f"Perform a comprehensive security and trading-risk audit of the following "
                f"file: {file_path}\n\n```python\n{code}\n```\n\n"
                "Check for security issues, prop-firm compliance, logic errors, and missing safeguards."
            ),
            expected_output="Security audit report with APPROVED/REJECTED verdict and finding list.",
            agent=pidev,
        )

        crew = Crew(agents=[pidev], tasks=[review_task], process=Process.sequential, verbose=self.verbose)
        try:
            result = crew.kickoff()
            return {"status": "success", "verdict": str(result), "file": file_path, "source": "crewai-pidev-review"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "file": file_path}

    @property
    def status(self) -> dict:
        return {
            "crewai_available": CREWAI_OK,
            "crewai_version": __import__("crewai").__version__ if CREWAI_OK else None,
            "agents": ["Hermes (Architect)", "OpenCode (Implementer)", "PiDev (Guardian)"],
            "process_modes": ["sequential", "hierarchical"],
            "source_repo": "https://github.com/crewAIInc/crewAI",
            "stars": "~22k",
        }


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

def run_trading_improvement(
    focus: str,
    code_snippet: str = "",
    model: str = "openai/gpt-4o-mini",
    verbose: bool = False,
) -> dict:
    """
    Convenience function: run the Hermes->OpenCode->PiDev crew on a trading improvement focus.

    Args:
        focus: What to improve (e.g. "EA v9 XAUUSD drawdown management")
        code_snippet: Optional Python code to analyze
        model: LLM model for OpenRouter routing
        verbose: Enable verbose CrewAI output

    Returns:
        dict with crew output and status
    """
    if not CREWAI_OK:
        return {
            "error": "crewai not installed",
            "install": "pip install crewai",
            "version_note": "crewai 1.14.4 installed — verify import with: python3 -c 'import crewai; print(crewai.__version__)'",
        }
    crew = TradingImprovementCrew(model=model, verbose=verbose)
    return crew.run_improvement_cycle(focus, code_snippet)


if __name__ == "__main__":
    import sys, json
    logging.basicConfig(level=logging.INFO)
    focus = sys.argv[1] if len(sys.argv) > 1 else "Improve EA v9 stop-loss tightening during high-volatility sessions"
    print(f"CrewAI Trading Loop status: {TradingImprovementCrew.status if not CREWAI_OK else 'crewai OK'}")
    print(f"\nRunning improvement cycle for: {focus}")
    result = run_trading_improvement(focus, verbose=True)
    print(json.dumps(result, indent=2, default=str))
