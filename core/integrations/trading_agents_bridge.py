"""
Bridge to TradingAgents — LangGraph-based multi-agent trading swarm for market analysis.

TradingAgents (~71k stars): https://github.com/TauricResearch/TradingAgents
Published: arXiv 2412.20138

NOTE: The tradingagents PyPI package requires Python >= 3.12.
This bridge provides:
  1. A thin import wrapper (if tradingagents becomes available via py3.12 venv)
  2. A subprocess/API-style adapter for running TradingAgents analyses
  3. A compatible standalone analyst chain using LangChain (available now) that
     mirrors TradingAgents' analyst roles (Fundamentals, Sentiment, News, Technical)

Usage:
    from core.integrations.trading_agents_bridge import analyze_ticker, TradingAgentsBridge

    result = analyze_ticker("XAUUSD", analysis_type="technical")
"""

import os
import json
import logging
from typing import Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# --- Attempt native import (requires Python 3.12+) ---
try:
    from tradingagents.graph.trading_graph import TradingAgentsGraph  # type: ignore
    from tradingagents.default_config import DEFAULT_CONFIG  # type: ignore
    TRADING_AGENTS_OK = True
    logger.info("tradingagents native import: OK")
except ImportError:
    TRADING_AGENTS_OK = False
    logger.info("tradingagents not installed (requires Python >=3.12); using LangChain fallback")

# --- LangChain fallback (Python 3.11 compatible) ---
try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_OK = True
except ImportError:
    LANGCHAIN_OK = False
    logger.warning("langchain_core not available — analyst chains disabled")


# ---------------------------------------------------------------------------
# Analyst prompt templates mirroring TradingAgents' analyst roles
# ---------------------------------------------------------------------------

_TECHNICAL_ANALYST_PROMPT = ChatPromptTemplate.from_template(
    """You are a Technical Analyst specializing in price action and indicators.

Ticker: {ticker}
Date context: {date}
Market data: {market_data}

Analyze using:
- MACD and RSI divergence patterns
- Bollinger Band structure (squeeze / expansion)
- Support/resistance levels
- Session-specific context (ASIAN / LONDON / NY)

Return a structured JSON with keys:
  signal (BUY/SELL/HOLD), confidence (0-1), reasoning (string),
  key_levels (list), timeframe (string)
"""
) if LANGCHAIN_OK else None

_SENTIMENT_ANALYST_PROMPT = ChatPromptTemplate.from_template(
    """You are a Sentiment Analyst aggregating news and social signals.

Ticker: {ticker}
Date context: {date}
Headlines/context: {headlines}

Aggregate sentiment from:
- News headlines
- Macro economic events
- Risk-on / risk-off environment

Return structured JSON with keys:
  sentiment (BULLISH/BEARISH/NEUTRAL), score (-1.0 to 1.0),
  key_events (list), confidence (0-1)
"""
) if LANGCHAIN_OK else None

_FUNDAMENTALS_ANALYST_PROMPT = ChatPromptTemplate.from_template(
    """You are a Fundamentals Analyst evaluating intrinsic value drivers.

Ticker: {ticker}
Date context: {date}
Context: {context}

For metals/crypto, evaluate:
- Macro drivers (USD strength, inflation expectations, risk appetite)
- Supply/demand fundamentals
- Correlation with DXY, bonds, equities

Return structured JSON with keys:
  outlook (BULLISH/BEARISH/NEUTRAL), intrinsic_bias (string),
  key_factors (list), confidence (0-1)
"""
) if LANGCHAIN_OK else None


class TradingAgentsBridge:
    """
    Bridge class wrapping TradingAgents functionality.

    Provides native pass-through when tradingagents is installed (Python 3.12+),
    and a LangChain-based analyst chain as fallback for Python 3.11.
    """

    def __init__(self, llm_provider: str = "openrouter", model: str = "openai/gpt-4o-mini"):
        self.llm_provider = llm_provider
        self.model = model
        self._native_graph = None
        self._llm = None

    def _get_llm(self):
        """Lazy-load an LLM client from available providers."""
        if self._llm is not None:
            return self._llm

        if not LANGCHAIN_OK:
            raise RuntimeError("langchain_core not available — cannot build analyst chain")

        # Try OpenRouter first (project standard)
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            try:
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    model=self.model,
                    api_key=openrouter_key,
                    base_url="https://openrouter.ai/api/v1",
                    temperature=0.1,
                )
                logger.info("TradingAgentsBridge: using OpenRouter (%s)", self.model)
                return self._llm
            except ImportError:
                pass

        # Fallback: Groq
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                from langchain_groq import ChatGroq
                self._llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_key, temperature=0.1)
                logger.info("TradingAgentsBridge: using Groq fallback")
                return self._llm
            except ImportError:
                pass

        raise RuntimeError(
            "No LLM provider available. Set OPENROUTER_API_KEY or GROQ_API_KEY."
        )

    def _get_native_graph(self, config: Optional[dict] = None):
        """Initialize the native TradingAgents graph (requires Python 3.12+)."""
        if not TRADING_AGENTS_OK:
            raise RuntimeError(
                "tradingagents package not available (requires Python >=3.12). "
                "Install with: pip install tradingagents"
            )
        if self._native_graph is None:
            cfg = DEFAULT_CONFIG.copy()
            if config:
                cfg.update(config)
            # Wire up API keys from environment
            cfg.setdefault("openai_api_key", os.getenv("OPENROUTER_API_KEY", ""))
            self._native_graph = TradingAgentsGraph(debug=False, config=cfg)
        return self._native_graph

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_ticker_native(
        self,
        ticker: str,
        date: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> dict:
        """
        Run full TradingAgents multi-agent analysis (requires Python 3.12+).

        Returns the final state dict from the LangGraph workflow including
        analyst reports, researcher debates, trader decision, and risk assessment.
        """
        if not TRADING_AGENTS_OK:
            return {
                "error": "tradingagents not installed",
                "install": "pip install tradingagents  # requires Python >=3.12",
                "fallback": "Use analyze_ticker() for LangChain-based analysis",
            }
        graph = self._get_native_graph(config)
        analysis_date = date or datetime.now().strftime("%Y-%m-%d")
        final_state, decision = graph.propagate(ticker, analysis_date)
        return {
            "ticker": ticker,
            "date": analysis_date,
            "decision": decision,
            "state": final_state,
            "source": "tradingagents-native",
        }

    def analyze_ticker_langchain(
        self,
        ticker: str,
        date: Optional[str] = None,
        analysis_type: str = "technical",
        market_data: Optional[str] = None,
        headlines: Optional[str] = None,
        context: Optional[str] = None,
    ) -> dict:
        """
        Run a single-analyst LangChain chain mirroring TradingAgents' analyst roles.

        analysis_type options: "technical" | "sentiment" | "fundamentals"
        """
        if not LANGCHAIN_OK:
            return {"error": "langchain_core not available", "install": "pip install langchain-core"}

        llm = self._get_llm()
        date_str = date or datetime.now().strftime("%Y-%m-%d")

        prompt_map = {
            "technical": (_TECHNICAL_ANALYST_PROMPT, {"ticker": ticker, "date": date_str, "market_data": market_data or "not provided"}),
            "sentiment": (_SENTIMENT_ANALYST_PROMPT, {"ticker": ticker, "date": date_str, "headlines": headlines or "not provided"}),
            "fundamentals": (_FUNDAMENTALS_ANALYST_PROMPT, {"ticker": ticker, "date": date_str, "context": context or "not provided"}),
        }

        if analysis_type not in prompt_map:
            return {"error": f"Unknown analysis_type '{analysis_type}'. Use: technical, sentiment, fundamentals"}

        prompt, variables = prompt_map[analysis_type]
        chain = prompt | llm | StrOutputParser()

        try:
            raw = chain.invoke(variables)
            # Attempt JSON parse; store raw text on failure
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"raw_analysis": raw}
            return {
                "ticker": ticker,
                "date": date_str,
                "analysis_type": analysis_type,
                "result": parsed,
                "source": "langchain-fallback",
            }
        except Exception as exc:
            logger.error("TradingAgentsBridge analysis error: %s", exc)
            return {"error": str(exc), "ticker": ticker, "analysis_type": analysis_type}

    def analyze_ticker(
        self,
        ticker: str,
        date: Optional[str] = None,
        analysis_type: str = "technical",
        **kwargs: Any,
    ) -> dict:
        """
        Unified entry point: uses native TradingAgents if available, else LangChain fallback.

        Args:
            ticker: Market symbol, e.g. "XAUUSD", "BTC/USDT", "AAPL"
            date: Analysis date string "YYYY-MM-DD" (default: today)
            analysis_type: "technical" | "sentiment" | "fundamentals" (fallback only)
            **kwargs: Passed through to native graph config or fallback chain variables
        """
        if TRADING_AGENTS_OK:
            return self.analyze_ticker_native(ticker, date, config=kwargs.get("config"))
        return self.analyze_ticker_langchain(ticker, date, analysis_type=analysis_type, **kwargs)

    @property
    def status(self) -> dict:
        """Return integration status for health checks."""
        return {
            "tradingagents_native": TRADING_AGENTS_OK,
            "langchain_fallback": LANGCHAIN_OK,
            "python_version_constraint": "tradingagents requires Python >=3.12",
            "current_mode": "native" if TRADING_AGENTS_OK else ("langchain-fallback" if LANGCHAIN_OK else "unavailable"),
            "source_repo": "https://github.com/TauricResearch/TradingAgents",
            "stars": "~71k",
        }


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

_bridge: Optional[TradingAgentsBridge] = None


def analyze_ticker(
    ticker: str,
    date: Optional[str] = None,
    analysis_type: str = "technical",
    llm: str = "openai/gpt-4o-mini",
    **kwargs: Any,
) -> dict:
    """
    Module-level convenience: run TradingAgents analysis on a ticker.

    Args:
        ticker: Market symbol (e.g. "XAUUSD", "BTC/USDT")
        date:   Analysis date "YYYY-MM-DD" (default: today)
        analysis_type: "technical" | "sentiment" | "fundamentals"
        llm:    LLM model name for OpenRouter routing

    Returns:
        dict with analysis result, signal, and metadata
    """
    global _bridge
    if _bridge is None:
        _bridge = TradingAgentsBridge(model=llm)
    return _bridge.analyze_ticker(ticker, date=date, analysis_type=analysis_type, **kwargs)


def get_status() -> dict:
    """Return TradingAgents integration status."""
    global _bridge
    if _bridge is None:
        _bridge = TradingAgentsBridge()
    return _bridge.status


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    ticker = sys.argv[1] if len(sys.argv) > 1 else "XAUUSD"
    print(f"TradingAgents bridge status: {get_status()}")
    print(f"\nRunning technical analysis for {ticker}...")
    result = analyze_ticker(ticker, analysis_type="technical")
    print(json.dumps(result, indent=2, default=str))
