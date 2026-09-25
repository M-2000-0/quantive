"""What-if panel API — deterministic scenario visualization data.

Serves the same first-order shock math the AI advisor uses
(app.ai.portfolio_context.compute_rate_shock) so the dashboard panel and
the chat answers always agree, computed live from the caller's own
portfolio. Org-scoped like every other dashboard endpoint.
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/whatif", tags=["what-if"])

# Ladder served to the dashboard panel (matches the demo script appendix).
DEFAULT_BPS_LADDER = [25, 50, 100, 200]


@router.get("/scenarios")
def get_scenarios(
    bps: Optional[str] = Query(default=None, description="Comma-separated bps values (default 25,50,100,200)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Rate-shock ladder for the caller's portfolio, base case first.

    Each rung carries the first-order interest delta and mark-to-market
    impact the AI advisor quotes; `currency_exposures` is included so the
    panel can later compose FX shocks the same way the chat does.
    """
    from app.ai.portfolio_context import (
        build_portfolio_snapshot,
        compute_fx_impact,
        compute_rate_shock,
    )

    rungs: list[dict[str, Any]] = []
    if bps:
        try:
            ladder = sorted({float(x) for x in bps.split(",") if x.strip()})
        except ValueError:
            ladder = []
        ladder = ladder[:8] or list(DEFAULT_BPS_LADDER)
    else:
        ladder = list(DEFAULT_BPS_LADDER)

    try:
        snap = build_portfolio_snapshot(user, db)
    except Exception:
        snap = None

    if not snap:
        return {
            "scenarios": [],
            "base": None,
            "currency_exposures": {},
            "note": "No portfolio data yet — run the demo seeder or add instruments.",
        }

    base_interest = float(snap["annual_interest"])
    total = float(snap["total_principal"])

    rungs.append({
        "label": "Base (today)",
        "bps": 0.0,
        "annual_interest": round(base_interest, 2),
        "interest_delta": 0.0,
        "mtm_impact": 0.0,
    })
    for bps_value in ladder:
        s = compute_rate_shock(snap, float(bps_value))
        rungs.append({
            "label": f"Rates +{bps_value:g}bps",
            "bps": float(bps_value),
            "annual_interest": round(base_interest + s["annual_interest_delta"], 2),
            "interest_delta": round(s["annual_interest_delta"], 2),
            "mtm_impact": round(s["mtm_impact"], 2),
        })

    fx = {c: round(v, 2) for c, v in (snap.get("currency_exposures_usd") or {}).items()}
    fx_note = None
    if fx:
        parts = [f"{c} {_fmt_m(v)}" for c, v in sorted(fx.items(), key=lambda kv: -kv[1])]
        fx_note = "Face-value exposure by currency: " + ", ".join(parts)

    return {
        "scenarios": rungs,
        "base": {
            "total_principal": round(total, 2),
            "weighted_coupon_pct": float(snap["wtd_coupon_pct"]),
            "annual_interest": round(base_interest, 2),
            "wtd_maturity_years": float(snap["wtd_maturity_years"]),
            "instrument_count": int(snap["instrument_count"]),
            "repricing_share_pct": round(
                min(
                    1.0,
                    max(
                        float(snap.get("floating_principal", 0.0)),
                        sum(
                            m["principal"]
                            for m in (snap.get("nearest_maturities") or [])
                            if m["years_left"] <= 2.0
                        ),
                    )
                    / total,
                )
                * 100,
                1,
            ),
        },
        "currency_exposures": fx,
        "note": (
            "First-order estimates from your live positions — floating/short-dated "
            "share reprices within a year; MTM ≈ Σ −Dᵢ×Δy×Pᵢ with per-instrument "
            "par-bond modified durations (floaters at next reset). Not investment advice."
        ),
    }


def _fmt_m(v: float) -> str:
    return f"${v / 1e6:,.0f}M" if abs(v) >= 1e6 else f"${v:,.0f}"
