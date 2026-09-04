"""
FX Hedging Recommendation API

Analyzes currency exposure and recommends hedging strategies:
- Identifies unhedged foreign currency debt
- Recommends hedging instruments (forwards, options, swaps)
- Estimates hedge costs and risk reduction
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/fx-hedging", tags=["fx-hedging"])


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


class FXHedgingRequest(BaseModel):
    target_hedge_ratio: float = 0.70
    fx_rates: Optional[dict] = None


@router.post("/analyze")
def analyze_fx_exposure(request: Request, data: FXHedgingRequest, db: Session = Depends(get_db)):
    """Analyze FX exposure and recommend hedging."""
    from app.services.fx_hedging import analyze_fx_exposure

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

    if not instruments:
        return {"error": "No instruments found"}

    inst_list = []
    for i in instruments:
        inst_list.append({
            "name": i.name,
            "instrument_type": i.instrument_type,
            "principal_outstanding": float(i.principal_outstanding),
            "currency": i.currency,
            "coupon_rate": float(i.coupon_rate) if i.coupon_rate else 0,
        })


    # Try to get live FX rates first
    fx_rates = data.fx_rates
    if not fx_rates:
        try:
            from app.api.realtime import _fetch_ecb_rates
            ecb = _fetch_ecb_rates()
            if ecb:
                fx_rates = ecb
        except Exception:
            pass

    result = analyze_fx_exposure(
        instruments=inst_list,
        fx_rates=fx_rates,
        target_hedge_ratio=data.target_hedge_ratio,
    )

    result["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    result["target_hedge_ratio"] = data.target_hedge_ratio

    return result


@router.get("/scenarios")
def hedging_scenarios(request: Request, db: Session = Depends(get_db)):
    """Run hedging analysis at different target ratios."""
    from app.services.fx_hedging import analyze_fx_exposure

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

    if not instruments:
        return {"error": "No instruments found"}

    inst_list = []
    for i in instruments:
        inst_list.append({
            "name": i.name,
            "instrument_type": i.instrument_type,
            "principal_outstanding": float(i.principal_outstanding),
            "currency": i.currency,
            "coupon_rate": float(i.coupon_rate) if i.coupon_rate else 0,
        })

    scenarios = {}
    for ratio in [0.30, 0.50, 0.70, 0.90]:
        result = analyze_fx_exposure(
            instruments=inst_list,
            target_hedge_ratio=ratio,
        )
        if "error" not in result:
            scenarios[f"{int(ratio*100)}%"] = {
                "target_ratio": ratio,
                "fx_risk_score": result.get("fx_risk_score", 0),
                "total_annual_cost": result.get("hedging_summary", {}).get("total_annual_hedge_cost", 0),
                "cost_pct": result.get("hedging_summary", {}).get("cost_as_pct_of_portfolio", 0),
                "currencies_to_hedge": result.get("hedging_summary", {}).get("currencies_to_hedge", 0),
            }

    return {
        "scenarios": scenarios,
        "base_currency": result.get("base_currency", "USD"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
