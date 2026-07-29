from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


@dataclass
class Document:
    id: str
    text: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorStore(ABC):
    """Abstract vector store for RAG."""

    @abstractmethod
    async def add(self, documents: List[Document]):
        ...

    @abstractmethod
    async def search(self, query_embedding: List[float], top_k: int = 5) -> List[Document]:
        ...

    @abstractmethod
    async def delete(self, ids: List[str]):
        ...


class InMemoryVectorStore(VectorStore):
    """Simple in-memory vector store for development."""

    def __init__(self):
        self._docs: Dict[str, Document] = {}
        self._index: List[str] = []

    async def add(self, documents: List[Document]):
        for doc in documents:
            self._docs[doc.id] = doc
            self._index.append(doc.id)

    async def search(self, query_embedding: List[float], top_k: int = 5) -> List[Document]:
        # Fallback: return most recent docs if no embeddings
        if not query_embedding or not self._docs:
            return [self._docs[i] for i in self._index[-top_k:] if i in self._docs]
        # Cosine similarity search
        scored = []
        for doc_id in self._index:
            doc = self._docs.get(doc_id)
            if doc and doc.embedding:
                score = self._cosine(query_embedding, doc.embedding)
                scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    async def delete(self, ids: List[str]):
        for id_ in ids:
            self._docs.pop(id_, None)
            if id_ in self._index:
                self._index.remove(id_)

    def _cosine(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class ChromaStore(VectorStore):
    """Chroma-backed vector store."""

    def __init__(self, collection_name: str = "oneagent"):
        self.collection_name = collection_name
        self._client = None

    async def _get_client(self):
        if self._client is None:
            import chromadb
            self._client = chromadb.PersistentClient(path="./chroma_db")
        return self._client

    async def add(self, documents: List[Document]):
        client = await self._get_client()
        coll = client.get_or_create_collection(self.collection_name)
        coll.add(
            ids=[d.id for d in documents],
            documents=[d.text for d in documents],
            metadatas=[d.metadata for d in documents],
            embeddings=[d.embedding for d in documents if d.embedding],
        )

    async def search(self, query_embedding: List[float], top_k: int = 5) -> List[Document]:
        client = await self._get_client()
        coll = client.get_or_create_collection(self.collection_name)
        results = coll.query(query_embeddings=[query_embedding], n_results=top_k)
        docs = []
        for i in range(len(results["ids"][0])):
            docs.append(Document(
                id=results["ids"][0][i],
                text=results["documents"][0][i] if results["documents"] else "",
                embedding=results["embeddings"][0][i] if results["embeddings"] else None,
                metadata=results["metadatas"][0][i] if results["metadatas"] else {},
            ))
        return docs

    async def delete(self, ids: List[str]):
        client = await self._get_client()
        coll = client.get_or_create_collection(self.collection_name)
        coll.delete(ids=ids)
