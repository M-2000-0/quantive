"""TinyLlama integration for enhanced AI responses.

Optional module that loads TinyLlama-1.1B for higher-quality generation.
Only loads if transformers is available and model is downloaded.
"""

import time
import threading
from typing import Dict, Any, Optional

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class TinyLlamaEngine:
    """Thread-safe TinyLlama inference engine."""

    def __init__(self, model_name: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"):
        self._model_name = model_name
        self._model = None
        self._tokenizer = None
        self._lock = threading.Lock()
        self._loaded = False
        self._load_time = None
        self._stats = {"requests": 0, "total_tokens": 0, "avg_latency_ms": 0}

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return True
        if not TRANSFORMERS_AVAILABLE:
            return False

        try:
            with self._lock:
                if self._loaded:
                    return True

                t0 = time.time()
                self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
                self._model = AutoModelForCausalLM.from_pretrained(
                    self._model_name,
                    torch_dtype=torch.float32,
                    device_map="cpu",
                )
                self._model.eval()
                self._loaded = True
                self._load_time = time.time() - t0
                return True
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> Dict[str, Any]:
        """Generate text using TinyLlama."""
        if not self._ensure_loaded():
            return {"error": "TinyLlama not available", "available": False}

        t0 = time.time()

        with self._lock:
            try:
                messages = [
                    {"role": "system", "content": "You are a sovereign debt and macroeconomic analysis expert. Provide clear, factual analysis."},
                    {"role": "user", "content": prompt},
                ]

                input_text = self._tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
                inputs = self._tokenizer(input_text, return_tensors="pt")

                with torch.no_grad():
                    outputs = self._model.generate(
                        **inputs,
                        max_new_tokens=max_new_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        do_sample=True,
                        pad_token_id=self._tokenizer.eos_token_id,
                    )

                generated = self._tokenizer.decode(
                    outputs[0][inputs["input_ids"].shape[1]:],
                    skip_special_tokens=True,
                )

                elapsed = time.time() - t0
                n_tokens = outputs.shape[1] - inputs["input_ids"].shape[1]

                self._stats["requests"] += 1
                self._stats["total_tokens"] += n_tokens
                self._stats["avg_latency_ms"] = round(
                    (self._stats["avg_latency_ms"] * (self._stats["requests"] - 1) + elapsed * 1000)
                    / self._stats["requests"], 1
                )

                return {
                    "text": generated.strip(),
                    "model": "tinyllama",
                    "tokens_generated": n_tokens,
                    "latency_ms": round(elapsed * 1000),
                    "tokens_per_second": round(n_tokens / max(elapsed, 0.001), 1),
                    "available": True,
                }

            except Exception as e:
                return {"error": str(e), "available": True}

    def status(self) -> Dict[str, Any]:
        return {
            "available": TRANSFORMERS_AVAILABLE,
            "loaded": self._loaded,
            "model_name": self._model_name,
            "load_time_s": round(self._load_time, 1) if self._load_time else None,
            "stats": self._stats,
        }


_engine = None


def get_tinyllama() -> TinyLlamaEngine:
    global _engine
    if _engine is None:
        _engine = TinyLlamaEngine()
    return _engine
