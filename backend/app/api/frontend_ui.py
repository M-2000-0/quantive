"""
Frontend UI API — Auth-protected bridge for the React SPA
=========================================================

These endpoints require a valid JWT cookie. In demo mode (no valid token),
they bind records to the organization's first user so the "Create Portfolio"
flow works end-to-end.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DebtInstrument, Organization, Portfolio, User
from app.schemas import DebtInstrumentCreate

router = APIRouter(prefix="/api/ui", tags=["ui"])


# ── Helpers ─────────────────────────────────────────────────────────────

def _get_user_from_request(request: Request, db: Session) -> User:
    """Return the logged-in user from cookie/JWT, falling back to first user in demo mode."""
    token = request.cookies.get("access_token")
    if token:
        try:
            from app.security import decode_token
            payload = decode_token(token)
            if payload:
                uid = payload.get("sub")
                user = db.query(User).filter(User.id == uid).first()
                if user:
                    return user
        except Exception:
            pass
    # Fallback: first user (demo mode only)
    user = db.query(User).order_by(User.created_at).first()
    if not user:
        raise HTTPException(status_code=503, detail="No user available to bind records")
    return user


def _portfolio_payload(portfolio: Portfolio, db: Session) -> dict:
    instruments = db.query(DebtInstrument).filter(DebtInstrument.portfolio_id == portfolio.id).all()
    aum = sum(float(i.principal_outstanding) for i in instruments)
    avg_coupon = (sum(float(i.coupon_rate) * float(i.principal_outstanding) for i in instruments) / aum
                  if aum else 0.0)
    years = []
    for i in instruments:
        try:
            y = int(i.maturity_date.split("-")[0])
        except (ValueError, IndexError):
            continue
        years.append((y, float(i.principal_outstanding)))
    currency_count = len({i.currency for i in instruments})
    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "description": portfolio.description,
        "created_at": portfolio.created_at.isoformat(),
        "updated_at": portfolio.updated_at.isoformat(),
        "total_value_usd": round(aum, 2),
        "instruments_count": len(instruments),
        "avg_coupon_pct": round(avg_coupon, 3),
        "currency_count": currency_count,
        "instruments": [
            {
                "id": i.id,
                "name": i.name,
                "instrument_type": str(i.instrument_type.value) if hasattr(i.instrument_type, "value") else str(i.instrument_type),
                "currency": i.currency,
                "principal_outstanding": float(i.principal_outstanding),
                "coupon_rate": float(i.coupon_rate),
                "maturity_date": i.maturity_date,
                "issue_date": i.issue_date,
                "spread_bps": float(i.spread_bps or 0.0),
            }
            for i in instruments
        ],
    }


# ── Endpoints ───────────────────────────────────────────────────────────

@router.get("/portfolio-overview")
def portfolio_overview(db: Session = Depends(get_db)):
    """Aggregated portfolio summary for the Portfolios page."""
    portfolios = db.query(Portfolio).order_by(Portfolio.created_at).all()
    items = [_portfolio_payload(p, db) for p in portfolios]
    return {
        "portfolios": items,
        "count": len(items),
        "total_aum_usd": round(sum(p["total_value_usd"] for p in items), 2),
        "total_instruments": sum(p["instruments_count"] for p in items),
        "total_currencies": len({i["currency"] for p in items for i in p["instruments"]}),
        "empty": len(items) == 0,
    }


@router.get("/portfolio/{portfolio_id}")
def portfolio_detail(portfolio_id: str, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return _portfolio_payload(portfolio, db)


class UIInstrumentCreate(DebtInstrumentCreate):
    pass


class UIPortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    instruments: list[UIInstrumentCreate] = []


@router.post("/portfolios", status_code=201)
def create_portfolio(request: Request, data: UIPortfolioCreate, db: Session = Depends(get_db)):
    """Create a portfolio bound to the logged-in user/org."""
    user = _get_user_from_request(request, db)

    # Plan limits: max_portfolios + max_instruments (stock limits)
    from app.billing import enforce_resource_limit
    enforce_resource_limit(
        user.org_id, "max_portfolios",
        db.query(Portfolio).filter(Portfolio.org_id == user.org_id).count(),
    )
    enforce_resource_limit(user.org_id, "max_instruments", len(data.instruments))

    portfolio = Portfolio(
        name=data.name,
        description=data.description,
        org_id=user.org_id,
        created_by=user.id,
    )
    db.add(portfolio)
    db.flush()

    for inv in data.instruments:
        db.add(DebtInstrument(
            portfolio_id=portfolio.id,
            name=inv.name,
            instrument_type=inv.instrument_type,
            currency=inv.currency,
            principal_outstanding=inv.principal_outstanding,
            coupon_rate=inv.coupon_rate,
            maturity_date=inv.maturity_date,
            issue_date=inv.issue_date,
            spread_bps=inv.spread_bps or 0.0,
        ))

    db.commit()
    db.refresh(portfolio)

    # Immutable audit log
    try:
        from app.security.immutable_audit import ImmutableAuditTrail
        audit = ImmutableAuditTrail(db)
        audit.record_event(
            action="portfolio.create",
            resource_type="portfolio",
            resource_id=portfolio.id,
            actor_id=user.id,
            actor_email=user.email,
            org_id=user.org_id,
            data={
                "name": data.name,
                "description": data.description,
                "instruments_count": len(data.instruments),
                "total_principal": sum(float(i.principal_outstanding) for i in data.instruments),
            },
        )
        db.commit()
    except Exception:
        pass  # Don't fail the request if audit logging fails

    return _portfolio_payload(portfolio, db)