"""Excel export API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.excel_export import export_optimization_excel, export_portfolio_excel, export_risk_excel
from app.models import BenchmarkResult, OptimizationJob, Portfolio, Strategy, User
from app.security import get_current_user

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.get("/portfolio/{portfolio_id}.xlsx")
def export_portfolio(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export portfolio instruments to Excel."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    portfolio_data = {
        "name": portfolio.name,
        "description": portfolio.description or "",
        "instruments": [
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
        ],
    }

    output = export_portfolio_excel(portfolio_data)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="portfolio-{portfolio.name.replace(" ", "_")}.xlsx"'
        },
    )


@router.get("/optimization/{job_id}.xlsx")
def export_optimization(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export optimization results to Excel."""
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
        "optimization_type": job.optimization_type.value if hasattr(job.optimization_type, "value") else job.optimization_type,
        "random_seed": job.random_seed,
        "created_at": job.created_at.isoformat() if job.created_at else "",
        "completed_at": job.completed_at.isoformat() if job.completed_at else "N/A",
    }

    strat_data = [
        {
            "rank": s.rank,
            "name": s.name,
            "description": s.description,
            "metrics": s.metrics,
            "stress_test_results": s.stress_test_results,
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

    output = export_optimization_excel(job_data, strat_data, bench_data)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="optimization-{job.name.replace(" ", "_")}.xlsx"'
        },
    )


@router.get("/risk/{portfolio_id}.xlsx")
def export_risk_report(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export risk analysis to Excel."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from app.risk_probabilities import get_risk_summary

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

    output = export_risk_excel(risk_data)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="risk-report-{portfolio.name.replace(" ", "_")}.xlsx"'
        },
    )
