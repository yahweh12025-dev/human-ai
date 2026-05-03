#!/usr/bin/env python3
"""
LangChain-based bidirectional pipeline for Dify & Graphify Synergy.
Routes data between Dify (RAG) and Graphify (Knowledge Graph) using LangChain components.
"""

import os
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from core.utils.langchain_dify import DifyLLMWrapper, DifyRetriever, DifyIndexingTool
from core.utils.langchain_graphify import GraphifyLLMWrapper, GraphifyRetriever, GraphifyTripleTool
from core.utils.dify_brain import DifyBrain
from core.utils.graphify_bridge import GraphifyBridge


class DifyToGraphifyPipeline:
    """Pipeline to flow data from Dify RAG to Graphify Knowledge Graph."""
    
    def __init__(self):
        self.dify_brain = DifyBrain()
        self.graphify_bridge = GraphifyBridge()
        self.dify_retriever = DifyRetriever()
        self.graphify_tool = GraphifyTripleTool()
        
    def sync_dify_to_graphify(self, query: str) -> Dict[str, Any]:
        """
        Sync data from Dify to Graphify:
        1. Query Dify for information on a topic
        2. Extract key concepts as triples
        3. Store triples in Graphify KG
        """
        # Step 1: Retrieve from Dify
        dify_docs = self.dify_retriever._get_relevant_documents(
            query, 
            run_manager=None
        )
        
        if not dify_docs:
            return {"status": "error", "message": "No data retrieved from Dify"}
        
        # Step 2: Extract triples from Dify content (using LLM)
        # In a real implementation, we would use an LLM to extract triples
        # For now, we'll create simple triples from the content
        content = dify_docs[0].page_content
        
        # Simple triple extraction (placeholder - in production use proper NLP)
        triples = self._extract_triples_from_text(content, query)
        
        # Step 3: Store in Graphify
        if triples:
            result = self.graphify_tool._run(triples, run_manager=None)
            return {
                "status": "success",
                "dify_content": content[:200] + "..." if len(content) > 200 else content,
                "triples_extracted": len(triples),
                "graphify_result": result
            }
        else:
            return {"status": "warning", "message": "No triples extracted from Dify content"}
    
    def _extract_triples_from_text(self, text: str, topic: str) -> List[Dict[str, str]]:
        """
        Extract subject-predicate-object triples from text.
        This is a simplified version - in production would use NLP/LLM.
        """
        triples = []
        
        # Add a basic triple about the topic
        triples.append({
            "subject": topic,
            "predicate": "is_documented_in",
            "object": "Dify RAG"
        })
        
        # Extract some simple patterns (very basic)
        sentences = text.split('.')
        for sentence in sentences[:3]:  # Limit to first 3 sentences
            if 'is' in sentence.lower() or 'are' in sentence.lower():
                # Very naive triple extraction
                words = sentence.strip().split()
                if len(words) >= 3:
                    triples.append({
                        "subject": words[0],
                        "predicate": "is_related_to",
                        "object": ' '.join(words[2:])[:50]  # Limit length
                    })
        
        return triples[:5]  # Limit total triples


class GraphifyToDifyPipeline:
    """Pipeline to flow data from Graphify Knowledge Graph to Dify RAG."""
    
    def __init__(self):
        self.dify_brain = DifyBrain()
        self.graphify_bridge = GraphifyBridge()
        self.graphify_retriever = GraphifyRetriever()
        self.dify_tool = DifyIndexingTool()
        
    def sync_graphify_to_dify(self, query: str) -> Dict[str, Any]:
        """
        Sync data from Graphify to Dify:
        1. Query Graphify for information on a topic
        2. Format the knowledge for Dify indexing
        3. Store in Dify Knowledge Base
        """
        # Step 1: Retrieve from Graphify
        graphify_docs = self.graphify_retriever._get_relevant_documents(
            query,
            run_manager=None
        )
        
        if not graphify_docs:
            return {"status": "error", "message": "No data retrieved from Graphify"}
        
        # Step 2: Format content for Dify indexing
        content_parts = []
        metadata = {
            "source": "graphify_kg_sync",
            "sync_query": query,
            "timestamp": self._get_timestamp()
        }
        
        for doc in graphify_docs:
            content_parts.append(doc.page_content)
            # Merge metadata
            metadata.update(doc.metadata)
        
        content = "\n\n---\n\n".join(content_parts)
        
        # Step 3: Store in Dify
        try:
            self.dify_brain.index_finding(content, metadata)
            return {
                "status": "success",
                "graphify_content": content[:200] + "..." if len(content) > 200 else content,
                "documents_indexed": len(graphify_docs),
                "dify_metadata": metadata
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to index in Dify: {str(e)}"}
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()


class BidirectionalSyncPipeline:
    """Main bidirectional synchronization pipeline."""
    
    def __init__(self):
        self.dify_to_graphify = DifyToGraphifyPipeline()
        self.graphify_to_dify = GraphifyToDifyPipeline()
    
    def sync_bidirectional(self, topic: str) -> Dict[str, Any]:
        """
        Perform bidirectional synchronization:
        1. Sync Dify -> Graphify
        2. Sync Graphify -> Dify (using the same topic)
        """
        print(f"🔄 Starting bidirectional sync for topic: {topic}")
        
        # Step 1: Dify -> Graphify
        print("📤 Syncing Dify → Graphify...")
        d2g_result = self.dify_to_graphify.sync_dify_to_graphify(topic)
        
        # Step 2: Graphify -> Dify
        print("📥 Syncing Graphify → Dify...")
        g2d_result = self.graphify_to_dify.sync_graphify_to_dify(topic)
        
        return {
            "topic": topic,
            "dify_to_graphify": d2g_result,
            "graphify_to_dify": g2d_result,
            "overall_status": "success" if 
                d2g_result.get("status") == "success" and 
                g2d_result.get("status") == "success" 
                else "partial"
        }
    
    def get_dify_enhanced_with_graphify(self, query: str) -> str:
        """
        Get a Dify response enhanced with Graphify knowledge.
        1. Query Graphify for relevant triples
        2. Augment the query with Graphify knowledge
        3. Query Dify with the augmented query
        """
        # Get Graphify context
        graphify_docs = self.graphify_retriever._get_relevant_documents(
            query,
            run_manager=None
        )
        
        graphify_context = ""
        if graphify_docs:
            graphify_context = "Relevant knowledge from Graphify KG:\n"
            for doc in graphify_docs:
                graphify_context += f"- {doc.page_content}\n"
        
        # Augment query with Graphify context
        if graphify_context:
            augmented_query = f"""
Based on the following knowledge from the knowledge graph:
{graphify_context}

Please answer this question: {query}
"""
        else:
            augmented_query = query
        
        # Query Dify
        return self.dify_brain.query(augmented_query)


# Example usage and testing functions
def test_pipelines():
    """Test the bidirectional pipelines."""
    print("🧪 Testing Dify & Graphify LangChain Pipelines")
    print("=" * 50)
    
    # Initialize pipelines
    pipeline = BidirectionalSyncPipeline()
    
    # Test topic
    test_topic = "artificial intelligence safety"
    
    # Test bidirectional sync
    result = pipeline.sync_bidirectional(test_topic)
    
    print("\n📊 Sync Results:")
    print(f"Topic: {result['topic']}")
    print(f"Dify → Graphify: {result['dify_to_graphify']['status']}")
    print(f"Graphify → Dify: {result['graphify_to_dify']['status']}")
    print(f"Overall: {result['overall_status']}")
    
    # Test enhanced query
    print("\n🔍 Testing Enhanced Query:")
    enhanced_answer = pipeline.get_dify_enhanced_with_graphify(
        "What are the latest developments in AI alignment?"
    )
    print(f"Enhanced Answer: {enhanced_answer[:300]}...")


if __name__ == "__main__":
    test_pipelines()