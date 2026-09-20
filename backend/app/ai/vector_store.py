"""ChromaDB vector store for sovereign debt knowledge base.

Stores document chunks with metadata for RAG retrieval.
"""

import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings

from app.ai.embeddings import embed_texts

DB_PATH = Path(__file__).parent.parent.parent / "data" / "chromadb"

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        DB_PATH.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(DB_PATH),
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name="sovereign_knowledge",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_documents(
    texts: List[str],
    metadatas: List[Dict[str, Any]],
    ids: Optional[List[str]] = None,
    batch_size: int = 100,
) -> int:
    """Add documents to vector store. Returns count added."""
    collection = _get_collection()

    if ids is None:
        ids = [hashlib.sha256(t.encode()).hexdigest()[:16] for t in texts]

    embeddings = embed_texts(texts, batch_size=batch_size)

    for i in range(0, len(texts), batch_size):
        end = min(i + batch_size, len(texts))
        collection.add(
            documents=texts[i:end],
            embeddings=embeddings[i:end].tolist(),
            metadatas=metadatas[i:end],
            ids=ids[i:end],
        )

    return len(texts)


def query(
    query_text: str,
    n_results: int = 5,
    where: Optional[Dict] = None,
) -> List[Dict[str, Any]]:
    """Query the vector store. Returns list of {text, metadata, score}."""
    collection = _get_collection()
    query_embedding = embed_texts([query_text])[0].tolist()

    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": min(n_results, collection.count() or 1),
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    output = []
    for i in range(len(results["documents"][0])):
        output.append({
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
            "score": 1 - results["distances"][0][i],  # cosine distance to similarity
            "id": results["ids"][0][i],
        })
    return output


def get_count() -> int:
    return _get_collection().count()


def delete_collection():
    global _collection
    if _client:
        try:
            _client.delete_collection("sovereign_knowledge")
        except Exception:
            pass
        _collection = None


def list_sources() -> List[Dict[str, Any]]:
    """List all unique sources in the collection."""
    collection = _get_collection()
    if collection.count() == 0:
        return []
    all_meta = collection.get()["metadatas"]
    sources = {}
    for m in all_meta:
        src = m.get("source", "unknown")
        if src not in sources:
            sources[src] = {"source": src, "count": 0, "type": m.get("doc_type", "unknown")}
        sources[src]["count"] += 1
    return list(sources.values())
