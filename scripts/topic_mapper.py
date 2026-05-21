import json
from typing import List, Dict, Any

def map_trending_topics():
    """
    Maps trending Twitter/X topics to Postiz Topic-Switch Module.
    This allows the content pipeline to contextualize AI generated posts.
    """
    trending_topics = [
        {"topic": "ETF Approval", "category": "Macro", "weight": 0.9},
        {"topic": "Layer2 Scaling", "category": "Tech", "weight": 0.7},
        {"topic": "Fed Interest Rates", "category": "Macro", "weight": 0.85},
        {"topic": "DeFi Yields", "category": "Finance", "weight": 0.6}
    ]
    
    mapping = {
        "Macro": [t["topic"] for t in trending_topics if t["category"] == "Macro"],
        "Tech": [t["topic"] for t in trending_topics if t["category"] == "Tech"],
        "Finance": [t["topic"] for t in trending_topics if t["category"] == "Finance"],
    }
    return mapping

if __name__ == "__main__":
    mapping = map_trending_topics()
    with open("data/social/trending_topics_map.json", "w") as f:
        json.dump(mapping, f, indent=2)
    print("Trending topics map updated.")
