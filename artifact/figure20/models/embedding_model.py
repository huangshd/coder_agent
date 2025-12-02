"""
Embedding Model Wrapper
Provides unified interface for embedding models (sentence-transformers, OpenAI, etc.)
"""

from typing import List, Optional, Dict, Any
import numpy as np


class EmbeddingModel:
    """
    Wrapper for embedding models.
    Supports: sentence-transformers, OpenAI embeddings, HuggingFace, etc.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 device: str = "cpu", cache_dir: Optional[str] = None):
        """
        Initialize embedding model.

        Args:
            model_name: Model identifier (HuggingFace model ID or OpenAI model name)
            device: Device to use ("cpu", "cuda", "cuda:0", etc.)
            cache_dir: Cache directory for downloaded models
        """
        self.model_name = model_name
        self.device = device
        self.cache_dir = cache_dir
        self.model = None
        self.embedding_dim = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the embedding model"""
        try:
            if "sentence-transformers" in self.model_name or "/" in self.model_name:
                # Use sentence-transformers
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_name, device=self.device)
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
            else:
                raise ValueError(f"Unsupported model: {self.model_name}")
        except ImportError:
            raise ImportError("Please install sentence-transformers: pip install sentence-transformers")

    def encode(self, texts: List[str] or str, batch_size: int = 32,
               normalize_embeddings: bool = True) -> np.ndarray or List[float]:
        """
        Encode text(s) to embeddings.

        Args:
            texts: Single string or list of strings
            batch_size: Batch size for processing
            normalize_embeddings: Whether to normalize embeddings

        Returns:
            Embedding vector(s) as numpy array
        """
        if isinstance(texts, str):
            texts = [texts]
            return_single = True
        else:
            return_single = False

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=normalize_embeddings,
            convert_to_numpy=True
        )

        return embeddings[0] if return_single and len(embeddings) == 1 else embeddings

    def get_embedding_dim(self) -> int:
        """Get embedding dimension"""
        return self.embedding_dim

    def similarity(self, query: str, texts: List[str]) -> List[float]:
        """
        Calculate similarity between query and texts.

        Args:
            query: Query text
            texts: List of document texts

        Returns:
            List of similarity scores
        """
        query_embedding = self.encode(query)
        text_embeddings = self.encode(texts)

        # Calculate cosine similarity
        similarities = np.dot(text_embeddings, query_embedding) / (
            np.linalg.norm(text_embeddings, axis=1) * np.linalg.norm(query_embedding)
        )

        return similarities.tolist()

    def batch_encode(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Encode multiple texts and return as list of lists.

        Args:
            texts: List of texts
            batch_size: Batch size

        Returns:
            List of embeddings
        """
        embeddings = self.encode(texts, batch_size=batch_size)
        return embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings
