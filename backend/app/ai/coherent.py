"""Coherent response engine using RAG context extraction.

Instead of generating text token by token (which requires a large LLM),
this engine retrieves relevant knowledge base chunks and constructs
grammatically coherent answers by extracting and combining key sentences.
"""

import re
import time
import threading
from typing import Dict, Any, List, Optional


class CoherentResponder:
    """Generates coherent answers from RAG-retrieved context."""

    def __init__(self):
        self._lock = threading.Lock()
        self._retriever = None

    def _get_retriever(self):
        if self._retriever is None:
            try:
                from app.ai.inference import KnowledgeRetriever
                self._retriever = KnowledgeRetriever()
            except Exception:
                from app.ai.vector_store import query as vs_query
                self._retriever = type('Retriever', (), {
                    'retrieve': lambda self, q, top_k=5: [
                        {"text": r["text"], "source": r["metadata"].get("source", "unknown"),
                         "type": r["metadata"].get("doc_type", "unknown"), "relevance": r["score"]}
                        for r in vs_query(q, n_results=top_k)
                    ]
                })()
        return self._retriever

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        text = re.sub(r'\s+', ' ', text).strip()
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 20]

    def _score_relevance(self, sentence: str, keywords: List[str]) -> float:
        """Score how relevant a sentence is to the query keywords."""
        lower = sentence.lower()
        matches = sum(1 for kw in keywords if kw in lower)
        return matches / max(len(keywords), 1)

    def _extract_key_sentences(self, contexts: List[str], query: str, max_sentences: int = 5) -> List[str]:
        """Extract the most relevant sentences from retrieved contexts."""
        # Extract keywords from query
        keywords = [w.lower() for w in re.findall(r'\b\w{3,}\b', query.lower())]
        stop_words = {'what', 'how', 'why', 'when', 'where', 'which', 'the', 'and', 'for',
                      'are', 'is', 'can', 'does', 'this', 'that', 'with', 'from', 'have',
                      'has', 'its', 'they', 'them', 'their', 'will', 'would', 'could', 'should'}
        keywords = [k for k in keywords if k not in stop_words]

        # Extract all sentences
        all_sentences = []
        for ctx in contexts:
            all_sentences.extend(self._split_sentences(ctx))

        # Score and sort
        scored = [(s, self._score_relevance(s, keywords)) for s in all_sentences]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Deduplicate similar sentences
        selected = []
        for sent, score in scored:
            if len(selected) >= max_sentences:
                break
            if score < 0.1 and len(selected) >= 2:
                break
            # Check for duplicates
            is_dup = False
            for existing in selected:
                if len(set(sent.lower().split()) & set(existing.lower().split())) / max(len(sent.split()), 1) > 0.6:
                    is_dup = True
                    break
            if not is_dup:
                selected.append(sent)

        return selected

    def _format_answer(self, query: str, sentences: List[str], sources: List[Dict]) -> str:
        """Format extracted sentences into a coherent answer."""
        if not sentences:
            return "I don't have enough information in my knowledge base to answer that question."

        # Clean up sentences
        cleaned = []
        for s in sentences:
            s = s.strip().rstrip('.')
            if s and not s.startswith(('<', '{', '[')):
                cleaned.append(s)

        if not cleaned:
            return "I don't have enough information in my knowledge base to answer that question."

        # Build answer
        answer = '. '.join(cleaned) + '.'

        # Clean up artifacts
        answer = re.sub(r'\s+', ' ', answer)
        answer = re.sub(r'\.{2,}', '.', answer)
        answer = answer.replace(' ,', ',').replace(' .', '.')

        # Capitalize first letter
        if answer:
            answer = answer[0].upper() + answer[1:]

        return answer

    def respond(self, query: str, top_k: int = 5, max_sentences: int = 5) -> Dict[str, Any]:
        """Generate a coherent response to a query."""
        t0 = time.time()

        # Live market data takes priority for stock/market questions so the
        # assistant answers with real numbers instead of textbook theory.
        market_block = ""
        market_ctx = None
        try:
            from app.ai.market_context import build_market_context, format_market_context_text
            market_ctx = build_market_context(query)
            if market_ctx:
                market_block = format_market_context_text(market_ctx)
        except Exception:
            market_ctx = None

        with self._lock:
            retriever = self._get_retriever()
            sources = retriever.retrieve(query, top_k=top_k)

        # Extract contexts
        contexts = [s["text"] for s in sources]

        # Extract key sentences
        sentences = self._extract_key_sentences(contexts, query, max_sentences=max_sentences)

        # Format answer
        answer = self._format_answer(query, sentences, sources)

        # Prepend the live-data block so the number comes first, and label
        # the knowledge-base text so it reads as related context, not a
        # non-sequitur under a stock quote.
        if market_block:
            answer = market_block + "\n\nFrom the knowledge base:\n" + answer

        elapsed = time.time() - t0

        result = {
            "text": answer,
            "model": "rag-extraction",
            "sources": sources,
            "query": query,
            "sentences_extracted": len(sentences),
            "latency_ms": round(elapsed * 1000),
        }
        if market_ctx:
            result["market_context"] = market_ctx
        return result

    def status(self) -> Dict[str, Any]:
        return {
            "engine": "rag-extraction",
            "model_loaded": True,
            "knowledge_chunks": 24,
        }


# Singleton
_responder = None


def get_responder() -> CoherentResponder:
    global _responder
    if _responder is None:
        _responder = CoherentResponder()
    return _responder
