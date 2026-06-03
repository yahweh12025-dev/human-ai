"""
Microsoft AutoGen bridge — multi-agent conversation framework for the Human-AI swarm.

AutoGen (~40k stars): https://github.com/microsoft/autogen
Package: autogen-agentchat 0.7.5 + autogen-core 0.7.5 (installed via pyautogen)

AutoGen provides a different multi-agent primitive than CrewAI:
  - Agents communicate via structured message passing
  - Supports GroupChat (N-way conversation with a manager)
  - Supports nested chats and handoffs
  - Built for iterative code generation + review loops

Integration use cases in Human-AI swarm:
  1. Market research conversation: Research agent <-> Analyst agent
  2. Code generation loop: Hermes proposes -> OpenCode implements -> PiDev verifies
  3. Trading signal debate: Bull analyst <-> Bear analyst -> Trader decides

Usage:
    from core.integrations.autogen_swarm_bridge import AutoGenSwarmBridge, run_trading_debate

    bridge = AutoGenSwarmBridge()
    result = bridge.run_bull_bear_debate("XAUUSD", context="Gold at 3400, NFP tomorrow")
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from autogen_agentchat.agents import AssistantAgent, UserProxyAgent  # type: ignore
    from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat  # type: ignore
    from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination  # type: ignore
    from autogen_agentchat.messages import TextMessage  # type: ignore
    AUTOGEN_OK = True
    logger.info("autogen_agentchat import: OK")
except ImportError as exc:
    AUTOGEN_OK = False
    logger.warning("autogen_agentchat not fully importable: %s", exc)
    AssistantAgent = UserProxyAgent = None  # type: ignore
    RoundRobinGroupChat = SelectorGroupChat = None  # type: ignore
    TextMentionTermination = MaxMessageTermination = None  # type: ignore

try:
    from autogen_ext.models.openai import OpenAIChatCompletionClient  # type: ignore
    AUTOGEN_OPENAI_EXT = True
except ImportError:
    AUTOGEN_OPENAI_EXT = False


def _build_model_client(model: str = "gpt-4o-mini", provider: str = "openrouter"):
    """Build an AutoGen model client from available API keys."""
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    if AUTOGEN_OPENAI_EXT and openrouter_key:
        try:
            client = OpenAIChatCompletionClient(
                model=model,
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1",
            )
            logger.info("AutoGen model client: OpenRouter (%s)", model)
            return client
        except Exception as exc:
            logger.warning("OpenRouter client failed: %s", exc)

    # Fallback: standard OpenAI key
    openai_key = os.getenv("OPENAI_API_KEY")
    if AUTOGEN_OPENAI_EXT and openai_key:
        try:
            client = OpenAIChatCompletionClient(model=model, api_key=openai_key)
            logger.info("AutoGen model client: OpenAI (%s)", model)
            return client
        except Exception as exc:
            logger.warning("OpenAI client failed: %s", exc)

    logger.warning("No AutoGen model client available — set OPENROUTER_API_KEY or OPENAI_API_KEY")
    return None


class AutoGenSwarmBridge:
    """
    Bridge that exposes AutoGen multi-agent conversation primitives
    for use within the Human-AI swarm.

    Provides:
      - Bull/Bear trading debate (RoundRobin group chat)
      - Research <-> Analyst dialogue
      - Code review conversation loop
    """

    def __init__(self, model: str = "gpt-4o-mini", max_rounds: int = 6):
        if not AUTOGEN_OK:
            raise RuntimeError(
                "autogen_agentchat not available. Install: pip install pyautogen"
            )
        self.model = model
        self.max_rounds = max_rounds
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = _build_model_client(self.model)
        return self._client

    def run_bull_bear_debate(
        self,
        ticker: str,
        context: str = "",
        max_rounds: Optional[int] = None,
    ) -> dict:
        """
        Run a structured bull/bear debate about a ticker using AutoGen RoundRobin group chat.

        Args:
            ticker: Market symbol (e.g. "XAUUSD", "BTC/USDT")
            context: Additional market context (price levels, events, etc.)
            max_rounds: Max conversation rounds (default: self.max_rounds)

        Returns:
            dict with debate transcript and consensus signal
        """
        import asyncio

        client = self._get_client()
        if client is None:
            return {
                "error": "No model client available",
                "hint": "Set OPENROUTER_API_KEY or OPENAI_API_KEY",
            }

        rounds = max_rounds or self.max_rounds
        context_block = f"\nAdditional context: {context}" if context else ""

        bull_analyst = AssistantAgent(
            name="BullAnalyst",
            model_client=client,
            system_message=(
                f"You are a bullish analyst for {ticker}. "
                "Present the strongest bull case using technical and fundamental arguments. "
                "Be specific about price targets, catalysts, and risk/reward. "
                "Keep responses under 150 words."
            ),
        )

        bear_analyst = AssistantAgent(
            name="BearAnalyst",
            model_client=client,
            system_message=(
                f"You are a bearish analyst for {ticker}. "
                "Present the strongest bear case. Identify risks, resistance levels, "
                "and macro headwinds. Keep responses under 150 words."
            ),
        )

        trader = AssistantAgent(
            name="Trader",
            model_client=client,
            system_message=(
                f"You are the final decision-maker for {ticker} trades. "
                "After the analysts debate, synthesize their arguments and produce a "
                "final trading recommendation: BUY, SELL, or HOLD with confidence (0-1) "
                "and a brief rationale. End your message with 'DECISION_MADE'."
            ),
        )

        termination = TextMentionTermination("DECISION_MADE") | MaxMessageTermination(rounds)

        team = RoundRobinGroupChat(
            participants=[bull_analyst, bear_analyst, trader],
            termination_condition=termination,
        )

        initial_message = (
            f"Analyze {ticker} for a trading decision.{context_block}\n"
            "Bull analyst: present your case first."
        )

        try:
            async def _run():
                messages = []
                async for msg in team.run_stream(task=initial_message):
                    if hasattr(msg, "content"):
                        messages.append({
                            "agent": getattr(msg, "source", "unknown"),
                            "content": msg.content,
                        })
                return messages

            loop = asyncio.new_event_loop()
            messages = loop.run_until_complete(_run())
            loop.close()

            # Extract trader decision from last Trader message
            trader_msgs = [m for m in messages if m.get("agent") == "Trader"]
            final_decision = trader_msgs[-1]["content"] if trader_msgs else "No decision reached"

            return {
                "ticker": ticker,
                "debate_transcript": messages,
                "final_decision": final_decision,
                "rounds": len(messages),
                "source": "autogen-bull-bear-debate",
            }
        except Exception as exc:
            logger.error("AutoGen debate error: %s", exc)
            return {"error": str(exc), "ticker": ticker}

    def run_code_review_conversation(
        self,
        code: str,
        task_description: str,
        max_rounds: Optional[int] = None,
    ) -> dict:
        """
        Run a two-agent code generation and review conversation.

        Uses an OpenCode-style implementer and PiDev-style reviewer
        in a back-and-forth until the code passes review.
        """
        import asyncio

        client = self._get_client()
        if client is None:
            return {"error": "No model client available"}

        rounds = max_rounds or self.max_rounds

        implementer = AssistantAgent(
            name="OpenCode",
            model_client=client,
            system_message=(
                "You are OpenCode, a Python trading systems engineer. "
                "Implement code changes when requested and respond to review feedback. "
                "When your code passes review, end your message with 'IMPLEMENTATION_COMPLETE'."
            ),
        )

        reviewer = AssistantAgent(
            name="PiDev",
            model_client=client,
            system_message=(
                "You are PiDev, a security and trading-risk auditor. "
                "Review code for: security vulnerabilities, prop-firm compliance "
                "(3% daily / 5% max drawdown / 0.05L hard cap), logic errors, "
                "and missing circuit breakers. Say 'APPROVED' if the code is safe."
            ),
        )

        termination = (
            TextMentionTermination("IMPLEMENTATION_COMPLETE")
            | TextMentionTermination("APPROVED")
            | MaxMessageTermination(rounds)
        )

        team = RoundRobinGroupChat(
            participants=[implementer, reviewer],
            termination_condition=termination,
        )

        initial_message = (
            f"Task: {task_description}\n\nCurrent code:\n```python\n{code}\n```\n"
            "OpenCode: propose your implementation."
        )

        try:
            async def _run():
                messages = []
                async for msg in team.run_stream(task=initial_message):
                    if hasattr(msg, "content"):
                        messages.append({
                            "agent": getattr(msg, "source", "unknown"),
                            "content": msg.content,
                        })
                return messages

            loop = asyncio.new_event_loop()
            messages = loop.run_until_complete(_run())
            loop.close()

            approved = any("APPROVED" in m.get("content", "") for m in messages)
            return {
                "task": task_description,
                "conversation": messages,
                "approved": approved,
                "rounds": len(messages),
                "source": "autogen-code-review",
            }
        except Exception as exc:
            logger.error("AutoGen code review error: %s", exc)
            return {"error": str(exc), "task": task_description}

    @property
    def status(self) -> dict:
        return {
            "autogen_available": AUTOGEN_OK,
            "autogen_openai_ext": AUTOGEN_OPENAI_EXT,
            "autogen_version": "0.7.5",
            "capabilities": ["bull_bear_debate", "code_review_conversation"],
            "source_repo": "https://github.com/microsoft/autogen",
            "stars": "~40k",
        }


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

def run_trading_debate(
    ticker: str,
    context: str = "",
    model: str = "gpt-4o-mini",
    max_rounds: int = 6,
) -> dict:
    """
    Convenience: run a bull/bear debate for a ticker using AutoGen.

    Args:
        ticker: Market symbol (e.g. "XAUUSD", "BTC/USDT")
        context: Market context string
        model: LLM model name
        max_rounds: Max conversation rounds

    Returns:
        dict with transcript and final trading decision
    """
    if not AUTOGEN_OK:
        return {
            "error": "autogen_agentchat not available",
            "install": "pip install pyautogen",
            "note": "pyautogen 0.10.0 is installed — verify: python3 -c 'from autogen_agentchat.agents import AssistantAgent'",
        }
    bridge = AutoGenSwarmBridge(model=model, max_rounds=max_rounds)
    return bridge.run_bull_bear_debate(ticker, context)


if __name__ == "__main__":
    import sys, json, asyncio
    logging.basicConfig(level=logging.INFO)
    ticker = sys.argv[1] if len(sys.argv) > 1 else "XAUUSD"
    bridge = AutoGenSwarmBridge()
    print(f"AutoGen bridge status: {bridge.status}")
    print(f"\nRunning bull/bear debate for {ticker}...")
    result = run_trading_debate(ticker)
    print(json.dumps(result, indent=2, default=str))
