"""RAG pipeline: chunking, retrieval, generation.

Combines vector search with a local language model for sovereign debt Q&A.
No external LLM APIs — everything runs locally.
"""

import re
from typing import List, Dict, Any, Optional

from app.ai.vector_store import query as vector_query, add_documents, get_count
from app.ai.embeddings import embed_texts

# ── Chunking ───────────────────────────────────────────────────────────

def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
    separators: Optional[List[str]] = None,
) -> List[str]:
    """Split text into overlapping chunks for embedding."""
    if separators is None:
        separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]

    if len(text) <= chunk_size:
        return [text.strip()] if text.strip() else []

    # Try each separator
    for sep in separators:
        parts = text.split(sep)
        if len(parts) <= 1:
            continue

        chunks = []
        current = ""
        for part in parts:
            test = current + sep + part if current else part
            if len(test) > chunk_size and current:
                chunks.append(current.strip())
                # Keep overlap
                words = current.split()
                overlap_words = words[-overlap // 4:] if overlap else []
                current = sep.join(overlap_words) + sep + part if overlap_words else part
            else:
                current = test
        if current.strip():
            chunks.append(current.strip())

        if len(chunks) > 1:
            return chunks

    # Fallback: hard split
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def chunk_document(text: str, metadata: Dict[str, Any], chunk_size: int = 512) -> List[Dict[str, Any]]:
    """Chunk a document and return list of {text, metadata}."""
    chunks = chunk_text(text, chunk_size=chunk_size)
    result = []
    for i, chunk in enumerate(chunks):
        meta = {**metadata, "chunk_index": i, "total_chunks": len(chunks)}
        result.append({"text": chunk, "metadata": meta})
    return result


# ── Ingestion ──────────────────────────────────────────────────────────

def ingest_document(
    text: str,
    source: str,
    doc_type: str = "knowledge",
    metadata: Optional[Dict[str, Any]] = None,
    chunk_size: int = 512,
) -> int:
    """Ingest a document into the vector store. Returns chunk count."""
    meta = {"source": source, "doc_type": doc_type, **(metadata or {})}
    doc_chunks = chunk_document(text, meta, chunk_size=chunk_size)

    texts = [c["text"] for c in doc_chunks]
    metadatas = [c["metadata"] for c in doc_chunks]

    return add_documents(texts, metadatas)


def ingest_texts(
    texts: List[str],
    source: str,
    doc_type: str = "knowledge",
    chunk_size: int = 512,
) -> int:
    """Ingest multiple texts. Returns total chunk count."""
    total = 0
    for i, text in enumerate(texts):
        total += ingest_document(text, f"{source}:{i}", doc_type, chunk_size=chunk_size)
    return total


# ── Retrieval ──────────────────────────────────────────────────────────

def retrieve(
    query: str,
    n_results: int = 5,
    min_score: float = 0.3,
    doc_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve relevant context for a query."""
    where = {"doc_type": doc_type} if doc_type else None
    results = vector_query(query, n_results=n_results, where=where)
    return [r for r in results if r["score"] >= min_score]


def build_context(results: List[Dict[str, Any]], max_tokens: int = 2000) -> str:
    """Build context string from retrieval results."""
    context_parts = []
    token_count = 0

    for r in results:
        text = r["text"]
        estimated_tokens = len(text.split())
        if token_count + estimated_tokens > max_tokens:
            break
        context_parts.append(f"[Source: {r['metadata'].get('source', 'unknown')}]\n{text}")
        token_count += estimated_tokens

    return "\n\n---\n\n".join(context_parts)


# ── Generation (Local) ────────────────────────────────────────────────

_local_model = None
_local_tokenizer = None


def _get_local_model():
    global _local_model, _local_tokenizer
    if _local_model is None:
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch

            model_name = "sshleifer/distilgpt2"  # 82MB, runs on CPU
            _local_tokenizer = AutoTokenizer.from_pretrained(model_name)
            _local_model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float32,
                device_map="cpu",
            )
        except Exception:
            return None, None
    return _local_model, _local_tokenizer


def generate_local(
    prompt: str,
    max_new_tokens: int = 512,
    temperature: float = 0.7,
    top_p: float = 0.9,
) -> str:
    """Generate text using local model."""
    model, tokenizer = _get_local_model()
    if model is None:
        return "[Local model not available. Using rule-based response.]"

    import torch
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return response.strip()


# ── RAG Query ──────────────────────────────────────────────────────────

SOVEREIGN_SYSTEM_PROMPT = """You are Quantive AI, an expert advisor on sovereign debt management, 
government bond optimization, and public finance. You provide accurate, data-driven analysis 
based on the provided context. Always cite your sources when possible.
If the context doesn't contain enough information, say so clearly."""


def rag_query(
    query: str,
    n_results: int = 5,
    use_local_model: bool = True,
    max_context_tokens: int = 2000,
) -> Dict[str, Any]:
    """Full RAG pipeline: retrieve context, generate answer."""
    results = retrieve(query, n_results=n_results)
    context = build_context(results, max_tokens=max_context_tokens)

    if use_local_model and context:
        prompt = f"""System: {SOVEREIGN_SYSTEM_PROMPT}

Context:
{context}

User Question: {query}

Answer:"""
        answer = generate_local(prompt)
    elif context:
        answer = f"Based on the available documents, here is relevant context for your query:\n\n{context}"
    else:
        answer = "I don't have enough information in my knowledge base to answer this question. Please provide more context or try a different query."

    return {
        "answer": answer,
        "sources": [
            {
                "text": r["text"][:200] + "..." if len(r["text"]) > 200 else r["text"],
                "source": r["metadata"].get("source", "unknown"),
                "score": round(r["score"], 3),
            }
            for r in results
        ],
        "context_count": len(results),
        "knowledge_base_size": get_count(),
    }
