"""
Market Intelligence API
=======================

CRUD, search, filter, and stats for the 50-industry x 20-subcategory
taxonomy of 3,000-5,000 upcoming product launches.
"""

import csv
import io
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.market_intelligence import MarketLaunch

router = APIRouter(prefix="/api/market-intelligence", tags=["market-intelligence"])


# ── Response Schemas ────────────────────────────────────────────────

class LaunchItem(BaseModel):
    id: str
    industry: str
    subcategory: str
    name: str
    company: str
    description: str
    target_market: str
    status: str
    estimated_launch: str
    market_size_billion: Optional[float] = None
    competitive_advantage: Optional[str] = None
    confidence: str = "medium"

    class Config:
        from_attributes = True


class IndustryStats(BaseModel):
    industry: str
    subcategory_count: int
    launch_count: int
    statuses: dict[str, int]


class IntelligenceSummary(BaseModel):
    total_launches: int
    total_industries: int
    total_subcategories: int
    status_distribution: dict[str, int]
    top_industries: list[IndustryStats]


# ── Endpoints ───────────────────────────────────────────────────────

@router.get("/summary", response_model=IntelligenceSummary)
def get_summary(db: Session = Depends(get_db)):
    """Get overall statistics of the market intelligence database."""
    total = db.query(func.count(MarketLaunch.id)).scalar() or 0
    industries = db.query(func.count(func.distinct(MarketLaunch.industry))).scalar() or 0
    subcategories = db.query(func.count(func.distinct(MarketLaunch.subcategory))).scalar() or 0

    # Status distribution
    status_rows = (
        db.query(MarketLaunch.status, func.count(MarketLaunch.id))
        .group_by(MarketLaunch.status)
        .all()
    )
    status_dist = {s: c for s, c in status_rows}

    # Top industries
    industry_rows = (
        db.query(
            MarketLaunch.industry,
            func.count(func.distinct(MarketLaunch.subcategory)).label("sub_count"),
            func.count(MarketLaunch.id).label("launch_count"),
        )
        .group_by(MarketLaunch.industry)
        .order_by(func.count(MarketLaunch.id).desc())
        .limit(20)
        .all()
    )
    top_industries = []
    for ind, sub_count, launch_count in industry_rows:
        ind_statuses = (
            db.query(MarketLaunch.status, func.count(MarketLaunch.id))
            .filter(MarketLaunch.industry == ind)
            .group_by(MarketLaunch.status)
            .all()
        )
        top_industries.append(IndustryStats(
            industry=ind,
            subcategory_count=sub_count,
            launch_count=launch_count,
            statuses={s: c for s, c in ind_statuses},
        ))

    return IntelligenceSummary(
        total_launches=total,
        total_industries=industries,
        total_subcategories=subcategories,
        status_distribution=status_dist,
        top_industries=top_industries,
    )


@router.get("/industries")
def get_industries(db: Session = Depends(get_db)):
    """Get list of all industries with their subcategories."""
    rows = (
        db.query(MarketLaunch.industry, MarketLaunch.subcategory, func.count(MarketLaunch.id))
        .group_by(MarketLaunch.industry, MarketLaunch.subcategory)
        .order_by(MarketLaunch.industry, MarketLaunch.subcategory)
        .all()
    )
    result = {}
    for industry, subcategory, count in rows:
        if industry not in result:
            result[industry] = []
        result[industry].append({"subcategory": subcategory, "count": count})
    return result


@router.get("/launches")
def search_launches(
    industry: Optional[str] = Query(None),
    subcategory: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Full-text search across name, company, description"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Search and filter launches with pagination."""
    query = db.query(MarketLaunch)

    if industry:
        query = query.filter(MarketLaunch.industry == industry)
    if subcategory:
        query = query.filter(MarketLaunch.subcategory == subcategory)
    if status:
        query = query.filter(MarketLaunch.status == status)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                MarketLaunch.name.ilike(pattern),
                MarketLaunch.company.ilike(pattern),
                MarketLaunch.description.ilike(pattern),
                MarketLaunch.target_market.ilike(pattern),
            )
        )

    total = query.count()
    items = (
        query.order_by(MarketLaunch.industry, MarketLaunch.subcategory, MarketLaunch.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "items": [LaunchItem.model_validate(item).model_dump() for item in items],
    }


@router.get("/launches/{launch_id}")
def get_launch(launch_id: str, db: Session = Depends(get_db)):
    """Get a single launch item by ID."""
    item = db.query(MarketLaunch).filter(MarketLaunch.id == launch_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Launch not found")
    return LaunchItem.model_validate(item).model_dump()


@router.get("/status-options")
def get_status_options():
    """Get all available launch statuses with descriptions."""
    return {
        "rumored": "Unconfirmed reports of development",
        "announced": "Officially announced by company",
        "in_development": "Actively being built",
        "beta": "In beta testing phase",
        "pilot": "Running pilot programs",
        "awaiting_funding": "Seeking investment to proceed",
        "in_production": "Manufacturing/deployment started",
        "soon": "Launching within 30 days",
        "delayed": "Launch date pushed back",
        "cancelled": "Development halted",
    }


@router.get("/stats/by-status")
def stats_by_status(db: Session = Depends(get_db)):
    """Launch count grouped by status."""
    rows = (
        db.query(MarketLaunch.status, func.count(MarketLaunch.id))
        .group_by(MarketLaunch.status)
        .order_by(func.count(MarketLaunch.id).desc())
        .all()
    )
    return [{"status": s, "count": c} for s, c in rows]


@router.get("/export")
def export_csv(
    industry: Optional[str] = Query(None),
    subcategory: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Export filtered launches as CSV download."""
    query = db.query(MarketLaunch)

    if industry:
        query = query.filter(MarketLaunch.industry == industry)
    if subcategory:
        query = query.filter(MarketLaunch.subcategory == subcategory)
    if status:
        query = query.filter(MarketLaunch.status == status)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                MarketLaunch.name.ilike(pattern),
                MarketLaunch.company.ilike(pattern),
                MarketLaunch.description.ilike(pattern),
                MarketLaunch.target_market.ilike(pattern),
            )
        )

    items = query.order_by(MarketLaunch.industry, MarketLaunch.subcategory, MarketLaunch.name).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Industry", "Subcategory", "Name", "Company", "Description",
        "Target Market", "Status", "Estimated Launch", "Market Size (B)",
        "Competitive Advantage", "Risk Factors", "Confidence",
    ])
    for item in items:
        writer.writerow([
            item.id, item.industry, item.subcategory, item.name, item.company,
            item.description, item.target_market, item.status, item.estimated_launch,
            item.market_size_billion or "", item.competitive_advantage or "",
            item.risk_factors or "", item.confidence,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=market-intelligence-export.csv"},
    )
