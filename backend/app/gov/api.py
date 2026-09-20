"""Government Debt Management API endpoints.

All endpoints for DSA, stress testing, maturity analysis,
fiscal tracking, audit, and RBAC.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

router = APIRouter(prefix="/api/gov", tags=["government"])


# ── DSA Endpoints ────────────────────────────────────────────────────

class DSARequest(BaseModel):
    debt_stock: float = Field(..., description="Total public debt stock (USD millions)")
    gdp_nominal: float = Field(..., description="Nominal GDP (USD millions)")
    exports: float = Field(..., description="Goods & services exports (USD millions)")
    revenue: float = Field(..., description="Total government revenue (USD millions)")
    debt_service: float = Field(..., description="Total debt service (USD millions)")
    interest_payments: float = Field(..., description="Interest payments (USD millions)")
    principal_repayments: float = Field(..., description="Principal repayments (USD millions)")
    gross_financing_needs: float = Field(..., description="GFN (USD millions)")
    country_type: str = Field(default="mac", description="mac or lic")
    total_ext_debt: float = Field(default=0)
    concessional_debt: float = Field(default=0)
    short_term_debt: float = Field(default=0)
    reserves: float = Field(default=0)


@router.post("/dsa/analyze")
def analyze_dsa(req: DSARequest):
    from app.gov.dsa import get_dsa_calculator
    return get_dsa_calculator().compute_dsa(**req.model_dump())


@router.get("/dsa/history")
def dsa_history():
    from app.gov.dsa import get_dsa_calculator
    return {"history": get_dsa_calculator().get_history()}


# ── Maturity Profile Endpoints ───────────────────────────────────────

class InstrumentRequest(BaseModel):
    name: str = ""
    isin: str = ""
    type: str = "bond"
    currency: str = "USD"
    coupon_rate: float = 0
    face_value: float = 0
    outstanding: float = 0
    issue_date: str = ""
    maturity_date: str = ""
    investor_type: str = "external"
    investor_name: str = ""
    rating: str = ""


@router.post("/maturity/instrument")
def add_instrument(req: InstrumentRequest):
    from app.gov.maturity import get_maturity_analyzer
    return get_maturity_analyzer().add_instrument(req.model_dump())


@router.delete("/maturity/instrument/{instrument_id}")
def remove_instrument(instrument_id: str):
    from app.gov.maturity import get_maturity_analyzer
    if get_maturity_analyzer().remove_instrument(instrument_id):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Instrument not found")


@router.get("/maturity/instruments")
def list_instruments():
    from app.gov.maturity import get_maturity_analyzer
    return {"instruments": get_maturity_analyzer().get_instruments()}


@router.get("/maturity/profile")
def maturity_profile(as_of_date: str = None):
    from app.gov.maturity import get_maturity_analyzer
    return get_maturity_analyzer().compute_maturity_profile(as_of_date)


# ── Stress Testing Endpoints ─────────────────────────────────────────

@router.get("/stress/scenarios")
def list_scenarios():
    from app.gov.stress import get_stress_engine
    return {"scenarios": get_stress_engine().get_default_scenarios()}


class StressTestRequest(BaseModel):
    baseline: Dict[str, float] = Field(..., description="Baseline macro parameters")
    shocks: Dict[str, float] = Field(..., description="Scenario shocks")


@router.post("/stress/run")
def run_stress_test(req: StressTestRequest):
    from app.gov.stress import get_stress_engine
    return get_stress_engine().run_stress_test(req.baseline, req.shocks)


@router.post("/stress/run/{scenario_id}")
def run_predefined_scenario(scenario_id: str, baseline: Dict[str, float] = None):
    from app.gov.stress import get_stress_engine
    engine = get_stress_engine()
    scenarios = {s["id"]: s for s in engine.get_default_scenarios()}
    if scenario_id not in scenarios:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")

    if baseline is None:
        baseline = {
            "debt_stock": 50000, "gdp": 100000, "exports": 25000,
            "revenue": 30000, "interest_rate": 0.05, "baseline_gdp_growth": 0.03,
            "primary_balance": 500, "fx_rate": 1,
        }

    return engine.run_stress_test(baseline, scenarios[scenario_id]["shocks"])


@router.get("/stress/history")
def stress_history():
    from app.gov.stress import get_stress_engine
    return {"results": get_stress_engine().get_history()}


# ── Fiscal Framework Endpoints ───────────────────────────────────────

class BudgetRequest(BaseModel):
    fiscal_year: str
    gdp_nominal: float
    tax_revenue: float = 0
    non_tax_revenue: float = 0
    grants: float = 0
    other_revenue: float = 0
    recurrent_expenditure: float = 0
    capital_expenditure: float = 0
    interest_payments: float = 0
    transfers: float = 0
    wages: float = 0
    other_expenditure: float = 0
    domestic_borrowing: float = 0
    external_borrowing: float = 0


@router.post("/fiscal/budget")
def set_budget(req: BudgetRequest):
    from app.gov.fiscal import get_fiscal_tracker
    return get_fiscal_tracker().set_budget(req.fiscal_year, req.model_dump())


class FiscalTargetRequest(BaseModel):
    fiscal_year: str
    max_deficit_gdp_pct: Optional[float] = None
    max_debt_gdp_pct: Optional[float] = None
    min_revenue_gdp_pct: Optional[float] = None
    max_interest_revenue_pct: Optional[float] = None


@router.post("/fiscal/targets")
def set_fiscal_targets(req: FiscalTargetRequest):
    from app.gov.fiscal import get_fiscal_tracker
    return get_fiscal_tracker().set_fiscal_target(req.fiscal_year, req.model_dump(exclude={"fiscal_year"}))


@router.get("/fiscal/dashboard/{fiscal_year}")
def fiscal_dashboard(fiscal_year: str):
    from app.gov.fiscal import get_fiscal_tracker
    return get_fiscal_tracker().fiscal_dashboard(fiscal_year)


@router.get("/fiscal/multi-year")
def fiscal_multi_year():
    from app.gov.fiscal import get_fiscal_tracker
    return {"years": get_fiscal_tracker().multi_year_summary()}


# ── Audit & RBAC Endpoints ───────────────────────────────────────────

@router.get("/audit/log")
def audit_log(
    user_id: str = None,
    action: str = None,
    resource: str = None,
    limit: int = 100,
):
    from app.gov.audit import get_audit_logger
    return {"entries": get_audit_logger().query(user_id=user_id, action=action, resource=resource, limit=limit)}


@router.get("/audit/verify")
def verify_audit_integrity():
    from app.gov.audit import get_audit_logger
    return get_audit_logger().verify_integrity()


@router.get("/roles")
def list_roles():
    from app.gov.audit import ROLES, PERMISSION_DESCRIPTIONS
    return {"roles": ROLES, "permissions": PERMISSION_DESCRIPTIONS}


class CreateUserRequest(BaseModel):
    user_id: str
    name: str
    role: str
    department: str = ""


@router.post("/users")
def create_user(req: CreateUserRequest):
    from app.gov.audit import get_rbac_manager
    return get_rbac_manager().create_user(req.user_id, req.name, req.role, req.department)


@router.get("/users")
def list_users():
    from app.gov.audit import get_rbac_manager
    return {"users": get_rbac_manager().list_users()}


@router.get("/users/{user_id}")
def get_user(user_id: str):
    from app.gov.audit import get_rbac_manager
    user = get_rbac_manager().get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
