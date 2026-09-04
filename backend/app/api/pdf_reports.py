"""PDF report generation API endpoints."""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BenchmarkResult, OptimizationJob, Portfolio, Strategy, User
from app.pdf_report import (
    generate_optimization_pdf,
    generate_portfolio_pdf,
    generate_risk_pdf,
    get_pdf_content_type,
)
from app.risk_probabilities import get_risk_summary
from app.security import get_current_user

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/portfolio/{portfolio_id}.pdf")
def portfolio_pdf(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate PDF report for a portfolio."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    instruments_data = [
        {
            "name": inst.name,
            "instrument_type": inst.instrument_type.value if hasattr(inst.instrument_type, "value") else inst.instrument_type,
            "currency": inst.currency,
            "principal_outstanding": inst.principal_outstanding,
            "coupon_rate": inst.coupon_rate,
            "maturity_date": inst.maturity_date,
            "issue_date": inst.issue_date,
            "spread_bps": inst.spread_bps,
            "is_callable": inst.is_callable,
            "call_date": inst.call_date,
            "call_price": inst.call_price,
        }
        for inst in portfolio.instruments
    ]

    analytics = None
    try:
        from app.analytics import _portfolio_to_quantive
        from quantive.analytics import portfolio_analytics
        qp = _portfolio_to_quantive(portfolio)
        analytics = portfolio_analytics(qp)
    except Exception:
        pass

    pdf_data = generate_portfolio_pdf(
        {"name": portfolio.name, "description": portfolio.description or ""},
        instruments_data,
        analytics,
    )

    content_type = get_pdf_content_type(pdf_data)
    ext = "pdf" if content_type == "application/pdf" else "html"

    return Response(
        content=pdf_data,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="portfolio-{portfolio.name.replace(" ", "_")}.{ext}"'
        },
    )


@router.get("/optimization/{job_id}.pdf")
def optimization_pdf(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate PDF report for optimization results."""
    job = db.query(OptimizationJob).filter(
        OptimizationJob.id == job_id, OptimizationJob.org_id == user.org_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Optimization not found")

    strategies = db.query(Strategy).filter(Strategy.job_id == job_id).order_by(Strategy.rank).all()
    benchmarks = db.query(BenchmarkResult).filter(BenchmarkResult.job_id == job_id).all()

    job_data = {
        "name": job.name,
        "status": job.status.value if hasattr(job.status, "value") else job.status,
    }

    strat_data = [
        {
            "rank": s.rank,
            "name": s.name,
            "description": s.description,
            "metrics": s.metrics,
            "feasible": s.metrics.get("feasible", True) if isinstance(s.metrics, dict) else True,
        }
        for s in strategies
    ]

    bench_data = [
        {
            "solver_name": b.solver_name,
            "feasible": b.feasible,
            "objective_value": b.objective_value,
            "execution_time_seconds": b.execution_time_seconds,
            "iterations": b.iterations,
            "metrics": b.metrics,
        }
        for b in benchmarks
    ]

    pdf_data = generate_optimization_pdf(job_data, strat_data, bench_data)
    content_type = get_pdf_content_type(pdf_data)
    ext = "pdf" if content_type == "application/pdf" else "html"

    return Response(
        content=pdf_data,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="optimization-{job.name.replace(" ", "_")}.{ext}"'
        },
    )


@router.get("/risk/{portfolio_id}.pdf")
def risk_pdf(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate PDF risk report for a portfolio."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    instruments_data = [
        {
            "name": inst.name,
            "instrument_type": inst.instrument_type.value if hasattr(inst.instrument_type, "value") else inst.instrument_type,
            "currency": inst.currency,
            "principal_outstanding": inst.principal_outstanding,
            "coupon_rate": inst.coupon_rate,
            "maturity_date": inst.maturity_date,
            "spread_bps": inst.spread_bps,
        }
        for inst in portfolio.instruments
    ]

    portfolio_value = sum(i.get("principal_outstanding", 0) for i in instruments_data)
    risk_data = get_risk_summary(portfolio_value, instruments_data)

    pdf_data = generate_risk_pdf(portfolio.name, risk_data)
    content_type = get_pdf_content_type(pdf_data)
    ext = "pdf" if content_type == "application/pdf" else "html"

    return Response(
        content=pdf_data,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="risk-{portfolio.name.replace(" ", "_")}.{ext}"'
        },
    )
