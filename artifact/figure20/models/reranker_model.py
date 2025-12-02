"""
Reranker Model Wrapper
Provides unified interface for reranker models (cross-encoders)
"""

from typing import List, Tuple, Optional
import numpy as np


class RerankerModel:
    """
    Wrapper for reranker models (cross-encoders).
    Supports: sentence-transformers cross-encoders, etc.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
                 device: str = "cpu", cache_dir: Optional[str] = None):
        """
        Initialize reranker model.

        Args:
            model_name: Model identifier (HuggingFace model ID)
            device: Device to use ("cpu", "cuda", "cuda:0", etc.)
            cache_dir: Cache directory for downloaded models
        """
        self.model_name = model_name
        self.device = device
        self.cache_dir = cache_dir
        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the reranker model"""
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name, device=self.device)
        except ImportError:
            raise ImportError("Please install sentence-transformers: pip install sentence-transformers")

    def rank(self, query: str, documents: List[str], top_k: Optional[int] = None
             ) -> List[Tuple[int, float, str]]:
        """
        Rank documents by relevance to query.

        Args:
            query: Query text
            documents: List of document texts
            top_k: Return only top-k documents (None = return all)

        Returns:
            List of (index, score, document) tuples sorted by score (descending)
        """
        # Prepare pairs
        pairs = [[query, doc] for doc in documents]

        # Score all pairs
        scores = self.model.predict(pairs)

        # Create result list with original indices
        results = [(i, score, doc) for i, (score, doc) in enumerate(zip(scores, documents))]

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        # Return top-k if specified
        if top_k:
            results = results[:top_k]

        return results

    def score(self, query: str, document: str) -> float:
        """
        Score relevance of a single document to query.

        Args:
            query: Query text
            document: Document text

        Returns:
            Relevance score
        """
        score = self.model.predict([[query, document]])[0]
        return float(score)

    def batch_rank(self, query: str, documents_batch: List[List[str]],
                   top_k: Optional[int] = None) -> List[List[Tuple[int, float, str]]]:
        """
        Rank multiple batches of documents.

        Args:
            query: Query text
            documents_batch: List of document lists
            top_k: Top-k per batch

        Returns:
            List of ranked results per batch
        """
        all_results = []
        for documents in documents_batch:
            results = self.rank(query, documents, top_k)
            all_results.append(results)
        return all_results

    def rerank_with_metadata(self, query: str, documents: List[dict],
                            doc_content_key: str = "content",
                            top_k: Optional[int] = None) -> List[dict]:
        """
        Rerank documents with metadata preservation.

        Args:
            query: Query text
            documents: List of document dicts with content and metadata
            doc_content_key: Key for document content field
            top_k: Top-k documents

        Returns:
            List of reranked documents with scores
        """
        doc_contents = [doc[doc_content_key] for doc in documents]
        ranked_results = self.rank(query, doc_contents, top_k)

        result_dicts = []
        for orig_idx, score, _ in ranked_results:
            doc_dict = documents[orig_idx].copy()
            doc_dict["rerank_score"] = float(score)
            result_dicts.append(doc_dict)

        return result_dicts
