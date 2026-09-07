"""Government Pilot Program API endpoints.

Exposes pilot tracking, case study generation, and metrics
for managing the "First Five" government pilots.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.pilot_program import (
    GovernmentPilot,
    PilotMilestone,
    PilotMetric,
    PilotCaseStudy,
    PilotStatus,
    PilotTier,
    ConversionStatus,
)
from app.security import get_current_user

router = APIRouter(prefix="/api/pilot-program", tags=["pilot-program"])


# ── Request Models ─────────────────────────────────────────────────

class PilotRequest(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=3)
    country_name: str = Field(..., min_length=2, max_length=255)
    government_entity: str = Field(..., min_length=2, max_length=255)
    entity_type: str = Field(..., description="DMO, Ministry, Central Bank")
    contact_name: str = Field(..., min_length=2, max_length=255)
    contact_title: str = Field(..., min_length=2, max_length=255)
    contact_email: str = Field(..., min_length=5)
    total_debt_outstanding: float = Field(..., gt=0)
    annual_issuance: float = Field(..., ge=0)
    currency: str = Field(default="USD", max_length=3)
    debt_to_gdp: float = Field(default=0.0, ge=0, le=200)


class MilestoneRequest(BaseModel):
    pilot_id: str
    milestone_name: str = Field(..., min_length=2, max_length=255)
    milestone_type: str = Field(..., description="deployment, training, go-live, etc.")
    target_date: str = Field(..., description="ISO 8601 date")


class MetricRequest(BaseModel):
    pilot_id: str
    metric_name: str = Field(..., min_length=2, max_length=100)
    metric_value: float
    metric_unit: str = Field(..., max_length=50)
    notes: str | None = Field(default=None, max_length=1000)


# ── API Endpoints ──────────────────────────────────────────────────

@router.get("/pilots")
def list_pilots(
    status: PilotStatus | None = None,
    tier: PilotTier | None = None,
    region: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List all government pilot programs."""
    query = db.query(GovernmentPilot)

    if status:
        query = query.filter(GovernmentPilot.status == status)
    if tier:
        query = query.filter(GovernmentPilot.portfolio_tier == tier)

    total = query.count()
    pilots = query.order_by(GovernmentPilot.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "pilots": [_format_pilot(p) for p in pilots],
    }


@router.post("/pilots")
def create_pilot(
    request: PilotRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new government pilot program."""
    # Determine tier based on debt size
    if request.total_debt_outstanding < 1_000_000_000:
        tier = PilotTier.STARTER
    elif request.total_debt_outstanding < 10_000_000_000:
        tier = PilotTier.PROFESSIONAL
    elif request.total_debt_outstanding < 100_000_000_000:
        tier = PilotTier.ENTERPRISE
    else:
        tier = PilotTier.SOVEREIGN

    pilot = GovernmentPilot(
        country_code=request.country_code.upper(),
        country_name=request.country_name,
        government_entity=request.government_entity,
        entity_type=request.entity_type,
        contact_name=request.contact_name,
        contact_title=request.contact_title,
        contact_email=request.contact_email,
        total_debt_outstanding=request.total_debt_outstanding,
        annual_issuance=request.annual_issuance,
        currency=request.currency,
        debt_to_gdp=request.debt_to_gdp,
        portfolio_tier=tier,
        status=PilotStatus.PROSPECTING,
        conversion_status=ConversionStatus.PENDING,
    )

    db.add(pilot)
    db.commit()
    db.refresh(pilot)

    # Create default milestones
    default_milestones = [
        {"name": "Pilot Agreement Signed", "type": "agreement", "offset_days": 0},
        {"name": "Infrastructure Setup", "type": "deployment", "offset_days": 14},
        {"name": "Data Import Complete", "type": "data", "offset_days": 30},
        {"name": "Staff Training", "type": "training", "offset_days": 45},
        {"name": "Go-Live", "type": "go_live", "offset_days": 60},
        {"name": "First Optimization Run", "type": "milestone", "offset_days": 90},
        {"name": "3-Month Review", "type": "review", "offset_days": 90},
        {"name": "6-Month Review", "type": "review", "offset_days": 180},
        {"name": "12-Month Review", "type": "review", "offset_days": 365},
    ]

    now = datetime.now(timezone.utc)
    for m in default_milestones:
        milestone = PilotMilestone(
            pilot_id=pilot.id,
            milestone_name=m["name"],
            milestone_type=m["type"],
            target_date=now + timedelta(days=m["offset_days"]),
            status="pending",
        )
        db.add(milestone)

    db.commit()

    return {
        "pilot": _format_pilot(pilot),
        "milestones_created": len(default_milestones),
        "message": f"Pilot program created for {request.country_name}. {len(default_milestones)} milestones configured.",
    }


@router.get("/pilots/{pilot_id}")
def get_pilot(
    pilot_id: str,
    db: Session = Depends(get_db),
):
    """Get detailed pilot information."""
    pilot = db.query(GovernmentPilot).filter(GovernmentPilot.id == pilot_id).first()
    if not pilot:
        raise HTTPException(404, "Pilot not found")

    milestones = db.query(PilotMilestone).filter(
        PilotMilestone.pilot_id == pilot_id
    ).order_by(PilotMilestone.target_date).all()

    metrics = db.query(PilotMetric).filter(
        PilotMetric.pilot_id == pilot_id
    ).order_by(PilotMetric.recorded_date.desc()).limit(50).all()

    case_study = db.query(PilotCaseStudy).filter(
        PilotCaseStudy.pilot_id == pilot_id
    ).first()

    return {
        "pilot": _format_pilot(pilot),
        "milestones": [_format_milestone(m) for m in milestones],
        "metrics": [_format_metric(m) for m in metrics],
        "case_study": _format_case_study(case_study) if case_study else None,
    }


@router.put("/pilots/{pilot_id}/status")
def update_pilot_status(
    pilot_id: str,
    status: PilotStatus,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update pilot program status."""
    pilot = db.query(GovernmentPilot).filter(GovernmentPilot.id == pilot_id).first()
    if not pilot:
        raise HTTPException(404, "Pilot not found")

    pilot.status = status

    # Set dates based on status
    now = datetime.now(timezone.utc)
    if status == PilotStatus.ACTIVE and not pilot.start_date:
        pilot.start_date = now
        pilot.end_date = now + timedelta(days=365)
    elif status == PilotStatus.COMPLETED:
        pilot.conversion_date = now

    db.commit()

    return {"pilot": _format_pilot(pilot)}


@router.post("/pilots/{pilot_id}/milestones")
def create_milestone(
    pilot_id: str,
    request: MilestoneRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a milestone to a pilot."""
    pilot = db.query(GovernmentPilot).filter(GovernmentPilot.id == pilot_id).first()
    if not pilot:
        raise HTTPException(404, "Pilot not found")

    milestone = PilotMilestone(
        pilot_id=pilot_id,
        milestone_name=request.milestone_name,
        milestone_type=request.milestone_type,
        target_date=datetime.fromisoformat(request.target_date.replace("Z", "+00:00")),
        status="pending",
    )

    db.add(milestone)
    db.commit()
    db.refresh(milestone)

    return {"milestone": _format_milestone(milestone)}


@router.post("/pilots/{pilot_id}/metrics")
def record_metric(
    pilot_id: str,
    request: MetricRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a metric for a pilot."""
    pilot = db.query(GovernmentPilot).filter(GovernmentPilot.id == pilot_id).first()
    if not pilot:
        raise HTTPException(404, "Pilot not found")

    metric = PilotMetric(
        pilot_id=pilot_id,
        metric_name=request.metric_name,
        metric_value=request.metric_value,
        metric_unit=request.metric_unit,
        recorded_date=datetime.now(timezone.utc),
        notes=request.notes,
    )

    db.add(metric)

    # Update pilot metrics based on metric name
    if request.metric_name == "financing_cost_reduction_bps":
        pilot.financing_cost_reduction_bps = request.metric_value
    elif request.metric_name == "risk_score_improvement_pct":
        pilot.risk_score_improvement_pct = request.metric_value
    elif request.metric_name == "user_adoption_rate_pct":
        pilot.user_adoption_rate_pct = request.metric_value

    db.commit()
    db.refresh(metric)

    return {"metric": _format_metric(metric)}


@router.post("/pilots/{pilot_id}/generate-case-study")
def generate_case_study(
    pilot_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a case study template for a pilot."""
    pilot = db.query(GovernmentPilot).filter(GovernmentPilot.id == pilot_id).first()
    if not pilot:
        raise HTTPException(404, "Pilot not found")

    # Generate template based on pilot data
    case_study = PilotCaseStudy(
        pilot_id=pilot_id,
        title=f"How {pilot.country_name} Optimized ${pilot.total_debt_outstanding / 1e9:.0f}B in Sovereign Debt",
        subtitle=f"A {pilot.entity_type} Digital Transformation Case Study",
        executive_summary=(
            f"{pilot.government_entity} partnered with Quantive for a 12-month pilot "
            f"to modernize their sovereign debt management practices. "
            f"With a portfolio of ${pilot.total_debt_outstanding / 1e9:.1f}B, "
            f"they achieved measurable improvements in financing costs, risk management, "
            f"and operational efficiency."
        ),
        challenge=(
            f"The {pilot.entity_type} faced challenges with legacy debt management systems, "
            f"manual processes, and limited analytics capabilities. "
            f"With annual issuance of ${pilot.annual_issuance / 1e9:.1f}B, "
            f"they needed a modern solution to optimize their debt portfolio."
        ),
        solution=(
            "Quantive deployed its Zero Trust Sovereign Mode, running entirely within "
            "the government's infrastructure. The platform provided real-time portfolio "
            "analysis, optimization recommendations, and scenario modeling."
        ),
        results={
            "financing_cost_reduction_bps": pilot.financing_cost_reduction_bps,
            "risk_score_improvement_pct": pilot.risk_score_improvement_pct,
            "user_adoption_rate_pct": pilot.user_adoption_rate_pct,
            "total_debt_managed": pilot.total_debt_outstanding,
            "annual_savings_estimate": pilot.total_debt_outstanding * pilot.financing_cost_reduction_bps / 10000,
        },
        status="draft",
    )

    db.add(case_study)
    db.commit()
    db.refresh(case_study)

    return {
        "case_study": _format_case_study(case_study),
        "message": "Case study template generated. Review and customize before publishing.",
    }


@router.get("/dashboard")
def get_pilot_dashboard(
    db: Session = Depends(get_db),
):
    """Get pilot program dashboard with key metrics."""
    pilots = db.query(GovernmentPilot).all()

    # Status counts
    status_counts = {}
    for p in pilots:
        status = p.status.value if hasattr(p.status, 'value') else str(p.status)
        status_counts[status] = status_counts.get(status, 0) + 1

    # Tier counts
    tier_counts = {}
    for p in pilots:
        tier = p.portfolio_tier.value if hasattr(p.portfolio_tier, 'value') else str(p.portfolio_tier)
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    # Conversion metrics
    active_pilots = [p for p in pilots if p.status == PilotStatus.ACTIVE]
    completed_pilots = [p for p in pilots if p.status == PilotStatus.COMPLETED]
    converted = [p for p in completed_pilots if p.conversion_status == ConversionStatus.CONVERTED]

    total_debt = sum(p.total_debt_outstanding for p in pilots)
    total_conversion_value = sum(p.conversion_value_usd for p in converted)

    return {
        "summary": {
            "total_pilots": len(pilots),
            "active_pilots": len(active_pilots),
            "completed_pilots": len(completed_pilots),
            "converted_pilots": len(converted),
            "conversion_rate": round(len(converted) / len(completed_pilots) * 100, 1) if completed_pilots else 0,
            "total_debt_managed": total_debt,
            "total_conversion_value": total_conversion_value,
        },
        "status_counts": status_counts,
        "tier_counts": tier_counts,
        "top_pilots": [_format_pilot(p) for p in sorted(pilots, key=lambda x: x.total_debt_outstanding, reverse=True)[:5]],
    }


@router.get("/first-five")
def get_first_five_targets():
    """Get recommended 'First Five' government targets based on 6.md criteria."""
    return {
        "criteria": [
            "Different income levels (low, lower-middle, upper-middle, high)",
            "Different geographies (Africa, Asia, Latin America, Europe, Middle East)",
            "Digital-first governments or those with reform mandates",
            "DMOs with existing technology adoption",
            "Countries with active debt management reform programs",
        ],
        "recommended_targets": [
            {
                "rank": 1,
                "country": "Kenya",
                "region": "Africa",
                "income_group": "Lower-middle",
                "rationale": "Active DMO reform, IMF program, growing debt portfolio, digital-first government initiative",
                "entity_type": "DMO",
                "total_debt_outstanding": 70_000_000_000,
                "contact_priority": "High",
            },
            {
                "rank": 2,
                "country": "Peru",
                "region": "Latin America",
                "income_group": "Upper-middle",
                "rationale": "Strong fiscal framework, modern DMO, active in international capital markets",
                "entity_type": "DMO",
                "total_debt_outstanding": 50_000_000_000,
                "contact_priority": "High",
            },
            {
                "rank": 3,
                "country": "Indonesia",
                "region": "Asia",
                "income_group": "Lower-middle",
                "rationale": "Large debt portfolio, active debt management reform, strong institutional capacity",
                "entity_type": "DMO",
                "total_debt_outstanding": 200_000_000_000,
                "contact_priority": "Medium",
            },
            {
                "rank": 4,
                "country": "Georgia",
                "region": "Europe/Central Asia",
                "income_group": "Lower-middle",
                "rationale": "Small but sophisticated DMO, strong reform agenda, World Bank engagement",
                "entity_type": "DMO",
                "total_debt_outstanding": 8_000_000_000,
                "contact_priority": "Medium",
            },
            {
                "rank": 5,
                "country": "Jordan",
                "region": "Middle East",
                "income_group": "Upper-middle",
                "rationale": "Active debt management, IMF program, reform-minded DMO, strategic location",
                "entity_type": "DMO",
                "total_debt_outstanding": 25_000_000_000,
                "contact_priority": "High",
            },
        ],
    }


# ── Helper serializers ──────────────────────────────────────────────

def _format_pilot(pilot: GovernmentPilot) -> dict:
    status = pilot.status.value if hasattr(pilot.status, 'value') else str(pilot.status)
    tier = pilot.portfolio_tier.value if hasattr(pilot.portfolio_tier, 'value') else str(pilot.portfolio_tier)
    conversion = pilot.conversion_status.value if hasattr(pilot.conversion_status, 'value') else str(pilot.conversion_status)

    return {
        "id": pilot.id,
        "country_code": pilot.country_code,
        "country_name": pilot.country_name,
        "government_entity": pilot.government_entity,
        "entity_type": pilot.entity_type,
        "contact_name": pilot.contact_name,
        "contact_email": pilot.contact_email,
        "total_debt_outstanding": pilot.total_debt_outstanding,
        "annual_issuance": pilot.annual_issuance,
        "currency": pilot.currency,
        "debt_to_gdp": pilot.debt_to_gdp,
        "portfolio_tier": tier,
        "status": status,
        "start_date": pilot.start_date.isoformat() if pilot.start_date else None,
        "end_date": pilot.end_date.isoformat() if pilot.end_date else None,
        "financing_cost_reduction_bps": pilot.financing_cost_reduction_bps,
        "risk_score_improvement_pct": pilot.risk_score_improvement_pct,
        "user_adoption_rate_pct": pilot.user_adoption_rate_pct,
        "conversion_status": conversion,
        "conversion_value_usd": pilot.conversion_value_usd,
        "case_study_published": pilot.case_study_published,
        "created_at": pilot.created_at.isoformat() if pilot.created_at else None,
    }


def _format_milestone(milestone: PilotMilestone) -> dict:
    return {
        "id": milestone.id,
        "milestone_name": milestone.milestone_name,
        "milestone_type": milestone.milestone_type,
        "target_date": milestone.target_date.isoformat() if milestone.target_date else None,
        "completed_date": milestone.completed_date.isoformat() if milestone.completed_date else None,
        "status": milestone.status,
    }


def _format_metric(metric: PilotMetric) -> dict:
    return {
        "id": metric.id,
        "metric_name": metric.metric_name,
        "metric_value": metric.metric_value,
        "metric_unit": metric.metric_unit,
        "recorded_date": metric.recorded_date.isoformat() if metric.recorded_date else None,
        "notes": metric.notes,
    }


def _format_case_study(case_study: PilotCaseStudy) -> dict:
    return {
        "id": case_study.id,
        "title": case_study.title,
        "subtitle": case_study.subtitle,
        "executive_summary": case_study.executive_summary,
        "challenge": case_study.challenge,
        "solution": case_study.solution,
        "results": case_study.results,
        "status": case_study.status,
        "published_url": case_study.published_url,
    }
