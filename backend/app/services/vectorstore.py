"""Vector store service wrapping ChromaDB with tenant isolation.

Each tenant gets its own isolated collection named '{prefix}_{tenant_id}',
ensuring complete data separation (equivalent to Pinecone namespaces).
"""

import math
from typing import Optional, Any
from app.config import get_settings

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a, b in zip(v1, v2)))
    norm2 = math.sqrt(sum(b * b for a, b in zip(v1, v2)))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class InMemoryCollection:
    """Fallback collection when ChromaDB is not installed (e.g. testing)."""

    def __init__(self, name: str):
        self.name = name
        self.records: dict[str, dict[str, Any]] = {}

    def count(self) -> int:
        return len(self.records)

    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ):
        for cid, emb, doc, meta in zip(ids, embeddings, documents, metadatas):
            self.records[cid] = {
                "id": cid,
                "embedding": emb,
                "document": doc,
                "metadata": meta,
            }

    def query(
        self,
        query_embeddings: list[list[float]],
        n_results: int = 5,
        include: list[str] = None,
    ) -> dict[str, list]:
        if not self.records or not query_embeddings:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        target_emb = query_embeddings[0]
        scored = []
        for cid, rec in self.records.items():
            sim = _cosine_similarity(target_emb, rec["embedding"])
            distance = 1.0 - sim
            scored.append((distance, rec))

        scored.sort(key=lambda x: x[0])
        top_k = scored[:n_results]

        ids = [x[1]["id"] for x in top_k]
        docs = [x[1]["document"] for x in top_k]
        metas = [x[1]["metadata"] for x in top_k]
        dists = [x[0] for x in top_k]

        return {
            "ids": [ids],
            "documents": [docs],
            "metadatas": [metas],
            "distances": [dists],
        }

    def get(self, limit: int = 50, include: list[str] = None) -> dict[str, list]:
        keys = list(self.records.keys())[:limit]
        return {
            "ids": keys,
            "documents": [self.records[k]["document"] for k in keys],
            "metadatas": [self.records[k]["metadata"] for k in keys],
        }


class VectorStoreService:
    """ChromaDB-backed vector store with per-tenant namespace isolation.

    Each tenant gets its own collection named '{prefix}_{tenant_id}',
    ensuring complete data separation.
    """

    _instance: Optional["VectorStoreService"] = None

    def __init__(self):
        settings = get_settings()
        self.collection_prefix = settings.CHROMA_COLLECTION_PREFIX
        self.embedding_dimension = settings.EMBEDDING_DIMENSION
        self.persist_dir = settings.CHROMA_PERSIST_DIR

        if HAS_CHROMADB:
            self.client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        else:
            self.client = None
            self._fallback_collections: dict[str, InMemoryCollection] = {}

    @classmethod
    def get_instance(cls) -> "VectorStoreService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def _collection_name(self, tenant_id: str) -> str:
        safe_id = tenant_id.replace(" ", "_")[:50]
        return f"{self.collection_prefix}_{safe_id}"

    def get_or_create_collection(self, tenant_id: str):
        c_name = self._collection_name(tenant_id)
        if HAS_CHROMADB:
            return self.client.get_or_create_collection(
                name=c_name,
                metadata={"hnsw:space": "cosine"},
            )
        else:
            if c_name not in self._fallback_collections:
                self._fallback_collections[c_name] = InMemoryCollection(c_name)
            return self._fallback_collections[c_name]

    def upsert_chunks(
        self,
        tenant_id: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> int:
        collection = self.get_or_create_collection(tenant_id)
        batch_size = 100
        total = 0
        for i in range(0, len(ids), batch_size):
            batch_end = min(i + batch_size, len(ids))
            collection.upsert(
                ids=ids[i:batch_end],
                embeddings=embeddings[i:batch_end],
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end],
            )
            total += batch_end - i
        return total

    def query(
        self,
        tenant_id: str,
        query_embedding: list[float],
        n_results: int = 5,
    ) -> list[dict]:
        collection = self.get_or_create_collection(tenant_id)

        if collection.count() == 0:
            return []

        actual_n = min(n_results, collection.count())
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_n,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        if results and results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                chunks.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                })
        return chunks

    def collection_count(self, tenant_id: str) -> int:
        collection = self.get_or_create_collection(tenant_id)
        return collection.count()

    def get_chunks(self, tenant_id: str, limit: int = 50) -> list[dict]:
        """Retrieve stored chunks for inspection."""
        collection = self.get_or_create_collection(tenant_id)
        if HAS_CHROMADB:
            data = collection.get(limit=limit, include=["documents", "metadatas"])
            chunks = []
            if data and data["ids"]:
                for i in range(len(data["ids"])):
                    chunks.append({
                        "id": data["ids"][i],
                        "document": data["documents"][i] if data["documents"] else "",
                        "metadata": data["metadatas"][i] if data["metadatas"] else {},
                    })
            return chunks
        else:
            data = collection.get(limit=limit)
            chunks = []
            for i in range(len(data["ids"])):
                chunks.append({
                    "id": data["ids"][i],
                    "document": data["documents"][i],
                    "metadata": data["metadatas"][i],
                })
            return chunks

    def delete_collection(self, tenant_id: str):
        c_name = self._collection_name(tenant_id)
        if HAS_CHROMADB:
            try:
                self.client.delete_collection(c_name)
            except ValueError:
                pass
        else:
            self._fallback_collections.pop(c_name, None)

    def is_healthy(self) -> bool:
        if HAS_CHROMADB:
            try:
                self.client.heartbeat()
                return True
            except Exception:
                return False
        return True
