"""
FinTech & Sovereign Debt Competitive Intelligence API
=====================================================

Provides CRUD, search, filtering, threat scoring, and comparison
for 300+ fintech/sovereign debt launches tracked for Quantive's
competitive positioning.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, Integer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.fintech_tracker import FintechLaunch

router = APIRouter(prefix="/api/fintech-tracker", tags=["fintech-tracker"])


# ── Response Schemas ────────────────────────────────────────────────

class LaunchDetail(BaseModel):
    id: str
    company_name: str
    company_url: Optional[str] = None
    hq_location: Optional[str] = None
    founded_year: Optional[int] = None
    employee_count: Optional[str] = None
    total_funding: Optional[str] = None
    valuation: Optional[str] = None
    product_name: str
    category: str
    subcategory: str
    description: str
    key_features: Optional[dict] = None
    target_users: Optional[str] = None
    pricing_model: Optional[str] = None
    stage: str
    announced_date: Optional[str] = None
    launch_date: Optional[str] = None
    threat_level: str
    threat_score: Optional[float] = None
    feature_overlap_pct: Optional[float] = None
    quantive_advantage: Optional[str] = None
    competitor_advantage: Optional[str] = None
    market_size_billion: Optional[float] = None
    api_available: bool = False
    open_source: bool = False
    confidence: str = "medium"

    class Config:
        from_attributes = True


class ThreatSummary(BaseModel):
    category: str
    total: int
    critical: int
    high: int
    medium: int
    low: int
    avg_threat_score: float
    avg_feature_overlap: float


class CompetitiveOverview(BaseModel):
    total_competitors: int
    total_categories: int
    threat_distribution: dict[str, int]
    stage_distribution: dict[str, int]
    avg_threat_score: float
    top_threats: list[LaunchDetail]
    categories: list[ThreatSummary]


# ── Endpoints ───────────────────────────────────────────────────────

@router.get("/overview", response_model=CompetitiveOverview)
def get_overview(db: Session = Depends(get_db)):
    """Full competitive overview with threat assessment."""
    total = db.query(func.count(FintechLaunch.id)).scalar() or 0
    categories = db.query(func.count(func.distinct(FintechLaunch.category))).scalar() or 0

    # Threat distribution
    threat_rows = (
        db.query(FintechLaunch.threat_level, func.count(FintechLaunch.id))
        .group_by(FintechLaunch.threat_level)
        .all()
    )
    threat_dist = {t: c for t, c in threat_rows}

    # Stage distribution
    stage_rows = (
        db.query(FintechLaunch.stage, func.count(FintechLaunch.id))
        .group_by(FintechLaunch.stage)
        .all()
    )
    stage_dist = {s: c for s, c in stage_rows}

    # Average scores
    avg_threat = db.query(func.avg(FintechLaunch.threat_score)).scalar() or 0

    # Top threats (highest threat score)
    top_threats_q = (
        db.query(FintechLaunch)
        .filter(FintechLaunch.threat_score.isnot(None))
        .order_by(FintechLaunch.threat_score.desc())
        .limit(10)
        .all()
    )
    top_threats = [LaunchDetail.model_validate(t).model_dump() for t in top_threats_q]

    # Category breakdown
    cat_rows = (
        db.query(
            FintechLaunch.category,
            func.count(FintechLaunch.id),
            func.sum(func.cast(FintechLaunch.threat_level == "critical", Integer)),
            func.sum(func.cast(FintechLaunch.threat_level == "high", Integer)),
            func.sum(func.cast(FintechLaunch.threat_level == "medium", Integer)),
            func.sum(func.cast(FintechLaunch.threat_level == "low", Integer)),
            func.avg(FintechLaunch.threat_score),
            func.avg(FintechLaunch.feature_overlap_pct),
        )
        .group_by(FintechLaunch.category)
        .all()
    )
    cat_summaries = []
    for cat, total_c, crit, high, med, low, avg_t, avg_f in cat_rows:
        cat_summaries.append(ThreatSummary(
            category=cat,
            total=total_c,
            critical=int(crit or 0),
            high=int(high or 0),
            medium=int(med or 0),
            low=int(low or 0),
            avg_threat_score=round(float(avg_t or 0), 1),
            avg_feature_overlap=round(float(avg_f or 0), 1),
        ))

    return CompetitiveOverview(
        total_competitors=total,
        total_categories=categories,
        threat_distribution=threat_dist,
        stage_distribution=stage_dist,
        avg_threat_score=round(float(avg_threat), 1),
        top_threats=top_threats,
        categories=cat_summaries,
    )


@router.get("/search")
def search_launches(
    category: Optional[str] = Query(None),
    subcategory: Optional[str] = Query(None),
    threat_level: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    min_overlap: Optional[float] = Query(None, description="Minimum feature overlap %"),
    min_threat: Optional[float] = Query(None, description="Minimum threat score"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = Query("threat_score", enum=["threat_score", "feature_overlap_pct", "market_size_billion", "company_name"]),
    sort_dir: str = Query("desc", enum=["asc", "desc"]),
    db: Session = Depends(get_db),
):
    """Search and filter fintech launches."""
    query = db.query(FintechLaunch)

    if category:
        query = query.filter(FintechLaunch.category == category)
    if subcategory:
        query = query.filter(FintechLaunch.subcategory == subcategory)
    if threat_level:
        query = query.filter(FintechLaunch.threat_level == threat_level)
    if stage:
        query = query.filter(FintechLaunch.stage == stage)
    if min_overlap is not None:
        query = query.filter(FintechLaunch.feature_overlap_pct >= min_overlap)
    if min_threat is not None:
        query = query.filter(FintechLaunch.threat_score >= min_threat)
    if q:
        pattern = f"%{q}%"
        query = query.filter(or_(
            FintechLaunch.company_name.ilike(pattern),
            FintechLaunch.product_name.ilike(pattern),
            FintechLaunch.description.ilike(pattern),
            FintechLaunch.subcategory.ilike(pattern),
        ))

    # Sorting
    sort_col = getattr(FintechLaunch, sort_by, FintechLaunch.threat_score)
    if sort_dir == "desc":
        query = query.order_by(sort_col.desc().nullslast())
    else:
        query = query.order_by(sort_col.asc().nullsfirst())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "items": [LaunchDetail.model_validate(item).model_dump() for item in items],
    }


@router.get("/launches/{launch_id}")
def get_launch(launch_id: str, db: Session = Depends(get_db)):
    """Get full details of a single competitor."""
    item = db.query(FintechLaunch).filter(FintechLaunch.id == launch_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Launch not found")
    return LaunchDetail.model_validate(item).model_dump()


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """Get all categories with counts."""
    rows = (
        db.query(FintechLaunch.category, func.count(FintechLaunch.id))
        .group_by(FintechLaunch.category)
        .order_by(func.count(FintechLaunch.id).desc())
        .all()
    )
    return [{"category": c, "count": n} for c, n in rows]


@router.get("/subcategories")
def get_subcategories(category: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get subcategories, optionally filtered by category."""
    query = db.query(FintechLaunch.subcategory, func.count(FintechLaunch.id))
    if category:
        query = query.filter(FintechLaunch.category == category)
    rows = query.group_by(FintechLaunch.subcategory).order_by(func.count(FintechLaunch.id).desc()).all()
    return [{"subcategory": s, "count": n} for s, n in rows]


@router.get("/compare")
def compare_competitors(
    ids: str = Query(..., description="Comma-separated IDs to compare"),
    db: Session = Depends(get_db),
):
    """Compare 2-5 competitors side by side."""
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if len(id_list) < 2 or len(id_list) > 5:
        raise HTTPException(status_code=400, detail="Provide 2-5 IDs to compare")
    items = db.query(FintechLaunch).filter(FintechLaunch.id.in_(id_list)).all()
    return [LaunchDetail.model_validate(item).model_dump() for item in items]


@router.get("/threat-matrix")
def threat_matrix(db: Session = Depends(get_db)):
    """Get threat matrix: category x threat level with counts and avg scores."""
    rows = (
        db.query(
            FintechLaunch.category,
            FintechLaunch.threat_level,
            func.count(FintechLaunch.id),
            func.avg(FintechLaunch.threat_score),
            func.avg(FintechLaunch.feature_overlap_pct),
        )
        .group_by(FintechLaunch.category, FintechLaunch.threat_level)
        .all()
    )
    matrix = {}
    for cat, level, count, avg_score, avg_overlap in rows:
        if cat not in matrix:
            matrix[cat] = {}
        matrix[cat][level] = {
            "count": count,
            "avg_threat_score": round(float(avg_score or 0), 1),
            "avg_feature_overlap": round(float(avg_overlap or 0), 1),
        }
    return matrix


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    """Quick statistics."""
    total = db.query(func.count(FintechLaunch.id)).scalar() or 0
    avg_threat = db.query(func.avg(FintechLaunch.threat_score)).scalar() or 0
    avg_overlap = db.query(func.avg(FintechLaunch.feature_overlap_pct)).scalar() or 0
    api_count = db.query(func.count(FintechLaunch.id)).filter(FintechLaunch.api_available.is_(True)).scalar() or 0
    oss_count = db.query(func.count(FintechLaunch.id)).filter(FintechLaunch.open_source.is_(True)).scalar() or 0
    return {
        "total": total,
        "avg_threat_score": round(float(avg_threat), 1),
        "avg_feature_overlap": round(float(avg_overlap), 1),
        "with_api": api_count,
        "open_source": oss_count,
    }
