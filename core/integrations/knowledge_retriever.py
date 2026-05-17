from dify import DifyRagWrapper
from bridge_router import BridgeRouter

class KnowledgeRetriever:
    def __init__(self, llm_client, confidence_threshold=0.7):
        self.llm_client = llm_client
        self.dify_rag = DifyRagWrapper()
        self.confidence_threshold = confidence_threshold
        self.router = BridgeRouter()

    def get_answer(self, query):
        # Primary response attempt
        primary_answer = self.llm_client.get_response(query)
        confidence = self.evaluate_confidence(primary_answer)

        if confidence >= self.confidence_threshold:
            return primary_answer

        # Confidence-triggered Dify RAG search
        return self.dify_rag.search(query)

    def evaluate_confidence(self, answer):
        # Implement confidence scoring logic
        # This could involve analyzing answer structure, length, keywords, etc.
        return 1.0 if len(answer) > 100 else 0.5  # Simplified example

__all__ = ['KnowledgeRetriever']