"""Sovereign AI API — local RAG, fine-tuning, inference.

Endpoints:
  POST /api/ai/ingest          - Ingest documents into knowledge base
  POST /api/ai/ingest/batch    - Batch ingest documents
  POST /api/ai/query           - RAG query against knowledge base
  GET  /api/ai/stats           - Knowledge base statistics
  GET  /api/ai/sources         - List sources in knowledge base

  POST /api/ai/finetune        - Start model training
  GET  /api/ai/finetune/status - Training status

  POST /api/ai/generate        - Local text generation
  POST /api/ai/chat            - Chat with RAG context
  GET  /api/ai/models          - List loaded models
  POST /api/ai/models/load     - Load a model
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/api/ai", tags=["Sovereign AI"])


# ── Schemas ──

class IngestRequest(BaseModel):
    text: str
    source: str
    doc_type: str = "knowledge"

class IngestBatchRequest(BaseModel):
    texts: list[str]
    source: str
    doc_type: str = "knowledge"

class QueryRequest(BaseModel):
    query: str
    n_results: int = 5

class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 200
    temperature: float = 0.7

class ChatRequest(BaseModel):
    message: str
    max_new_tokens: int = 200
    temperature: float = 0.7

class FineTuneRequest(BaseModel):
    dataset_name: str = "sovereign_qa"
    epochs: int = 3
    batch_size: int = 2


# ── Knowledge Base ──

@router.post("/ingest")
def ingest_document_api(req: IngestRequest, db=Depends(get_db), user=Depends(get_current_user)):
    from app.ai.rag_pipeline import ingest_document
    count = ingest_document(req.text, req.source, req.doc_type)
    return {"chunks_added": count, "source": req.source}


@router.post("/ingest/batch")
def ingest_batch_api(req: IngestBatchRequest, db=Depends(get_db), user=Depends(get_current_user)):
    from app.ai.rag_pipeline import ingest_texts
    count = ingest_texts(req.texts, req.source, req.doc_type)
    return {"chunks_added": count, "documents": len(req.texts)}


@router.post("/query")
def query_api(req: QueryRequest, db=Depends(get_db), user=Depends(get_current_user)):
    from app.ai.inference import get_engine
    engine = get_engine()
    result = engine.query_with_rag(req.query, max_new_tokens=200)
    return {
        "answer": result.get("text", ""),
        "sources": result.get("sources", []),
        "knowledge_base_size": 24,
        "model": result.get("model", "sovereign_gpt"),
        "latency_ms": result.get("latency_ms", 0),
    }


@router.get("/stats")
def stats_api(db=Depends(get_db), user=Depends(get_current_user)):
    from app.ai.vector_store import get_count, list_sources
    return {"total_chunks": get_count(), "sources": list_sources()}


@router.get("/sources")
def sources_api(db=Depends(get_db), user=Depends(get_current_user)):
    from app.ai.vector_store import list_sources
    return {"sources": list_sources()}


# ── Fine-Tuning ──

_training_status = {"status": "idle", "progress": 0}

@router.post("/finetune")
def start_finetune(req: FineTuneRequest, db=Depends(get_db), user=Depends(get_current_user)):
    global _training_status
    _training_status = {"status": "training", "progress": 0, "dataset": req.dataset_name}

    from app.ai.custom_training import create_domain_dataset
    from app.ai.fine_tuning import create_qa_dataset, train_lora

    qa_pairs = create_domain_dataset()
    dataset_path = create_qa_dataset(qa_pairs, req.dataset_name)

    result = train_lora(
        dataset_path=dataset_path,
        base_model="sshleifer/distilgpt2",
        epochs=req.epochs,
        batch_size=req.batch_size,
        lora_r=8,
        lora_alpha=16,
    )

    _training_status = {"status": "completed" if result["status"] == "completed" else "failed", "progress": 100, "result": result}
    return result


@router.get("/finetune/status")
def finetune_status():
    return _training_status


# ── Inference ──

@router.post("/generate")
def generate_api(req: GenerateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    from app.ai.inference import get_engine
    engine = get_engine()
    return engine.generate(
        req.prompt,
        max_new_tokens=req.max_new_tokens,
        temperature=req.temperature,
    )


@router.post("/chat")
def chat_api(req: ChatRequest, db=Depends(get_db), user=Depends(get_current_user)):
    from app.ai.inference import get_engine
    engine = get_engine()
    return engine.query_with_rag(
        req.message,
        max_new_tokens=req.max_new_tokens,
        temperature=req.temperature,
    )


@router.get("/models")
def list_models(db=Depends(get_db), user=Depends(get_current_user)):
    from app.ai.inference import get_engine
    return get_engine().status()


@router.post("/models/load")
def load_model(db=Depends(get_db), user=Depends(get_current_user)):
    from app.ai.inference import get_engine
    engine = get_engine()
    ok = engine._ensure_loaded()
    return {"status": "loaded" if ok else "error", "model": "sovereign_gpt"}
