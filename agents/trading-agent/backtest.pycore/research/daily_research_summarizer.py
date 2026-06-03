#!/usr/bin/env python3
"""
T479: Automate daily collection and summarization of latest AI and finance
research papers from arXiv and other sources.

POW File: research/daily_research_summarizer.py

This module provides:
- ArXiv API querying for AI/ML and quantitative finance papers
- Abstract parsing and relevance scoring
- LLM-powered summarization with actionable insight extraction
- Daily digest generation with priority ranking
- Persistent storage of summaries for trend analysis
"""

import os
import sys
import json
import hashlib
import logging
import datetime
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

import requests

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.llm_router import query_llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("daily_research_summarizer")

# ArXiv categories relevant to the project
ARXIV_CATEGORIES = [
    "cs.AI",       # Artificial Intelligence
    "cs.LG",       # Machine Learning
    "cs.MA",       # Multi-Agent Systems
    "q-fin.TR",    # Trading and Market Microstructure
    "q-fin.PM",    # Portfolio Management
    "q-fin.ST",    # Statistical Finance
    "q-fin.CP",    # Computational Finance
    "q-fin.RM",    # Risk Management
    "stat.ML",     # Machine Learning (Stats)
]

ARXIV_API_BASE = "http://export.arxiv.org/api/query"
STORAGE_DIR = PROJECT_ROOT / "research" / "memory" / "daily_digests"


@dataclass
class Paper:
    """Represents a research paper from arXiv."""
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    categories: List[str]
    published: str
    link: str
    relevance_score: float = 0.0
    summary: str = ""
    actionable_insights: List[str] = field(default_factory=list)
    trading_relevance: str = ""


@dataclass
class DailyDigest:
    """Daily research digest with ranked papers and insights."""
    date: str
    total_papers_found: int
    papers_analyzed: int
    top_papers: List[Dict[str, Any]]
    key_themes: List[str]
    actionable_signals: List[str]
    generated_at: str = ""


class ArXivFetcher:
    """Fetches papers from the arXiv API."""

    def __init__(self, max_results_per_category: int = 10):
        self.max_results = max_results_per_category

    def fetch_recent_papers(self, categories: List[str],
                           days_back: int = 1) -> List[Paper]:
        """Fetch recent papers from specified arXiv categories."""
        all_papers = []
        seen_ids = set()

        for category in categories:
            try:
                papers = self._query_category(category, days_back)
                for paper in papers:
                    if paper.arxiv_id not in seen_ids:
                        seen_ids.add(paper.arxiv_id)
                        all_papers.append(paper)
            except Exception as e:
                logger.warning(f"Failed to fetch category {category}: {e}")

        logger.info(f"Fetched {len(all_papers)} unique papers from {len(categories)} categories")
        return all_papers

    def _query_category(self, category: str, days_back: int) -> List[Paper]:
        """Query a single arXiv category for recent papers."""
        query = f"cat:{category}"
        params = {
            "search_query": query,
            "start": 0,
            "max_results": self.max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        response = requests.get(ARXIV_API_BASE, params=params, timeout=30)
        response.raise_for_status()

        return self._parse_feed(response.text)

    def _parse_feed(self, xml_text: str) -> List[Paper]:
        """Parse ArXiv Atom feed XML into Paper objects."""
        papers = []
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        root = ET.fromstring(xml_text)
        entries = root.findall("atom:entry", ns)

        for entry in entries:
            try:
                arxiv_id_raw = entry.find("atom:id", ns).text
                arxiv_id = arxiv_id_raw.split("/abs/")[-1] if "/abs/" in arxiv_id_raw else arxiv_id_raw

                title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
                abstract = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
                published = entry.find("atom:published", ns).text

                authors = []
                for author_elem in entry.findall("atom:author", ns):
                    name = author_elem.find("atom:name", ns)
                    if name is not None:
                        authors.append(name.text)

                categories = []
                for cat_elem in entry.findall("atom:category", ns):
                    term = cat_elem.get("term")
                    if term:
                        categories.append(term)

                link = ""
                for link_elem in entry.findall("atom:link", ns):
                    if link_elem.get("type") == "text/html":
                        link = link_elem.get("href", "")
                        break
                if not link:
                    link = f"https://arxiv.org/abs/{arxiv_id}"

                papers.append(Paper(
                    arxiv_id=arxiv_id,
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    categories=categories,
                    published=published,
                    link=link,
                ))
            except Exception as e:
                logger.debug(f"Failed to parse entry: {e}")

        return papers


class RelevanceScorer:
    """Scores papers for relevance to the Human-AI project."""

    # Keywords with weights for relevance scoring
    HIGH_RELEVANCE_KEYWORDS = {
        "multi-agent": 3.0,
        "autonomous trading": 3.0,
        "algorithmic trading": 2.5,
        "reinforcement learning": 2.0,
        "market microstructure": 2.5,
        "portfolio optimization": 2.5,
        "swarm intelligence": 3.0,
        "agent communication": 2.5,
        "self-healing": 2.0,
        "anomaly detection": 2.0,
        "regime detection": 2.5,
        "market regime": 2.5,
        "alpha generation": 3.0,
        "signal processing": 1.5,
        "time series": 1.5,
        "transformer": 1.5,
        "attention mechanism": 1.5,
        "knowledge graph": 2.0,
        "verification": 1.5,
        "backtesting": 2.0,
        "risk management": 2.0,
        "natural language processing": 1.0,
        "large language model": 1.5,
        "llm agent": 2.5,
        "tool use": 2.0,
        "cryptocurrency": 2.0,
        "decentralized": 1.5,
        "sentiment analysis": 2.0,
        "alternative data": 2.0,
    }

    def score_papers(self, papers: List[Paper]) -> List[Paper]:
        """Score and rank papers by relevance."""
        for paper in papers:
            paper.relevance_score = self._compute_score(paper)

        papers.sort(key=lambda p: p.relevance_score, reverse=True)
        return papers

    def _compute_score(self, paper: Paper) -> float:
        """Compute relevance score for a single paper."""
        score = 0.0
        text = (paper.title + " " + paper.abstract).lower()

        for keyword, weight in self.HIGH_RELEVANCE_KEYWORDS.items():
            if keyword.lower() in text:
                score += weight

        # Bonus for quantitative finance categories
        qfin_cats = [c for c in paper.categories if c.startswith("q-fin")]
        score += len(qfin_cats) * 1.5

        # Bonus for multi-agent systems
        if "cs.MA" in paper.categories:
            score += 2.0

        return round(score, 2)


class PaperSummarizer:
    """Uses LLM to generate summaries and extract insights."""

    SYSTEM_PROMPT = """You are a research analyst for an autonomous multi-agent trading system.
Your job is to summarize academic papers and extract actionable insights for:
1. Algorithmic trading strategy improvement
2. Multi-agent system optimization
3. Market regime detection
4. Risk management enhancement

Be concise and focus on practical applicability."""

    def summarize_paper(self, paper: Paper) -> Paper:
        """Generate LLM-powered summary and insights for a paper."""
        prompt = f"""Analyze this research paper and provide:
1. A 2-3 sentence summary focused on practical implications
2. 1-3 actionable insights for an algorithmic trading system
3. A one-line assessment of trading strategy relevance (high/medium/low)

Title: {paper.title}
Authors: {', '.join(paper.authors[:5])}
Abstract: {paper.abstract}

Format your response as JSON:
{{
  "summary": "...",
  "actionable_insights": ["insight1", "insight2"],
  "trading_relevance": "high|medium|low: brief explanation"
}}"""

        try:
            response = query_llm(
                agent_name="hermes",
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                max_tokens=512,
                temperature=0.3,
            )

            # Parse JSON from response
            parsed = self._extract_json(response)
            if parsed:
                paper.summary = parsed.get("summary", "")
                paper.actionable_insights = parsed.get("actionable_insights", [])
                paper.trading_relevance = parsed.get("trading_relevance", "")
            else:
                # Fallback: use raw response as summary
                paper.summary = response[:500]
                paper.actionable_insights = []
                paper.trading_relevance = "unknown"

        except Exception as e:
            logger.warning(f"LLM summarization failed for {paper.arxiv_id}: {e}")
            paper.summary = self._fallback_summary(paper)
            paper.actionable_insights = []
            paper.trading_relevance = "unknown"

        return paper

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from LLM response text."""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block in response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

        return None

    def _fallback_summary(self, paper: Paper) -> str:
        """Generate basic summary without LLM."""
        abstract_sentences = paper.abstract.split(". ")
        if len(abstract_sentences) >= 2:
            return ". ".join(abstract_sentences[:2]) + "."
        return paper.abstract[:200]


class DigestGenerator:
    """Generates daily research digests."""

    def __init__(self, top_n: int = 10):
        self.top_n = top_n

    def generate_digest(self, papers: List[Paper], date: str) -> DailyDigest:
        """Generate a daily digest from scored and summarized papers."""
        top_papers = papers[:self.top_n]

        # Extract key themes
        key_themes = self._extract_themes(top_papers)

        # Collect actionable signals
        actionable_signals = []
        for paper in top_papers:
            actionable_signals.extend(paper.actionable_insights)

        digest = DailyDigest(
            date=date,
            total_papers_found=len(papers),
            papers_analyzed=len(top_papers),
            top_papers=[asdict(p) for p in top_papers],
            key_themes=key_themes,
            actionable_signals=actionable_signals[:20],
            generated_at=datetime.datetime.utcnow().isoformat(),
        )

        return digest

    def _extract_themes(self, papers: List[Paper]) -> List[str]:
        """Extract recurring themes from top papers."""
        theme_counts: Dict[str, int] = {}
        theme_keywords = [
            "reinforcement learning", "transformer", "attention",
            "multi-agent", "portfolio", "risk", "regime",
            "sentiment", "prediction", "optimization",
            "deep learning", "neural network", "time series",
            "volatility", "momentum", "mean reversion",
        ]

        for paper in papers:
            text = (paper.title + " " + paper.abstract).lower()
            for theme in theme_keywords:
                if theme in text:
                    theme_counts[theme] = theme_counts.get(theme, 0) + 1

        # Return themes sorted by frequency
        sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
        return [theme for theme, count in sorted_themes[:8] if count >= 1]


class DailyResearchSummarizer:
    """
    Main orchestrator for daily research paper collection and summarization.

    Usage:
        summarizer = DailyResearchSummarizer()
        digest = summarizer.run()
    """

    def __init__(self, categories: Optional[List[str]] = None,
                 max_results_per_category: int = 10,
                 top_n_papers: int = 10,
                 days_back: int = 1):
        self.categories = categories or ARXIV_CATEGORIES
        self.fetcher = ArXivFetcher(max_results_per_category)
        self.scorer = RelevanceScorer()
        self.summarizer = PaperSummarizer()
        self.digest_generator = DigestGenerator(top_n_papers)
        self.days_back = days_back
        self.top_n = top_n_papers

    def run(self, use_llm: bool = True) -> DailyDigest:
        """Execute the full daily research summarization pipeline."""
        today = datetime.date.today().isoformat()
        logger.info(f"Starting daily research summarization for {today}")

        # Step 1: Fetch papers
        logger.info("Fetching papers from arXiv...")
        papers = self.fetcher.fetch_recent_papers(self.categories, self.days_back)

        if not papers:
            logger.warning("No papers found. Generating empty digest.")
            return DailyDigest(
                date=today,
                total_papers_found=0,
                papers_analyzed=0,
                top_papers=[],
                key_themes=[],
                actionable_signals=[],
                generated_at=datetime.datetime.utcnow().isoformat(),
            )

        # Step 2: Score relevance
        logger.info("Scoring paper relevance...")
        papers = self.scorer.score_papers(papers)

        # Step 3: Summarize top papers
        top_papers = papers[:self.top_n]
        if use_llm:
            logger.info(f"Summarizing top {len(top_papers)} papers with LLM...")
            for i, paper in enumerate(top_papers):
                logger.info(f"  [{i+1}/{len(top_papers)}] {paper.title[:60]}...")
                self.summarizer.summarize_paper(paper)
        else:
            logger.info("Skipping LLM summarization (use_llm=False)")
            for paper in top_papers:
                paper.summary = self.summarizer._fallback_summary(paper)

        # Step 4: Generate digest
        logger.info("Generating daily digest...")
        digest = self.digest_generator.generate_digest(top_papers, today)

        # Step 5: Persist digest
        self._save_digest(digest)

        logger.info(
            f"Digest complete: {digest.total_papers_found} found, "
            f"{digest.papers_analyzed} analyzed, "
            f"{len(digest.actionable_signals)} signals extracted"
        )

        return digest

    def _save_digest(self, digest: DailyDigest) -> Path:
        """Save digest to JSON file for historical tracking."""
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        filepath = STORAGE_DIR / f"digest_{digest.date}.json"

        with open(filepath, "w") as f:
            json.dump(asdict(digest), f, indent=2, default=str)

        logger.info(f"Digest saved to {filepath}")
        return filepath

    def get_historical_digests(self, days: int = 7) -> List[DailyDigest]:
        """Load recent historical digests for trend analysis."""
        digests = []
        if not STORAGE_DIR.exists():
            return digests

        files = sorted(STORAGE_DIR.glob("digest_*.json"), reverse=True)
        for filepath in files[:days]:
            try:
                with open(filepath) as f:
                    data = json.load(f)
                digests.append(DailyDigest(**data))
            except Exception as e:
                logger.warning(f"Failed to load digest {filepath}: {e}")

        return digests

    def get_trending_themes(self, days: int = 7) -> List[Tuple[str, int]]:
        """Analyze theme trends across recent digests."""
        theme_counts: Dict[str, int] = {}
        digests = self.get_historical_digests(days)

        for digest in digests:
            for theme in digest.key_themes:
                theme_counts[theme] = theme_counts.get(theme, 0) + 1

        return sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)


def main():
    """Run the daily research summarizer."""
    import argparse

    parser = argparse.ArgumentParser(description="Daily AI/Finance Research Summarizer")
    parser.add_argument("--days-back", type=int, default=1,
                        help="How many days back to fetch papers")
    parser.add_argument("--top-n", type=int, default=10,
                        help="Number of top papers to summarize")
    parser.add_argument("--no-llm", action="store_true",
                        help="Skip LLM summarization (use fallback)")
    parser.add_argument("--categories", nargs="+", default=None,
                        help="ArXiv categories to search")
    parser.add_argument("--trends", action="store_true",
                        help="Show trending themes from recent digests")

    args = parser.parse_args()

    summarizer = DailyResearchSummarizer(
        categories=args.categories,
        top_n_papers=args.top_n,
        days_back=args.days_back,
    )

    if args.trends:
        trends = summarizer.get_trending_themes()
        print("\n=== Trending Research Themes (Last 7 Days) ===")
        for theme, count in trends[:15]:
            print(f"  {theme}: mentioned in {count} digests")
        return

    digest = summarizer.run(use_llm=not args.no_llm)

    # Print summary
    print(f"\n{'='*60}")
    print(f"DAILY RESEARCH DIGEST - {digest.date}")
    print(f"{'='*60}")
    print(f"Papers found: {digest.total_papers_found}")
    print(f"Papers analyzed: {digest.papers_analyzed}")
    print(f"\nKey Themes: {', '.join(digest.key_themes)}")
    print(f"\nActionable Signals:")
    for i, signal in enumerate(digest.actionable_signals[:10], 1):
        print(f"  {i}. {signal}")

    if digest.top_papers:
        print(f"\nTop Papers:")
        for i, paper in enumerate(digest.top_papers[:5], 1):
            print(f"  {i}. [{paper['relevance_score']}] {paper['title'][:70]}")
            if paper.get("summary"):
                print(f"     Summary: {paper['summary'][:100]}...")


if __name__ == "__main__":
    main()
