"""
ChromaDB Vector Store - RAG backend for OneAgent
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..logging import get_logger

logger = get_logger("rag.chroma_store")


@dataclass
class Document:
    """A document in the vector store."""
    id: str
    content: str
    metadata: Dict[str, Any]


class ChromaStore:
    """
    ChromaDB-backed vector store for RAG.

    Falls back to in-memory storage if ChromaDB is not available.
    """

    def __init__(
        self,
        collection_name: str = "oneagent",
        persist_directory: Optional[str] = None,
        embedding_provider: str = "default",
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory or os.getenv(
            "ONEAGENT_CHROMA_DIR", "./chroma_data"
        )
        self._client = None
        self._collection = None
        self._fallback_store: Dict[str, Dict] = {}
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of ChromaDB client."""
        if self._initialized:
            return

        try:
            import chromadb

            self._client = chromadb.PersistentClient(path=self.persist_directory)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._initialized = True
            logger.info(f"ChromaDB initialized: {self.collection_name}")
        except ImportError:
            logger.warning("chromadb not installed, using in-memory fallback")
            self._initialized = True
        except Exception as e:
            logger.warning(f"ChromaDB init failed ({e}), using in-memory fallback")
            self._initialized = True

    def _degrade_to_fallback(self, reason: str):
        """Disable the ChromaDB backend and serve from the in-memory store.

        Used when ChromaDB is installed but unusable at runtime (e.g. the
        default embedding model cannot be downloaded because the network is
        unavailable). Mirrors the ImportError fallback policy in
        _ensure_initialized.
        """
        logger.warning(
            f"ChromaDB backend unusable ({reason}); degrading to in-memory fallback"
        )
        self._collection = None
        self._client = None

    def add(
        self,
        documents: List[Document],
    ) -> List[str]:
        """Add documents to the store. Returns document IDs."""
        self._ensure_initialized()

        if self._collection is not None:
            ids = [doc.id for doc in documents]
            contents = [doc.content for doc in documents]
            # chromadb >=0.4.22 rejects empty metadata dicts in upsert;
            # normalize empties to a placeholder so documents always land.
            metadatas = [
                doc.metadata if doc.metadata else {"source": "oneagent"}
                for doc in documents
            ]

            try:
                self._collection.upsert(
                    ids=ids,
                    documents=contents,
                    metadatas=metadatas,
                )
            except Exception as e:
                self._degrade_to_fallback(str(e))
                for doc in documents:
                    self._fallback_store[doc.id] = {
                        "content": doc.content,
                        "metadata": doc.metadata,
                    }
                return [doc.id for doc in documents]
            logger.debug(f"Added {len(documents)} docs to ChromaDB")
            return ids
        else:
            for doc in documents:
                self._fallback_store[doc.id] = {
                    "content": doc.content,
                    "metadata": doc.metadata,
                }
            return [doc.id for doc in documents]

    def add_text(self, content: str, metadata: Optional[Dict] = None) -> str:
        """Add a single text document."""
        import hashlib

        doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        self.add([Document(id=doc_id, content=content, metadata=metadata or {})])
        return doc_id

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """Query for similar documents."""
        self._ensure_initialized()

        if self._collection is not None:
            kwargs = {"query_texts": [query_text], "n_results": n_results}
            if where:
                kwargs["where"] = where

            try:
                results = self._collection.query(**kwargs)
            except Exception as e:
                self._degrade_to_fallback(str(e))
                return self._keyword_fallback_query(query_text, n_results)

            documents = []
            for i in range(len(results["ids"][0])):
                documents.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                })
            return documents
        else:
            return self._keyword_fallback_query(query_text, n_results)

    def _keyword_fallback_query(self, query_text: str, n_results: int) -> List[Dict[str, Any]]:
        """Simple keyword matching over the in-memory store."""
        results = []
        query_lower = query_text.lower()
        for doc_id, doc_data in self._fallback_store.items():
            if query_lower in doc_data["content"].lower():
                results.append({
                    "id": doc_id,
                    "content": doc_data["content"],
                    "metadata": doc_data["metadata"],
                    "distance": None,
                })
        return results[:n_results]

    def delete(self, ids: List[str]) -> None:
        """Delete documents by ID."""
        self._ensure_initialized()

        if self._collection is not None:
            self._collection.delete(ids=ids)
        else:
            for doc_id in ids:
                self._fallback_store.pop(doc_id, None)

    def count(self) -> int:
        """Count documents in the store."""
        self._ensure_initialized()

        if self._collection is not None:
            return self._collection.count()
        return len(self._fallback_store)

    def clear(self) -> None:
        """Clear all documents."""
        if self._collection is not None:
            self._client.delete_collection(self.collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        else:
            self._fallback_store.clear()
