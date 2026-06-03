import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearchTrendTracker:
    """
    Tracks research trends and suggests new research directions based on arXiv and papers.
    """
    def __init__(self):
        self.trends = []

    def track_paper(self, title: str, abstract: str):
        """Analyzes a paper to identify emerging keywords."""
        # Mock keyword extraction
        keywords = ["Quantum", "LLM", "RLHF", "Slippage"]
        found = [k for k in keywords if k.lower() in abstract.lower()]
        self.trends.extend(found)

    def get_top_trends(self, top_n: int = 3) -> List[str]:
        """Returns the most frequent keywords found in analyzed papers."""
        if not self.trends: return []
        val, counts = np.unique(self.trends, return_counts=True)
        sorted_indices = np.argsort(-counts)
        return val[sorted_indices][:top_n].tolist()

if __name__ == "__main__":
    tracker = ResearchTrendTracker()
    tracker.track_paper("LLM for Trading", "Using LLMs to predict price movements via RLHF.")
    tracker.track_paper("Quantum Finance", "Applying Quantum computing to solve portfolio optimization.")
    print(f"Top Trends: {tracker.get_top_trends()}")
