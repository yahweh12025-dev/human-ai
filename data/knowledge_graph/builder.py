import networkx as nx
import json
import os
from typing import List, Dict, Any

class KnowledgeGraphBuilder:
    """
    Builds a real-time knowledge graph connecting market events, 
    news, social sentiment, and technical indicators.
    """
    def __init__(self, storage_path: str = "data/knowledge_graph/graph.json"):
        self.graph = nx.DiGraph()
        self.storage_path = storage_path

    def add_event(self, event_id: str, event_type: str, related_entities: List[str]):
        """Adds a market event and its connections to the graph."""
        self.graph.add_node(event_id, type=event_type)
        for entity in related_entities:
            self.graph.add_edge(event_id, entity, relation="AFFECTS")

    def save_graph(self):
        """Saves the graph structure to a JSON file."""
        data = nx.node_link_data(self.graph)
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)

if __name__ == "__main__":
    builder = KnowledgeGraphBuilder()
    builder.add_event("FED_MEETING_2026", "MacroEvent", ["USD", "BTC", "S&P500"])
    builder.add_event("ETF_APPROVAL", "News", ["BTC", "BlackRock"])
    builder.save_graph()
    print(f"Knowledge Graph saved to {builder.storage_path}")
