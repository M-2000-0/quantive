"""Local inference engine for sovereign debt AI.

Uses the custom-trained SovereignGPT model (no HuggingFace downloads).
All inference runs on CPU with PyTorch.
"""

import json
import time
import threading
import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from pathlib import Path
from typing import Dict, Any, Optional, List

MODEL_DIR = Path(__file__).parent.parent.parent / "data" / "training" / "models" / "sovereign_gpt_v2"


# ── Model Architecture (must match training script) ───────────────────

class SovereignGPT(nn.Module):
    def __init__(self, vocab_size=5000, d_model=192, n_heads=6, n_layers=4, d_ff=512, max_seq=512):
        super().__init__()
        self.config = {
            'vocab_size': vocab_size, 'd_model': d_model,
            'n_heads': n_heads, 'n_layers': n_layers,
            'd_ff': d_ff, 'max_seq': max_seq,
        }
        self.embeddings = nn.Embedding(vocab_size, d_model)
        self.pos_embeddings = nn.Embedding(max_seq, d_model)
        self.dropout = nn.Dropout(0.1)
        decoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_ff,
            dropout=0.1, activation='gelu', batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(decoder_layer, num_layers=n_layers)
        self.ln = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size)

    def forward(self, input_ids):
        B, T = input_ids.shape
        pos = torch.arange(T, device=input_ids.device).unsqueeze(0)
        x = self.dropout(self.embeddings(input_ids) + self.pos_embeddings(pos))
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=input_ids.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        return self.head(self.ln(x))


# ── Simple Tokenizer ──────────────────────────────────────────────────

class WordTokenizer:
    """Word-level tokenizer loaded from training checkpoint."""

    def __init__(self, word2idx, idx2word):
        self.word2idx = word2idx
        self.idx2word = {int(k): v for k, v in idx2word.items()}

    def encode(self, text, max_length=128):
        import re
        text = text.lower().strip()
        text = re.sub(r'([?.!,;:])', r' \1 ', text)
        tokens = text.split()
        ids = [self.word2idx.get('<BOS>', 2)]
        for w in tokens[:max_length - 2]:
            ids.append(self.word2idx.get(w, self.word2idx.get('<UNK>', 1)))
        ids.append(self.word2idx.get('<EOS>', 3))
        return ids

    def decode(self, ids):
        skip = {'<PAD>', '<BOS>', '<EOS>', '<SEP>', '<UNK>', '<Q>', '<A>'}
        words = []
        for i in ids:
            w = self.idx2word.get(i, '<UNK>')
            if w not in skip:
                words.append(w)
        return ' '.join(words)


# ── Knowledge Base Retrieval ──────────────────────────────────────────

class KnowledgeRetriever:
    """Simple TF-IDF keyword retrieval from the vector store."""

    def __init__(self):
        self._chunks = []
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        try:
            from app.ai.vector_store import list_sources, get_count
            self._loaded = True
        except Exception:
            pass

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        self._load()
        try:
            from app.ai.vector_store import _get_collection
            collection = _get_collection()
            results = collection.query(query_texts=[query], n_results=top_k)
            sources = []
            if results and results.get('documents'):
                for doc, meta, dist in zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0],
                ):
                    sources.append({
                        "text": doc,
                        "source": meta.get('source', 'unknown'),
                        "type": meta.get('doc_type', 'unknown'),
                        "relevance": round(max(0, 1 - dist), 3),
                    })
            return sources
        except Exception:
            return []


# ── Inference Engine ──────────────────────────────────────────────────

class InferenceEngine:
    """Thread-safe local inference engine.

    Primary: RAG extraction (coherent, factually grounded).
    Secondary: TinyLlama (high-quality, requires download).
    Fallback: SovereignGPT custom model (domain-specific but less coherent).
    """

    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._lock = threading.Lock()
        self._retriever = KnowledgeRetriever()
        self._coherent = None
        self._tinyllama = None
        self._load_time = None

    def _ensure_loaded(self) -> bool:
        """Load model if not already loaded."""
        if self._model is not None:
            return True
        try:
            checkpoint_path = MODEL_DIR / "model.pt"
            if not checkpoint_path.exists():
                return False
            checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
            config = checkpoint['config']
            self._model = SovereignGPT(**config)
            self._model.load_state_dict(checkpoint['model_state_dict'])
            self._model.eval()
            tok_data = checkpoint['tokenizer']
            self._tokenizer = WordTokenizer(tok_data['word2idx'], tok_data['idx2word'])
            self._load_time = time.time()
            return True
        except Exception as e:
            print(f"Model load error: {e}")
            return False

    def generate(self, prompt: str, max_new_tokens: int = 150, temperature: float = 0.8) -> Dict[str, Any]:
        """Generate text from a prompt.

        Primary: RAG extraction (coherent, factually grounded).
        Secondary: TinyLlama (high-quality, requires download).
        Fallback: SovereignGPT custom model.
        """
        # Try coherent responder first (always works, no model loading needed)
        try:
            from app.ai.coherent import get_responder
            if self._coherent is None:
                self._coherent = get_responder()
            result = self._coherent.respond(prompt, top_k=5, max_sentences=5)
            return result
        except Exception:
            pass

        # Try TinyLlama (higher quality if available)
        try:
            from app.ai.tiny_llama import get_tinyllama
            if self._tinyllama is None:
                self._tinyllama = get_tinyllama()
            tl_result = self._tinyllama.generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature)
            if tl_result.get("text") and not tl_result.get("error"):
                return tl_result
        except Exception:
            pass

        # Fallback to SovereignGPT
        with self._lock:
            if not self._ensure_loaded():
                return {"text": "I can provide information from my knowledge base. Please ask a specific question about sovereign debt, bonds, or fiscal policy.", "model": "fallback"}

            start = time.time()
            model_max_seq = self._model.config.get('max_seq', 512)
            max_input = min(256, model_max_seq - 10)
            ids = self._tokenizer.encode(prompt[:max_input * 4], max_length=max_input)
            input_t = torch.tensor([ids], dtype=torch.long)

            with torch.no_grad():
                for _ in range(min(max_new_tokens, 200)):
                    logits = self._model(input_t)
                    next_logits = logits[:, -1, :] / max(temperature, 0.01)
                    probs = F.softmax(next_logits, dim=-1)
                    next_token = torch.multinomial(probs, 1)
                    input_t = torch.cat([input_t, next_token], dim=1)
                    if input_t.shape[1] >= model_max_seq:
                        break
                    if next_token.item() == self._tokenizer.word2idx.get('<EOS>', 3):
                        break

            generated = self._tokenizer.decode(input_t[0].tolist())
            elapsed = time.time() - start
            n_tokens = input_t.shape[1] - len(ids)

            return {
                "text": generated,
                "model": "sovereign_gpt",
                "tokens_generated": n_tokens,
                "latency_ms": round(elapsed * 1000),
                "tokens_per_second": round(n_tokens / max(elapsed, 0.001), 1),
            }

    def query_with_rag(self, question: str, max_new_tokens: int = 200, temperature: float = 0.7) -> Dict[str, Any]:
        """RAG query: retrieve context, then generate coherent answer."""
        # Try coherent responder first
        try:
            from app.ai.coherent import get_responder
            if self._coherent is None:
                self._coherent = get_responder()
            result = self._coherent.respond(question, top_k=5, max_sentences=6)
            result["query"] = question
            return result
        except Exception:
            pass

        # Try TinyLlama with RAG context
        sources = self._retriever.retrieve(question, top_k=3)
        context = "\n".join([s["text"][:300] for s in sources[:3]])

        try:
            from app.ai.tiny_llama import get_tinyllama
            if self._tinyllama is None:
                self._tinyllama = get_tinyllama()
            prompt = f"Based on this context:\n{context}\n\nAnswer the question: {question}"
            tl_result = self._tinyllama.generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature)
            if tl_result.get("text") and not tl_result.get("error"):
                tl_result["sources"] = sources
                tl_result["query"] = question
                return tl_result
        except Exception:
            pass

        # Fallback to SovereignGPT RAG
        context = "\n".join([s["text"][:300] for s in sources[:3]])
        prompt = f"Context: {context}\n\nQuestion: {question}\nAnswer:"
        result = self.generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature)
        result["sources"] = sources
        result["query"] = question
        return result

    def status(self) -> Dict[str, Any]:
        tl_status = {}
        try:
            from app.ai.tiny_llama import get_tinyllama
            tl_status = get_tinyllama().status()
        except Exception:
            tl_status = {"available": False}

        return {
            "model_loaded": self._model is not None,
            "model_name": "sovereign_gpt + rag_extraction + tinyllama",
            "parameters_m": round(sum(p.numel() for p in self._model.parameters()) / 1e6, 1) if self._model else 0,
            "load_time": round(time.time() - self._load_time, 1) if self._load_time else None,
            "knowledge_chunks": 24,
            "tinyllama": tl_status,
        }


# Singleton
_engine = None

def get_engine() -> InferenceEngine:
    global _engine
    if _engine is None:
        _engine = InferenceEngine()
    return _engine
