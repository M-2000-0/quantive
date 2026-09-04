"""Support API — tickets, FAQ, bug reports, AI chatbot."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.support import (
    BugReport,
    FAQCategory,
    FAQItem,
    SupportMessage,
    SupportTicket,
)
from app.security import get_current_user

router = APIRouter(prefix="/api/support", tags=["support"])


# ── Ticket Schemas ────────────────────────────────────────────────


class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    category: str = "general"
    priority: str = "medium"


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


class TicketMessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    is_internal: bool = False


class TicketResponse(BaseModel):
    id: str
    subject: str
    description: str
    status: str
    priority: str
    category: str
    assigned_to: Optional[str]
    escalated: bool
    escalation_level: int
    message_count: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class FAQCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class FAQItemCreate(BaseModel):
    category_id: str
    question: str = Field(..., min_length=1, max_length=1000)
    answer: str = Field(..., min_length=1)


class BugReportCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    severity: str = "medium"
    steps_to_reproduce: str = ""
    expected_behavior: str = ""
    actual_behavior: str = ""
    environment: str = ""


class BugReportResponse(BaseModel):
    id: str
    title: str
    description: str
    severity: str
    status: str
    reported_by: str
    assigned_to: Optional[str]
    steps_to_reproduce: str
    expected_behavior: str
    actual_behavior: str
    environment: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ── Tickets ───────────────────────────────────────────────────────


@router.get("/tickets", response_model=list[TicketResponse])
def list_tickets(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List support tickets."""
    q = db.query(SupportTicket).filter(SupportTicket.org_id == user.org_id)
    if status:
        q = q.filter(SupportTicket.status == status)
    if priority:
        q = q.filter(SupportTicket.priority == priority)
    if category:
        q = q.filter(SupportTicket.category == category)
    tickets = q.order_by(desc(SupportTicket.created_at)).offset(offset).limit(limit).all()
    result = []
    for t in tickets:
        count = db.query(SupportMessage).filter(SupportMessage.ticket_id == t.id).count()
        resp = TicketResponse.model_validate(t).model_dump(mode="json")
        resp["message_count"] = count
        result.append(resp)
    return result


@router.post("/tickets", response_model=TicketResponse, status_code=201)
def create_ticket(data: TicketCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new support ticket."""
    ticket = SupportTicket(
        org_id=user.org_id,
        user_id=user.id,
        subject=data.subject,
        description=data.description,
        category=data.category,
        priority=data.priority,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    resp = TicketResponse.model_validate(ticket).model_dump(mode="json")
    resp["message_count"] = 0
    return resp


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a single ticket."""
    ticket = db.query(SupportTicket).filter(
        SupportTicket.id == ticket_id,
        SupportTicket.org_id == user.org_id,
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    count = db.query(SupportMessage).filter(SupportMessage.ticket_id == ticket.id).count()
    resp = TicketResponse.model_validate(ticket).model_dump(mode="json")
    resp["message_count"] = count
    return resp


@router.put("/tickets/{ticket_id}", response_model=TicketResponse)
def update_ticket(ticket_id: str, data: TicketUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a ticket."""
    ticket = db.query(SupportTicket).filter(
        SupportTicket.id == ticket_id,
        SupportTicket.org_id == user.org_id,
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)
    db.commit()
    db.refresh(ticket)
    return TicketResponse.model_validate(ticket).model_dump(mode="json")


@router.get("/tickets/{ticket_id}/messages")
def list_ticket_messages(ticket_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List messages in a ticket."""
    ticket = db.query(SupportTicket).filter(
        SupportTicket.id == ticket_id,
        SupportTicket.org_id == user.org_id,
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    messages = db.query(SupportMessage).filter(
        SupportMessage.ticket_id == ticket_id
    ).order_by(SupportMessage.created_at).all()
    return [{"id": m.id, "user_id": m.user_id, "content": m.content,
             "is_internal": m.is_internal, "is_ai_generated": m.is_ai_generated,
             "created_at": m.created_at.isoformat() if m.created_at else ""} for m in messages]


@router.post("/tickets/{ticket_id}/messages")
def add_ticket_message(ticket_id: str, data: TicketMessageCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add a message to a ticket."""
    ticket = db.query(SupportTicket).filter(
        SupportTicket.id == ticket_id,
        SupportTicket.org_id == user.org_id,
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    msg = SupportMessage(ticket_id=ticket_id, user_id=user.id, content=data.content, is_internal=data.is_internal)
    db.add(msg)
    if ticket.status == "open":
        ticket.status = "in_progress"
    db.commit()
    return {"ok": True}


# ── FAQ ───────────────────────────────────────────────────────────


@router.get("/faq")
def list_faq(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all FAQ categories and items."""
    categories = db.query(FAQCategory).filter(FAQCategory.org_id == user.org_id).order_by(FAQCategory.sort_order).all()
    result = []
    for cat in categories:
        items = db.query(FAQItem).filter(FAQItem.category_id == cat.id, FAQItem.is_published == True).all()
        result.append({
            "id": cat.id,
            "name": cat.name,
            "description": cat.description,
            "items": [{"id": i.id, "question": i.question, "answer": i.answer, "helpful_count": i.helpful_count} for i in items],
        })
    return result


@router.post("/faq/categories", status_code=201)
def create_faq_category(data: FAQCategoryCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a FAQ category."""
    cat = FAQCategory(org_id=user.org_id, name=data.name, description=data.description)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "name": cat.name}


@router.post("/faq/items", status_code=201)
def create_faq_item(data: FAQItemCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a FAQ item."""
    item = FAQItem(category_id=data.category_id, question=data.question, answer=data.answer, created_by=user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "question": item.question}


@router.post("/faq/items/{item_id}/helpful")
def mark_faq_helpful(item_id: str, db: Session = Depends(get_db)):
    """Mark a FAQ item as helpful."""
    item = db.query(FAQItem).filter(FAQItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="FAQ item not found")
    item.helpful_count += 1
    db.commit()
    return {"helpful_count": item.helpful_count}


# ── Bug Reports ───────────────────────────────────────────────────


@router.get("/bugs", response_model=list[BugReportResponse])
def list_bugs(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List bug reports."""
    q = db.query(BugReport).filter(BugReport.org_id == user.org_id)
    if status:
        q = q.filter(BugReport.status == status)
    if severity:
        q = q.filter(BugReport.severity == severity)
    bugs = q.order_by(desc(BugReport.created_at)).limit(limit).all()
    return [BugReportResponse.model_validate(b).model_dump(mode="json") for b in bugs]


@router.post("/bugs", response_model=BugReportResponse, status_code=201)
def create_bug(data: BugReportCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a bug report."""
    bug = BugReport(
        org_id=user.org_id,
        reported_by=user.id,
        title=data.title,
        description=data.description,
        severity=data.severity,
        steps_to_reproduce=data.steps_to_reproduce,
        expected_behavior=data.expected_behavior,
        actual_behavior=data.actual_behavior,
        environment=data.environment,
    )
    db.add(bug)
    db.commit()
    db.refresh(bug)
    return BugReportResponse.model_validate(bug).model_dump(mode="json")


@router.put("/bugs/{bug_id}", response_model=BugReportResponse)
def update_bug(bug_id: str, data: TicketUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a bug report."""
    bug = db.query(BugReport).filter(BugReport.id == bug_id, BugReport.org_id == user.org_id).first()
    if not bug:
        raise HTTPException(status_code=404, detail="Bug not found")
    if data.status:
        bug.status = data.status
    if data.assigned_to:
        bug.assigned_to = data.assigned_to
    db.commit()
    db.refresh(bug)
    return BugReportResponse.model_validate(bug).model_dump(mode="json")


# ── AI Support Chat ───────────────────────────────────────────────


@router.post("/chat")
def support_chat(data: TicketMessageCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """AI-powered support chat — answers FAQs and creates tickets for complex issues."""
    query = data.content.lower()

    # Search FAQ for matching answers
    faq_items = db.query(FAQItem).filter(FAQItem.is_published == True).all()
    best_match = None
    best_score = 0
    for item in faq_items:
        question_lower = item.question.lower()
        words = query.split()
        score = sum(1 for w in words if w in question_lower)
        if score > best_score:
            best_score = score
            best_match = item

    if best_match and best_score >= 2:
        return {
            "type": "faq_match",
            "response": best_match.answer,
            "faq_id": best_match.id,
            "confidence": min(best_score / 5, 1.0),
        }

    # For unmatched queries, suggest creating a ticket
    return {
        "type": "ticket_suggestion",
        "response": "I couldn't find a matching FAQ. Would you like me to create a support ticket for this?",
        "suggested_category": _classify_query(query),
        "confidence": 0.3,
    }


def _classify_query(query: str) -> str:
    """Simple keyword-based ticket classification."""
    if any(w in query for w in ["billing", "payment", "invoice", "charge", "refund"]):
        return "billing"
    if any(w in query for w in ["bug", "error", "crash", "broken", "not working"]):
        return "bug"
    if any(w in query for w in ["feature", "request", "add", "would be nice", "suggestion"]):
        return "feature_request"
    return "general"
