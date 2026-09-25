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

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func

from app.database import get_db
from app.security import get_current_user


def _gen_uuid() -> str:
    import uuid
    return str(uuid.uuid4())


def _utcnow():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)

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

class HistoryTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str
    max_new_tokens: int = 200
    temperature: float = 0.7
    # Recent conversation turns (oldest→newest). Lets follow-ups like
    # "what about 100bps?" resolve against the previous exchange.
    history: Optional[list[HistoryTurn]] = None
    # Persisted-thread support: attach the turn to a conversation. When
    # conversation_id is omitted a new thread is created automatically.
    conversation_id: Optional[str] = None


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    preview: str

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
    from app.ai.portfolio_context import build_portfolio_context, format_portfolio_context_text
    engine = get_engine()
    ctx = build_portfolio_context(req.query, user, db)
    context_block = format_portfolio_context_text(ctx) if ctx else None
    result = engine.query_with_rag(req.query, max_new_tokens=200, context_block=context_block)
    if ctx:
        result["portfolio_context"] = ctx
    return {
        "answer": result.get("text", ""),
        "sources": result.get("sources", []),
        "knowledge_base_size": 24,
        "model": result.get("model", "quantive_ai"),
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
    from app.ai.portfolio_context import (
        build_portfolio_context, format_portfolio_context_text, resolve_followup,
    )
    from app.models import ChatConversation, ChatMessage
    engine = get_engine()
    history = [t.model_dump() for t in (req.history or [])][-8:]
    # Conversation memory: rewrite "what about 100bps?" into a standalone
    # query that carries the antecedent, so retrieval and the portfolio
    # classifier see the full intent.
    resolved = resolve_followup(req.message, history)
    ctx = build_portfolio_context(resolved, user, db, shock_source=req.message)
    context_block = format_portfolio_context_text(ctx) if ctx else None
    result = engine.query_with_rag(
        resolved,
        max_new_tokens=req.max_new_tokens,
        temperature=req.temperature,
        context_block=context_block,
    )
    result["query"] = req.message
    if resolved != req.message:
        result["resolved_query"] = resolved
    if ctx:
        result["portfolio_context"] = ctx

    # ── Persist the exchange ──
    answer = str(result.get("text") or result.get("answer") or "")
    sources = result.get("sources") or []
    try:
        conv = None
        if req.conversation_id:
            conv = (
                db.query(ChatConversation)
                .filter(
                    ChatConversation.id == req.conversation_id,
                    ChatConversation.org_id == user.org_id,
                    ChatConversation.user_id == user.id,
                )
                .first()
            )
        if conv is None:
            conv = ChatConversation(
                id=_gen_uuid(),
                org_id=user.org_id,
                user_id=user.id,
                title=(req.message or "New conversation")[:255],
            )
            db.add(conv)
            db.flush()
        next_seq = (
            db.query(func.max(ChatMessage.seq))
            .filter(ChatMessage.conversation_id == conv.id)
            .scalar()
        )
        next_seq = (next_seq or 0) + 1
        db.add(ChatMessage(
            id=_gen_uuid(), conversation_id=conv.id, org_id=user.org_id,
            role="user", content=(req.message or "")[:4000], seq=next_seq,
        ))
        db.add(ChatMessage(
            id=_gen_uuid(), conversation_id=conv.id, org_id=user.org_id,
            role="assistant", content=answer[:4000], sources=sources[:5], seq=next_seq + 1,
        ))
        if conv.title in ("", "New conversation"):
            conv.title = (req.message or "New conversation")[:255]
        conv.updated_at = _utcnow()
        db.commit()
        result["conversation_id"] = conv.id
    except Exception:
        import logging
        logging.getLogger("uvicorn.error").exception("Chat conversation persistence failed")
        db.rollback()
        # Chat must keep working even if persistence hiccups.

    return result


@router.get("/models")
def list_models(db=Depends(get_db), user=Depends(get_current_user)):
    from app.ai.inference import get_engine
    return get_engine().status()


@router.post("/models/load")
def load_model(db=Depends(get_db), user=Depends(get_current_user)):
    from app.ai.inference import get_engine
    engine = get_engine()
    ok = engine._ensure_loaded()
    return {"status": "loaded" if ok else "error", "model": "quantive_ai"}


# ── Conversation persistence ─────────────────────────────────────────

@router.get("/conversations")
def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """List the caller's chat threads, newest activity first."""
    from app.models import ChatConversation, ChatMessage

    convs = (
        db.query(ChatConversation)
        .filter(ChatConversation.org_id == user.org_id, ChatConversation.user_id == user.id)
        .order_by(ChatConversation.updated_at.desc())
        .limit(limit)
        .all()
    )
    out = []
    for c in convs:
        first_msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == c.id, ChatMessage.role == "user")
            .order_by(ChatMessage.created_at.asc())
            .first()
        )
        count = (
            db.query(func.count(ChatMessage.id))
            .filter(ChatMessage.conversation_id == c.id)
            .scalar()
        )
        out.append({
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "message_count": int(count or 0),
            "preview": (first_msg.content[:80] if first_msg else ""),
        })
    return {"conversations": out}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Delete a thread and all its messages (org/user scoped)."""
    from app.models import ChatConversation, ChatMessage

    conv = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == conversation_id,
            ChatConversation.org_id == user.org_id,
            ChatConversation.user_id == user.id,
        )
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.query(ChatMessage).filter(ChatMessage.conversation_id == conv.id).delete()
    db.delete(conv)
    db.commit()
    return {"deleted": conversation_id}


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Fetch one conversation with all its turns (restores the thread)."""
    from app.models import ChatConversation, ChatMessage

    conv = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == conversation_id,
            ChatConversation.org_id == user.org_id,
            ChatConversation.user_id == user.id,
        )
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conv.id)
        .order_by(ChatMessage.seq.asc(), ChatMessage.created_at.asc())
        .all()
    )
    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "sources": m.sources or [],
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ],
    }
