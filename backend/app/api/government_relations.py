"""Government Relations API endpoints.

Exposes procurement pipeline, RFP tracking, and government sales management
to help win government contracts.
"""

import enum
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/government-relations", tags=["government-relations"])


# ── Enums ──────────────────────────────────────────────────────────

class RFPStatus(str, enum.Enum):
    IDENTIFIED = "identified"
    PREPARING = "preparing"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    SHORTLISTED = "shortlisted"
    NEGOTIATING = "negotiating"
    AWARDED = "awarded"
    LOST = "lost"


class OpportunityStage(str, enum.Enum):
    AWARENESS = "awareness"
    INTEREST = "interest"
    EVALUATION = "evaluation"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class ContactRole(str, enum.Enum):
    DECISION_MAKER = "decision_maker"
    TECHNICAL_EVALUATOR = "technical_evaluator"
    BUDGET_HOLDER = "budget_holder"
    END_USER = "end_user"
    CHAMPION = "champion"
    INFLUENCER = "influencer"


# ── In-memory storage (replace with DB models in production) ────────

_rfps: dict[str, dict] = {}
_opportunities: dict[str, dict] = {}
_contacts: dict[str, dict] = {}
_activities: list[dict] = []


# ── Request Models ─────────────────────────────────────────────────

class RFPRequest(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=3)
    country_name: str = Field(..., min_length=2, max_length=255)
    entity_name: str = Field(..., min_length=2, max_length=255)
    rfp_title: str = Field(..., min_length=5, max_length=500)
    rfp_reference: str | None = Field(default=None, max_length=100)
    estimated_value_usd: float = Field(..., ge=0)
    submission_deadline: str = Field(..., description="ISO 8601 datetime")
    requirements_summary: str | None = Field(default=None, max_length=2000)
    competitor_intel: str | None = Field(default=None, max_length=1000)


class OpportunityRequest(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=3)
    country_name: str = Field(..., min_length=2, max_length=255)
    entity_name: str = Field(..., min_length=2, max_length=255)
    opportunity_name: str = Field(..., min_length=5, max_length=500)
    estimated_value_usd: float = Field(..., ge=0)
    stage: str = Field(default="awareness")
    expected_close_date: str | None = Field(default=None)
    notes: str | None = Field(default=None, max_length=2000)


class ContactRequest(BaseModel):
    government_id: str
    name: str = Field(..., min_length=2, max_length=255)
    title: str = Field(..., min_length=2, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    role: str = Field(default="end_user")
    notes: str | None = Field(default=None, max_length=1000)


# ── API Endpoints ──────────────────────────────────────────────────

@router.get("/rfps")
def list_rfps(
    status: RFPStatus | None = None,
    country_code: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all tracked RFPs."""
    rfps = list(_rfps.values())

    if status:
        rfps = [r for r in rfps if r["status"] == status.value]
    if country_code:
        rfps = [r for r in rfps if r["country_code"] == country_code.upper()]

    # Sort by submission deadline
    rfps.sort(key=lambda r: r.get("submission_deadline", "9999"))

    return {
        "total": len(rfps),
        "rfps": rfps[offset:offset + limit],
    }


@router.post("/rfps")
def create_rfp(
    request: RFPRequest,
    user: User = Depends(get_current_user),
):
    """Track a new government RFP."""
    rfp_id = str(uuid.uuid4())
    rfp = {
        "id": rfp_id,
        "country_code": request.country_code.upper(),
        "country_name": request.country_name,
        "entity_name": request.entity_name,
        "rfp_title": request.rfp_title,
        "rfp_reference": request.rfp_reference,
        "estimated_value_usd": request.estimated_value_usd,
        "submission_deadline": request.submission_deadline,
        "requirements_summary": request.requirements_summary,
        "competitor_intel": request.competitor_intel,
        "status": RFPStatus.IDENTIFIED.value,
        "assigned_to": user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _rfps[rfp_id] = rfp

    # Log activity
    _activities.append({
        "type": "rfp_created",
        "rfp_id": rfp_id,
        "user_id": user.id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {"rfp": rfp}


@router.put("/rfps/{rfp_id}/status")
def update_rfp_status(
    rfp_id: str,
    status: RFPStatus,
    user: User = Depends(get_current_user),
):
    """Update RFP status."""
    if rfp_id not in _rfps:
        raise HTTPException(404, "RFP not found")

    _rfps[rfp_id]["status"] = status.value
    _rfps[rfp_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

    _activities.append({
        "type": "rfp_status_updated",
        "rfp_id": rfp_id,
        "new_status": status.value,
        "user_id": user.id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {"rfp": _rfps[rfp_id]}


@router.get("/opportunities")
def list_opportunities(
    stage: OpportunityStage | None = None,
    country_code: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all government opportunities."""
    opps = list(_opportunities.values())

    if stage:
        opps = [o for o in opps if o["stage"] == stage.value]
    if country_code:
        opps = [o for o in opps if o["country_code"] == country_code.upper()]

    return {
        "total": len(opps),
        "opportunities": opps[offset:offset + limit],
    }


@router.post("/opportunities")
def create_opportunity(
    request: OpportunityRequest,
    user: User = Depends(get_current_user),
):
    """Create a new government opportunity."""
    opp_id = str(uuid.uuid4())
    opportunity = {
        "id": opp_id,
        "country_code": request.country_code.upper(),
        "country_name": request.country_name,
        "entity_name": request.entity_name,
        "opportunity_name": request.opportunity_name,
        "estimated_value_usd": request.estimated_value_usd,
        "stage": request.stage,
        "expected_close_date": request.expected_close_date,
        "notes": request.notes,
        "owner_id": user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _opportunities[opp_id] = opportunity

    return {"opportunity": opportunity}


@router.put("/opportunities/{opp_id}/stage")
def update_opportunity_stage(
    opp_id: str,
    stage: OpportunityStage,
    user: User = Depends(get_current_user),
):
    """Update opportunity stage."""
    if opp_id not in _opportunities:
        raise HTTPException(404, "Opportunity not found")

    _opportunities[opp_id]["stage"] = stage.value
    _opportunities[opp_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

    return {"opportunity": _opportunities[opp_id]}


@router.get("/contacts")
def list_contacts(
    government_id: str | None = None,
    role: ContactRole | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    """List government contacts."""
    contacts = list(_contacts.values())

    if government_id:
        contacts = [c for c in contacts if c["government_id"] == government_id]
    if role:
        contacts = [c for c in contacts if c["role"] == role.value]

    return {
        "total": len(contacts),
        "contacts": contacts[:limit],
    }


@router.post("/contacts")
def create_contact(
    request: ContactRequest,
    user: User = Depends(get_current_user),
):
    """Add a government contact."""
    contact_id = str(uuid.uuid4())
    contact = {
        "id": contact_id,
        "government_id": request.government_id,
        "name": request.name,
        "title": request.title,
        "email": request.email,
        "phone": request.phone,
        "role": request.role,
        "notes": request.notes,
        "added_by": user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _contacts[contact_id] = contact

    return {"contact": contact}


@router.get("/pipeline")
def get_pipeline(
    user: User = Depends(get_current_user),
):
    """Get sales pipeline summary."""
    opps = list(_opportunities.values())

    # Group by stage
    pipeline = {}
    for stage in OpportunityStage:
        stage_opps = [o for o in opps if o["stage"] == stage.value]
        pipeline[stage.value] = {
            "count": len(stage_opps),
            "total_value": sum(o["estimated_value_usd"] for o in stage_opps),
            "opportunities": stage_opps,
        }

    # Calculate metrics
    total_value = sum(o["estimated_value_usd"] for o in opps)
    won_value = sum(
        o["estimated_value_usd"] for o in opps
        if o["stage"] == OpportunityStage.CLOSED_WON.value
    )

    return {
        "pipeline": pipeline,
        "summary": {
            "total_opportunities": len(opps),
            "total_value": total_value,
            "won_value": won_value,
            "win_rate": round(won_value / total_value * 100, 1) if total_value > 0 else 0,
        },
    }


@router.get("/activities")
def get_activities(
    limit: int = Query(50, ge=1, le=200),
):
    """Get recent activities."""
    recent = sorted(_activities, key=lambda a: a["timestamp"], reverse=True)
    return {"activities": recent[:limit]}


@router.get("/dashboard")
def get_gr_dashboard():
    """Get government relations dashboard."""
    rfps = list(_rfps.values())
    opps = list(_opportunities.values())
    contacts = list(_contacts.values())

    # RFP metrics
    active_rfps = [r for r in rfps if r["status"] not in ["awarded", "lost"]]
    total_rfp_value = sum(r["estimated_value_usd"] for r in active_rfps)

    # Opportunity metrics
    total_opp_value = sum(o["estimated_value_usd"] for o in opps)
    weighted_value = sum(
        o["estimated_value_usd"] * _stage_probability(o["stage"])
        for o in opps
    )

    # Geographic distribution
    countries = set()
    for r in rfps:
        countries.add(r["country_code"])
    for o in opps:
        countries.add(o["country_code"])

    return {
        "summary": {
            "total_rfps": len(rfps),
            "active_rfps": len(active_rfps),
            "total_rfp_value": total_rfp_value,
            "total_opportunities": len(opps),
            "total_opp_value": total_opp_value,
            "weighted_pipeline": weighted_value,
            "total_contacts": len(contacts),
            "countries_engaged": len(countries),
        },
        "rfp_by_status": _count_by_field(rfps, "status"),
        "opps_by_stage": _count_by_field(opps, "stage"),
        "top_countries": _top_countries(rfps + opps),
    }


# ── Helper functions ───────────────────────────────────────────────

def _stage_probability(stage: str) -> float:
    """Conversion probability by stage."""
    probabilities = {
        "awareness": 0.1,
        "interest": 0.2,
        "evaluation": 0.35,
        "proposal": 0.5,
        "negotiation": 0.7,
        "closed_won": 1.0,
        "closed_lost": 0.0,
    }
    return probabilities.get(stage, 0.0)


def _count_by_field(items: list, field: str) -> dict:
    counts = {}
    for item in items:
        value = item.get(field, "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _top_countries(items: list) -> list[dict]:
    country_values = {}
    for item in items:
        code = item.get("country_code", "unknown")
        value = item.get("estimated_value_usd", 0)
        country_values[code] = country_values.get(code, 0) + value

    sorted_countries = sorted(country_values.items(), key=lambda x: x[1], reverse=True)
    return [{"country_code": c, "total_value": v} for c, v in sorted_countries[:10]]
