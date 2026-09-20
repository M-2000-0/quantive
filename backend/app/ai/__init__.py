"""AI module — local sovereign debt intelligence.

Zero external LLM APIs. Everything runs on-premise.
"""

from app.ai.embeddings import embed_texts, embed_query, get_dimension
from app.ai.vector_store import add_documents, query, get_count, list_sources
from app.ai.rag_pipeline import ingest_document, ingest_texts, retrieve, rag_query, chunk_text
from app.ai.fine_tuning import create_qa_dataset, train_lora, evaluate_model
from app.ai.custom_training import train_tokenizer, pretrain_model, get_model_config, create_domain_dataset
from app.ai.inference import get_engine

__all__ = [
    "embed_texts", "embed_query", "get_dimension",
    "add_documents", "query", "get_count", "list_sources",
    "ingest_document", "ingest_texts", "retrieve", "rag_query", "chunk_text",
    "create_qa_dataset", "train_lora", "evaluate_model",
    "train_tokenizer", "pretrain_model", "get_model_config", "create_domain_dataset",
    "get_engine",
]
