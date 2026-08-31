"""Investor classification + conflict detection — §3-5."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel

from quantive.investor.models import Horizon, InvestmentObjective, InvestorProfile


class ProfileConflict(BaseModel):
    severity: Literal["warning", "error"]
    code: str
    message: str
    field: str | None = None


class InvestorEngine:
    """Stateless profiler: classifies and validates investor profiles."""

    # Thresholds for auto-classification
    CLASSIFICATION_RULES: dict[InvestmentObjective, dict] = {
        InvestmentObjective.CAPITAL_PRESERVATION: {"max_vol": 0.08, "max_dd": 0.10, "desc": "Prioritize low volatility, capital preservation, liquidity"},
        InvestmentObjective.INCOME: {"max_vol": 0.10, "max_dd": 0.12, "desc": "Stable returns, diversification, lower volatility"},
        InvestmentObjective.BALANCED: {"max_vol": 0.15, "max_dd": 0.20, "desc": "Balance growth, income, risk"},
        InvestmentObjective.GROWTH: {"max_vol": 0.22, "max_dd": 0.30, "desc": "Long-term appreciation, moderate-high risk"},
        InvestmentObjective.AGGRESSIVE_GROWTH: {"max_vol": 0.30, "max_dd": 0.40, "desc": "High expected growth, accepts significant volatility"},
        InvestmentObjective.SPECULATIVE: {"max_vol": 0.50, "max_dd": 0.60, "desc": "High-volatility assets only with explicit acknowledgement"},
    }

    def classify(self, profile: InvestorProfile) -> InvestmentObjective:
        """Return the InvestmentObjective that best fits risk numbers."""
        # Use max_acceptable_drawdown as primary classifier
        dd = profile.risk_tolerance.max_acceptable_drawdown
        if dd <= 0.10:
            return InvestmentObjective.CAPITAL_PRESERVATION
        if dd <= 0.15:
            return InvestmentObjective.INCOME
        if dd <= 0.25:
            return InvestmentObjective.BALANCED
        if dd <= 0.35:
            return InvestmentObjective.GROWTH
        if dd <= 0.50:
            return InvestmentObjective.AGGRESSIVE_GROWTH
        return InvestmentObjective.SPECULATIVE

    def validate(self, profile: InvestorProfile) -> list[ProfileConflict]:
        """Check for tolerance vs capacity conflicts, horizon mismatches etc."""
        conflicts: list[ProfileConflict] = []
        # §4 tolerance vs capacity
        if conflict := profile.risk_conflict():
            conflicts.append(ProfileConflict(severity="warning", code="tolerance_exceeds_capacity", message=conflict, field="risk_tolerance.max_acceptable_drawdown"))
        # Horizon vs objective
        if profile.horizon == Horizon.SHORT and profile.investment_objective in (InvestmentObjective.AGGRESSIVE_GROWTH, InvestmentObjective.SPECULATIVE):
            conflicts.append(ProfileConflict(severity="warning", code="horizon_objective_mismatch", message="Short horizon with aggressive/speculative objective — consider rebalancing horizon or de-risking", field="horizon"))
        # Concentration vs diversification
        if profile.concentration_preference == "concentrated" and profile.min_diversification > 10:
            conflicts.append(ProfileConflict(severity="info", code="concentration_diversification_tension", message="Concentrated preference conflicts with high diversification minimum", field="concentration_preference"))
        # Speculative without acknowledgement
        if profile.investment_objective == InvestmentObjective.SPECULATIVE and profile.investment_experience == "novice":
            conflicts.append(ProfileConflict(severity="warning", code="speculative_novice", message="Speculative objective with novice experience — requires explicit acknowledgement and controls", field="investment_experience"))
        # Liquidity need vs capacity DD
        if profile.risk_capacity.liquidity_need_pct > 0.5 and profile.horizon == Horizon.LONG:
            conflicts.append(ProfileConflict(severity="warning", code="liquidity_horizon_mismatch", message="High near-term liquidity need with long horizon", field="risk_capacity.liquidity_need_pct"))
        return conflicts

    def effective_max_drawdown(self, profile: InvestorProfile, require_ack: bool = False) -> float:
        """Effective investable DD — capacity is hard ceiling unless acked."""
        tol = profile.risk_tolerance.max_acceptable_drawdown
        cap = profile.risk_capacity.max_sustainable_drawdown
        if tol > cap and not require_ack:
            return cap
        return tol

    def describe(self, profile: InvestorProfile) -> dict:
        """Explainable summary for Why This Portfolio? (§51)."""
        inferred = self.classify(profile)
        conflicts = self.validate(profile)
        return {
            "profile_id": profile.id,
            "stated_objective": profile.investment_objective.value,
            "inferred_objective": inferred.value,
            "horizon": profile.horizon.value,
            "horizon_years": profile.horizon_years(),
            "tolerance_dd": profile.risk_tolerance.max_acceptable_drawdown,
            "capacity_dd": profile.risk_capacity.max_sustainable_drawdown,
            "effective_dd": self.effective_max_drawdown(profile),
            "conflicts": [c.model_dump() for c in conflicts],
            "speculative_allowed": profile.is_speculative_allowed(),
        }
