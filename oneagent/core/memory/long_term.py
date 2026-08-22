"""
Long-term Memory - Vector-based semantic memory
"""

import hashlib
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]
    created_at: str


class LongTermMemory:
    """
    Long-term semantic memory using vector embeddings.

    Note: This is a simple in-memory implementation for Phase A.
    In production, this should be backed by ChromaDB or similar vector store.
    """

    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self._entries: Dict[str, MemoryEntry] = {}
        self._index: List[str] = []  # For simple iteration

    def add(self, text: str, metadata: Dict = None) -> str:
        """Add text with embedding to memory."""
        doc_id = hashlib.md5(text.encode()).hexdigest()[:16]

        # Generate simple embedding (placeholder - use actual embedding model in production)
        embedding = self._generate_embedding(text)

        entry = MemoryEntry(
            id=doc_id,
            text=text,
            embedding=embedding,
            metadata=metadata or {},
            created_at=metadata.get("created_at") if metadata else ""
        )

        self._entries[doc_id] = entry
        self._index.append(doc_id)

        return doc_id

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        """
        Search for similar documents using cosine similarity.
        Returns list of (doc_id, score, metadata) tuples.
        """
        query_embedding = self._generate_embedding(query)

        scores = []
        for doc_id in self._index:
            entry = self._entries[doc_id]
            score = self._cosine_similarity(query_embedding, entry.embedding)
            scores.append((doc_id, score, entry.metadata))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def get(self, doc_id: str) -> Optional[MemoryEntry]:
        """Get entry by ID."""
        return self._entries.get(doc_id)

    def get_text(self, doc_id: str) -> Optional[str]:
        """Get text content by ID."""
        entry = self._entries.get(doc_id)
        return entry.text if entry else None

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.

        Note: This is a placeholder using a simple hash-based mock.
        In production, use actual embedding model (OpenAI, Anthropic, local, etc.)
        """
        # Simple mock embedding based on text hash
        import random
        random.seed(hash(text) % (2**32))
        return [random.random() for _ in range(self.embedding_dim)]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def __len__(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
        self._index.clear()