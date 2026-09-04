"""
PDF Export API — Generate printable reports for portfolios and compliance.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/pdf-export", tags=["pdf-export"])


def _get_user(request: Request, db: Session):
    token = request.cookies.get("access_token", "")
    if not token:
        return None
    try:
        from app.security import decode_token
        payload = decode_token(token)
        if payload:
            return db.query(User).filter(User.id == payload.get("sub")).first()
    except Exception:
        pass
    return None


class PortfolioReportRequest(BaseModel):
    portfolio_id: Optional[str] = None


@router.post("/portfolio", response_class=HTMLResponse)
def export_portfolio_report(
    request: Request,
    data: PortfolioReportRequest,
    db: Session = Depends(get_db),
):
    """Generate a printable portfolio report."""
    from app.services.pdf_export import generate_portfolio_report

    user = _get_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from app.models import Portfolio
    from app.models import DebtInstrument

    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    portfolio_ids = [p.id for p in portfolios]
    instruments = db.query(DebtInstrument).filter(
        DebtInstrument.portfolio_id.in_(portfolio_ids)
    ).all() if portfolio_ids else []

    inst_list = []
    for i in instruments:
        inst_list.append({
            "name": i.name,
            "instrument_type": i.instrument_type,
            "principal_outstanding": float(i.principal_outstanding),
            "currency": i.currency,
            "coupon_rate": float(i.coupon_rate) if i.coupon_rate else 0,
            "maturity_date": str(i.maturity_date) if i.maturity_date else None,
        })

    portfolio_name = "Sovereign Debt Portfolio"
    if data.portfolio_id:
        for p in portfolios:
            if str(p.id) == data.portfolio_id:
                portfolio_name = p.name
                break

    html = generate_portfolio_report(inst_list, portfolio_name)
    return HTMLResponse(content=html)


@router.post("/compliance", response_class=HTMLResponse)
def export_compliance_report(
    request: Request,
    data: PortfolioReportRequest,
    db: Session = Depends(get_db),
):
    """Generate a printable compliance report."""
    from app.services.pdf_export import generate_compliance_report
    from app.services.compliance_checker import check_compliance

    user = _get_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from app.models import Portfolio
    from app.models import DebtInstrument

    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    portfolio_ids = [p.id for p in portfolios]
    instruments = db.query(DebtInstrument).filter(
        DebtInstrument.portfolio_id.in_(portfolio_ids)
    ).all() if portfolio_ids else []

    inst_list = []
    for i in instruments:
        inst_list.append({
            "name": i.name,
            "instrument_type": i.instrument_type,
            "principal_outstanding": float(i.principal_outstanding),
            "currency": i.currency,
            "coupon_rate": float(i.coupon_rate) if i.coupon_rate else 0,
            "maturity_date": str(i.maturity_date) if i.maturity_date else None,
            "is_callable": getattr(i, "is_callable", False),
        })

    compliance_result = check_compliance(inst_list)
    html = generate_compliance_report(compliance_result)
    return HTMLResponse(content=html)
