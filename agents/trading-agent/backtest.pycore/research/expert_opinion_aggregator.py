import numpy as np
from typing import List, Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExpertOpinionAggregator:
    """
    Weights and synthesizes insights from multiple domain experts on trading strategies.
    """
    def __init__(self):
        self.experts = {} # Expert -> Reliability Score

    def add_expert(self, name: str, reliability: float):
        self.experts[name] = reliability

    def aggregate(self, opinions: List[Dict[str, Any]]) -> float:
        """
        Calculates a weighted average of expert opinions.
        """
        total_weight = 0
        weighted_sum = 0
        
        for op in opinions:
            expert = op['expert']
            weight = self.experts.get(expert, 0.5)
            weighted_sum += op['score'] * weight
            total_weight += weight
            
        return weighted_sum / total_weight if total_weight > 0 else 0.0

if __name__ == "__main__":
    agg = ExpertOpinionAggregator()
    agg.add_expert("Quant_Expert_1", 0.9)
    agg.add_expert("Trader_Expert_2", 0.6)
    
    opinions = [
        {"expert": "Quant_Expert_1", "score": 1.0},
        {"expert": "Trader_Expert_2", "score": -1.0}
    ]
    print(f"Aggregated Opinion: {agg.aggregate(opinions):.4f}")
