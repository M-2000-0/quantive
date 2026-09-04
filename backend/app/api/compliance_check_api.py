"""
Regulatory Compliance Auto-Check API

Validates portfolios against fiscal rules:
- Debt-to-GDP limits
- Floating rate exposure
- Currency concentration
- Maturity walls
- Short-term debt ratios
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/compliance-check", tags=["compliance-check"])


def _get_user_from_request(request: Request, db: Session):
    """Get user from access_token cookie."""
    token = request.cookies.get("access_token", "")
    if not token:
        return None
    try:
        from app.security import decode_token
        payload = decode_token(token)
        if payload:
            uid = payload.get("sub")
            return db.query(User).filter(User.id == uid).first()
    except Exception:
        pass
    return None


class ComplianceCheckRequest(BaseModel):
    portfolio_id: Optional[str] = None
    fiscal_rules: Optional[dict] = None
    macro_data: Optional[dict] = None


@router.post("/run")
def run_compliance_check(request: Request, data: ComplianceCheckRequest, db: Session = Depends(get_db)):
    """Run compliance check on a portfolio."""
    from app.services.compliance_checker import check_compliance

    user = _get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Load instruments from database via portfolios (match rebalancing pattern: org_id)
    from app.models import Portfolio
    from app.models import DebtInstrument
    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    portfolio_ids = [p.id for p in portfolios]
    instruments = db.query(DebtInstrument).filter(
        DebtInstrument.portfolio_id.in_(portfolio_ids)
    ).all() if portfolio_ids else []

    if not instruments:
        return {"compliant": True, "checks": [], "message": "No instruments to check"}

    # Convert to dicts
    inst_list = []
    for i in instruments:
        inst_list.append({
            "name": i.name,
            "instrument_type": i.instrument_type,
            "principal_outstanding": float(i.principal_outstanding),
            "currency": i.currency,
            "coupon_rate": float(i.coupon_rate) if i.coupon_rate else 0,
            "maturity_date": str(i.maturity_date) if i.maturity_date else None,
            "issue_date": str(i.issue_date) if i.issue_date else None,
            "is_callable": getattr(i, "is_callable", False),
        })

    result = check_compliance(
        instruments=inst_list,
        fiscal_rules=data.fiscal_rules,
        macro_data=data.macro_data,
    )

    # Add metadata
    result["portfolio_id"] = data.portfolio_id
    result["checked_at"] = datetime.now(timezone.utc).isoformat()
    result["instrument_count"] = len(inst_list)

    return result


@router.get("/rules")
def get_default_rules(request: Request):
    """Get default fiscal rules."""
    from app.services.compliance_checker import DEFAULT_FISCAL_RULES
    return {
        "rules": DEFAULT_FISCAL_RULES,
        "description": "Default fiscal rules for compliance checking",
        "adjustable": True,
    }


@router.post("/check-custom")
def check_custom_rules(request: Request, data: ComplianceCheckRequest, db: Session = Depends(get_db)):
    """Run compliance check with custom rules only."""
    from app.services.compliance_checker import check_compliance

    user = _get_user_from_request(request, db)
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

    result = check_compliance(
        instruments=inst_list,
        fiscal_rules=data.fiscal_rules,
        macro_data=data.macro_data,
    )

    result["checked_at"] = datetime.now(timezone.utc).isoformat()
    return result
