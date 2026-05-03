#!/usr/bin/env python3
"""
LangChain integration for Dify RAG system.
Provides LangChain-compatible wrappers for Dify Brain operations.
"""

import os
from typing import Any, Dict, List, Mapping, Optional
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import LLM
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import BaseTool
from pydantic import Field, PrivateAttr

from core.utils.dify_brain import DifyBrain


class DifyLLMWrapper(LLM):
    """LangChain LLM wrapper for Dify's chat completion API."""
    
    dify_brain: DifyBrain = Field(default_factory=DifyBrain)
    
    @property
    def _llm_type(self) -> str:
        return "dify"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call Dify's chat API."""
        return self.dify_brain.query(prompt)


class DifyRetriever(BaseRetriever):
    """LangChain Retriever wrapper for Dify Knowledge Base."""
    
    dify_brain: DifyBrain = Field(default_factory=DifyBrain)
    k: int = Field(default=4)
    
    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForLLMRun,
        **kwargs: Any,
    ) -> List[Document]:
        """Get relevant documents from Dify knowledge base."""
        # Query Dify for context
        context = self.dify_brain.query(query)
        
        # Create a document from the response
        # In a real implementation, Dify might return multiple documents
        # For now, we create one document with the answer
        doc = Document(
            page_content=context,
            metadata={"source": "dify_kg", "query": query}
        )
        
        return [doc]


class DifyIndexingTool(BaseTool):
    """LangChain Tool for indexing content into Dify Knowledge Base."""
    
    name: str = "dify_indexer"
    description: str = "Index text content into the Dify Knowledge Base"
    dify_brain: DifyBrain = Field(default_factory=DifyBrain)
    
    def _run(
        self,
        content: str,
        metadata: Optional[Mapping[str, Any]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
    ) -> str:
        """Index content into Dify."""
        if metadata is None:
            metadata = {}
        
        # Add timestamp if not provided
        if "timestamp" not in metadata:
            from datetime import datetime
            metadata["timestamp"] = datetime.now().isoformat()
            
        self.dify_brain.index_finding(content, dict(metadata))
        return f"Successfully indexed content into Dify Knowledge Base"


# Export for easy importing
__all__ = ["DifyLLMWrapper", "DifyRetriever", "DifyIndexingTool"]