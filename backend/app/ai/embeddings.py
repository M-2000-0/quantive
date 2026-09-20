"""Local embedding service using sentence-transformers.

Provides deterministic, GPU-free embeddings for RAG pipeline.
Default model: all-MiniLM-L6-v2 (80MB, 384-dim, fast CPU).
"""

import hashlib
import json
import threading
from pathlib import Path
from typing import List

import numpy as np

_model = None
_model_lock = threading.Lock()
CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "embeddings_cache"


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_texts(texts: List[str], batch_size: int = 64) -> np.ndarray:
    """Embed a list of texts. Returns (N, 384) float32 array."""
    model = _get_model()
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
    return np.array(embeddings, dtype=np.float32)


def embed_query(query: str) -> np.ndarray:
    """Embed a single query. Returns (384,) float32 array."""
    return embed_texts([query])[0]


def get_dimension() -> int:
    return 384


def cache_embeddings(texts: List[str], embeddings: np.ndarray, namespace: str = "default"):
    """Cache embeddings to disk for fast reload."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    content_hash = hashlib.sha256(json.dumps(texts).encode()).hexdigest()[:16]
    path = CACHE_DIR / f"{namespace}_{content_hash}.npz"
    np.savez_compressed(path, texts=np.array(texts, dtype=object), embeddings=embeddings)
    return str(path)


def load_cached_embeddings(namespace: str = "default"):
    """Load cached embeddings if available. Returns (texts, embeddings) or None."""
    if not CACHE_DIR.exists():
        return None
    files = sorted(CACHE_DIR.glob(f"{namespace}_*.npz"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return None
    data = np.load(files[0], allow_pickle=True)
    return data["texts"].tolist(), data["embeddings"]
