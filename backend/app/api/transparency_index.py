"""Sovereign Debt Transparency Index API endpoints.

Exposes country rankings, scores, and methodology to position Quantive
as a thought leader in sovereign debt transparency.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.transparency_index import (
    IndexHistory,
    IndexMethodology,
    CountryTier,
    SovereignDebtIndex,
)
from app.security import get_current_user

router = APIRouter(prefix="/api/transparency-index", tags=["transparency-index"])


@router.get("/rankings")
def get_rankings(
    region: str | None = None,
    income_group: str | None = None,
    tier: CountryTier | None = None,
    sort_by: str = Query("overall_score", pattern="^(overall_score|rank|country_name)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get country rankings with optional filters."""
    query = db.query(SovereignDebtIndex)

    if region:
        query = query.filter(SovereignDebtIndex.region == region)
    if income_group:
        query = query.filter(SovereignDebtIndex.income_group == income_group)
    if tier:
        query = query.filter(SovereignDebtIndex.tier == tier)

    # Sort
    sort_col = getattr(SovereignDebtIndex, sort_by)
    if order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    total = query.count()
    results = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "rankings": [_format_ranking(r) for r in results],
    }


@router.get("/country/{country_code}")
def get_country_detail(
    country_code: str,
    db: Session = Depends(get_db),
):
    """Get detailed scores for a specific country."""
    country = db.query(SovereignDebtIndex).filter(
        SovereignDebtIndex.country_code == country_code.upper()
    ).first()

    if not country:
        raise HTTPException(404, f"Country {country_code} not found")

    # Get historical trend
    history = db.query(IndexHistory).filter(
        IndexHistory.country_code == country_code.upper()
    ).order_by(IndexHistory.assessment_date.desc()).limit(10).all()

    return {
        "country": _format_country_detail(country),
        "history": [_format_history(h) for h in history],
    }


@router.get("/compare")
def compare_countries(
    country_codes: str = Query(..., description="Comma-separated country codes"),
    db: Session = Depends(get_db),
):
    """Compare multiple countries side-by-side."""
    codes = [c.strip().upper() for c in country_codes.split(",")]
    if len(codes) < 2 or len(codes) > 5:
        raise HTTPException(400, "Provide 2-5 country codes to compare")

    countries = db.query(SovereignDebtIndex).filter(
        SovereignDebtIndex.country_code.in_(codes)
    ).all()

    if len(countries) != len(codes):
        found = {c.country_code for c in countries}
        missing = set(codes) - found
        raise HTTPException(404, f"Countries not found: {', '.join(missing)}")

    return {
        "countries": [_format_country_detail(c) for c in countries],
        "comparison": _build_comparison(countries),
    }


@router.get("/global-stats")
def get_global_stats(
    db: Session = Depends(get_db),
):
    """Get global statistics and aggregates."""
    all_countries = db.query(SovereignDebtIndex).all()

    scores = [c.overall_score for c in all_countries]
    tier_counts = {}
    for c in all_countries:
        tier = c.tier.value if hasattr(c.tier, 'value') else str(c.tier)
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    region_scores = {}
    for c in all_countries:
        if c.region not in region_scores:
            region_scores[c.region] = []
        region_scores[c.region].append(c.overall_score)

    income_scores = {}
    for c in all_countries:
        if c.income_group not in income_scores:
            income_scores[c.income_group] = []
        income_scores[c.income_group].append(c.overall_score)

    return {
        "total_countries": len(all_countries),
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "median_score": round(sorted(scores)[len(scores) // 2], 1) if scores else 0,
        "highest_score": round(max(scores), 1) if scores else 0,
        "lowest_score": round(min(scores), 1) if scores else 0,
        "tier_distribution": tier_counts,
        "regional_averages": {
            r: round(sum(s) / len(s), 1) for r, s in region_scores.items()
        },
        "income_group_averages": {
            g: round(sum(s) / len(s), 1) for g, s in income_scores.items()
        },
    }


@router.get("/methodology")
def get_methodology(
    db: Session = Depends(get_db),
):
    """Get the current methodology documentation."""
    methodology = db.query(IndexMethodology).filter(
        IndexMethodology.is_current == True
    ).order_by(IndexMethodology.created_at.desc()).first()

    if not methodology:
        # Return default methodology
        return {
            "version": "1.0",
            "title": "Sovereign Debt Transparency Index Methodology",
            "description": "A comprehensive framework for evaluating sovereign debt management transparency.",
            "category_weights": {
                "disclosure": 0.20,
                "data_access": 0.15,
                "institutional": 0.15,
                "reporting_freq": 0.12,
                "audit_trail": 0.12,
                "digital_infra": 0.10,
                "compliance": 0.10,
                "stakeholder": 0.06,
            },
            "categories": [
                {"name": "disclosure", "label": "Public Disclosure", "weight": 0.20,
                 "description": "Quality and completeness of public debt reporting"},
                {"name": "data_access", "label": "Data Accessibility", "weight": 0.15,
                 "description": "Availability of debt data in machine-readable formats"},
                {"name": "institutional", "label": "Institutional Framework", "weight": 0.15,
                 "description": "DMO independence, capacity, and governance"},
                {"name": "reporting_freq", "label": "Reporting Frequency", "weight": 0.12,
                 "description": "Timeliness and frequency of debt publications"},
                {"name": "audit_trail", "label": "Audit & Oversight", "weight": 0.12,
                 "description": "External audit and internal control mechanisms"},
                {"name": "digital_infra", "label": "Digital Infrastructure", "weight": 0.10,
                 "description": "Modern debt management systems and cybersecurity"},
                {"name": "compliance", "label": "Standards Compliance", "weight": 0.10,
                 "description": "Adherence to IMF/World Bank standards"},
                {"name": "stakeholder", "label": "Stakeholder Engagement", "weight": 0.06,
                 "description": "Parliamentary and public engagement on debt"},
            ],
        }

    return {
        "version": methodology.version,
        "title": methodology.title,
        "description": methodology.description,
        "category_weights": methodology.category_weights,
        "scoring_criteria": methodology.scoring_criteria,
        "data_sources": methodology.data_sources,
    }


@router.get("/trend/{country_code}")
def get_country_trend(
    country_code: str,
    years: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Get historical trend for a country's scores."""
    history = db.query(IndexHistory).filter(
        IndexHistory.country_code == country_code.upper()
    ).order_by(IndexHistory.assessment_date.desc()).limit(years).all()

    if not history:
        raise HTTPException(404, f"No historical data for {country_code}")

    return {
        "country_code": country_code.upper(),
        "trend": [_format_history(h) for h in reversed(history)],
    }


@router.get("/regions")
def get_regions(db: Session = Depends(get_db)):
    """Get list of regions with country counts."""
    regions = db.query(
        SovereignDebtIndex.region,
        func.count(SovereignDebtIndex.id)
    ).group_by(SovereignDebtIndex.region).all()

    return {
        "regions": [{"name": r, "count": c} for r, c in regions]
    }


@router.get("/improvers")
def get_top_improvers(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get countries with highest score improvement over last assessment period."""
    # Get countries with at least 2 historical records
    countries_with_history = db.query(
        SovereignDebtIndex.country_code,
        SovereignDebtIndex.country_name,
        SovereignDebtIndex.overall_score,
    ).all()

    improvements = []
    for code, name, current_score in countries_with_history:
        prev = db.query(IndexHistory).filter(
            IndexHistory.country_code == code
        ).order_by(IndexHistory.assessment_date.desc()).first()

        if prev:
            improvement = current_score - prev.overall_score
            improvements.append({
                "country_code": code,
                "country_name": name,
                "current_score": current_score,
                "previous_score": prev.overall_score,
                "improvement": round(improvement, 1),
            })

    improvements.sort(key=lambda x: x["improvement"], reverse=True)
    return {"improvers": improvements[:limit]}


# ── Helper serializers ──────────────────────────────────────────────

def _format_ranking(country: SovereignDebtIndex) -> dict:
    tier = country.tier.value if hasattr(country.tier, 'value') else str(country.tier)
    return {
        "rank": country.rank,
        "country_code": country.country_code,
        "country_name": country.country_name,
        "region": country.region,
        "income_group": country.income_group,
        "overall_score": country.overall_score,
        "tier": tier,
        "category_scores": {
            "disclosure": country.disclosure_score,
            "data_access": country.data_access_score,
            "institutional": country.institutional_score,
            "reporting_freq": country.reporting_freq_score,
            "audit_trail": country.audit_trail_score,
            "digital_infra": country.digital_infra_score,
            "compliance": country.compliance_score,
            "stakeholder": country.stakeholder_score,
        },
    }


def _format_country_detail(country: SovereignDebtIndex) -> dict:
    tier = country.tier.value if hasattr(country.tier, 'value') else str(country.tier)
    return {
        "rank": country.rank,
        "country_code": country.country_code,
        "country_name": country.country_name,
        "region": country.region,
        "income_group": country.income_group,
        "overall_score": country.overall_score,
        "tier": tier,
        "category_scores": {
            "disclosure": country.disclosure_score,
            "data_access": country.data_access_score,
            "institutional": country.institutional_score,
            "reporting_freq": country.reporting_freq_score,
            "audit_trail": country.audit_trail_score,
            "digital_infra": country.digital_infra_score,
            "compliance": country.compliance_score,
            "stakeholder": country.stakeholder_score,
        },
        "strengths": country.strengths,
        "weaknesses": country.weaknesses,
        "recommendations": country.recommendations,
        "data_sources": country.data_sources,
        "methodology_version": country.methodology_version,
        "assessment_date": country.assessment_date.isoformat() if country.assessment_date else None,
        "next_assessment": country.next_assessment.isoformat() if country.next_assessment else None,
    }


def _format_history(history: IndexHistory) -> dict:
    tier = history.tier.value if hasattr(history.tier, 'value') else str(history.tier)
    return {
        "date": history.assessment_date.isoformat(),
        "overall_score": history.overall_score,
        "tier": tier,
        "rank": history.rank,
        "category_scores": history.category_scores,
    }


def _build_comparison(countries: list) -> dict:
    """Build comparison analysis between countries."""
    if len(countries) < 2:
        return {}

    best = max(countries, key=lambda c: c.overall_score)
    worst = min(countries, key=lambda c: c.overall_score)

    categories = [
        "disclosure_score", "data_access_score", "institutional_score",
        "reporting_freq_score", "audit_trail_score", "digital_infra_score",
        "compliance_score", "stakeholder_score",
    ]

    category_leaders = {}
    for cat in categories:
        best_country = max(countries, key=lambda c: getattr(c, cat))
        category_leaders[cat.replace("_score", "")] = {
            "leader": best_country.country_name,
            "score": getattr(best_country, cat),
        }

    return {
        "overall_leader": {
            "country_code": best.country_code,
            "country_name": best.country_name,
            "score": best.overall_score,
        },
        "largest_gap": {
            "between": f"{best.country_name} vs {worst.country_name}",
            "gap": round(best.overall_score - worst.overall_score, 1),
        },
        "category_leaders": category_leaders,
    }
