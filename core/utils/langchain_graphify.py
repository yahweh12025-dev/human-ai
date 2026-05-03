#!/usr/bin/env python3
"""
LangChain integration for Graphify Knowledge Graph.
Provides LangChain-compatible wrappers for Graphify operations.
"""

import os
from typing import Any, List, Mapping, Optional
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import LLM
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import BaseTool
from pydantic import Field, PrivateAttr

from core.utils.graphify_bridge import GraphifyBridge


class GraphifyLLMWrapper(LLM):
    """LangChain LLM wrapper for Graphify's knowledge graph querying."""
    
    graphify_bridge: GraphifyBridge = Field(default_factory=GraphifyBridge)
    
    @property
    def _llm_type(self) -> str:
        return "graphify"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Query Graphify knowledge graph and return relevant triples as text."""
        triples = self.graphify_bridge.query_graph(prompt)
        if not triples:
            return "No relevant information found in Graphify knowledge graph."
        
        # Format triples as readable text
        formatted_triples = []
        for triple in triples:
            if isinstance(triple, dict):
                subj = triple.get('subject', '')
                pred = triple.get('predicate', '')
                obj = triple.get('object', '')
                formatted_triples.append(f"{subj} {pred} {obj}")
            else:
                formatted_triples.append(str(triple))
        
        return "\n".join(formatted_triples)


class GraphifyRetriever(BaseRetriever):
    """LangChain Retriever wrapper for Graphify Knowledge Graph."""
    
    graphify_bridge: GraphifyBridge = Field(default_factory=GraphifyBridge)
    k: int = Field(default=4)
    
    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForLLMRun,
        **kwargs: Any,
    ) -> List[Document]:
        """Get relevant documents from Graphify knowledge graph."""
        # Query Graphify for triples
        triples = self.graphify_bridge.query_graph(query)
        
        # Create documents from triples
        documents = []
        for i, triple in enumerate(triples[:self.k]):
            if isinstance(triple, dict):
                subj = triple.get('subject', '')
                pred = triple.get('predicate', '')
                obj = triple.get('object', '')
                content = f"{subj} {pred} {obj}"
                metadata = {
                    "source": "graphify_kg",
                    "query": query,
                    "triple_index": i,
                    "subject": subj,
                    "predicate": pred,
                    "object": obj
                }
            else:
                content = str(triple)
                metadata = {
                    "source": "graphify_kg",
                    "query": query,
                    "triple_index": i
                }
            
            doc = Document(
                page_content=content,
                metadata=metadata
            )
            documents.append(doc)
        
        return documents


class GraphifyTripleTool(BaseTool):
    """LangChain Tool for adding triples to Graphify Knowledge Graph."""
    
    name: str = "graphify_triple_adder"
    description: str = "Add knowledge triples to the Graphify Knowledge Graph"
    graphify_bridge: GraphifyBridge = Field(default_factory=GraphifyBridge)
    
    def _run(
        self,
        triples: List[Dict[str, str]],
        run_manager: Optional[CallbackManagerForLLMRun] = None,
    ) -> str:
        """Add triples to Graphify."""
        success_count = 0
        for triple in triples:
            if self.graphify_bridge.sync_to_graph([triple]):
                success_count += 1
        
        return f"Successfully added {success_count}/{len(triples)} triples to Graphify Knowledge Graph"


# Export for easy importing
__all__ = ["GraphifyLLMWrapper", "GraphifyRetriever", "GraphifyTripleTool"]