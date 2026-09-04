"""
Debt Restructuring / Reprofiling Simulator
=============================================
Models haircuts, maturity extensions, coupon reductions, NPV relief.
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RestructuringProposal:
    """A proposed restructuring action on a bond."""
    instrument_id: str
    name: str
    original_principal: float
    original_coupon: float         # Annual %
    original_maturity_years: float
    currency: str

    # Restructuring terms
    haircut_pct: float = 0.0       # Principal reduction %
    maturity_extension_years: float = 0.0  # How many years to extend
    coupon_reduction_bps: float = 0.0  # Coupon reduction in basis points
    grace_period_years: float = 0.0  # Years of no/suspended payments

    # Output
    new_principal: float = 0.0
    new_coupon: float = 0.0
    new_maturity_years: float = 0.0
    npv_relief: float = 0.0        # NPV savings for the debtor
    creditor_loss: float = 0.0     # NPV loss for creditors
    annual_savings: float = 0.0    # Annual debt service reduction


@dataclass
class RestructuringResult:
    """Complete restructuring analysis."""
    proposals: list[RestructuringProposal]
    total_original_debt: float
    total_new_debt: float
    total_npv_relief: float
    total_creditor_loss: float
    total_annual_savings: float
    debt_to_gdp_before: float
    debt_to_gdp_after: float
    debt_service_reduction_pct: float


class RestructuringSimulator:
    """
    Models debt restructuring/reprofiling scenarios.

    Types of restructuring:
    1. Haircut: Reduce principal (e.g., Argentina 2005: 65% haircut)
    2. Maturity extension: Push payments further into the future
    3. Coupon reduction: Lower the interest rate
    4. Grace period: Suspend payments temporarily
    5. Combination: Mix of the above
    """

    def __init__(self, discount_rate: float = 0.08):
        """discount_rate: used for NPV calculations (e.g., 8% exit yield)."""
        self.discount_rate = discount_rate

    def apply_restructuring(
        self,
        instruments: list[dict],
        proposal_type: str = "extension",
        haircut_pct: float = 0.0,
        extension_years: float = 0.0,
        coupon_reduction_bps: float = 0.0,
        grace_years: float = 0.0,
    ) -> RestructuringResult:
        """Apply restructuring terms to a set of instruments."""
        proposals = []
        total_original = 0.0
        total_new = 0.0
        total_npv = 0.0
        total_creditor_loss = 0.0
        total_savings = 0.0

        for inst in instruments:
            principal = float(inst.get("principal_outstanding", 0))
            coupon = float(inst.get("coupon_rate", 0))
            maturity = float(inst.get("maturity_years", 10))
            currency = inst.get("currency", "USD")

            # Apply restructuring
            new_principal = principal * (1 - haircut_pct / 100)
            new_coupon = max(0, coupon - coupon_reduction_bps / 100)
            new_maturity = maturity + extension_years

            # NPV calculation
            original_npv = self._bond_npv(principal, coupon, maturity)
            new_npv = self._bond_npv(new_principal, new_coupon, new_maturity, grace_years)
            npv_relief = original_npv - new_npv
            creditor_loss = original_npv - new_npv

            # Annual savings
            original_annual = principal * coupon / 100
            new_annual = new_principal * new_coupon / 100
            annual_savings = original_annual - new_annual

            proposal = RestructuringProposal(
                instrument_id=inst.get("id", ""),
                name=inst.get("name", ""),
                original_principal=principal,
                original_coupon=coupon,
                original_maturity_years=maturity,
                currency=currency,
                haircut_pct=haircut_pct,
                maturity_extension_years=extension_years,
                coupon_reduction_bps=coupon_reduction_bps,
                grace_period_years=grace_years,
                new_principal=round(new_principal, 2),
                new_coupon=round(new_coupon, 4),
                new_maturity_years=round(new_maturity, 1),
                npv_relief=round(npv_relief, 2),
                creditor_loss=round(creditor_loss, 2),
                annual_savings=round(annual_savings, 2),
            )
            proposals.append(proposal)

            total_original += principal
            total_new += new_principal
            total_npv += npv_relief
            total_creditor_loss += creditor_loss
            total_savings += annual_savings

        # Debt-to-GDP impact
        estimated_gdp = 500e9  # Placeholder
        dtg_before = (total_original / estimated_gdp) * 100
        dtg_after = (total_new / estimated_gdp) * 100
        debt_service_reduction = (total_savings / max(total_original * 0.05, 1)) * 100

        return RestructuringResult(
            proposals=proposals,
            total_original_debt=round(total_original, 2),
            total_new_debt=round(total_new, 2),
            total_npv_relief=round(total_npv, 2),
            total_creditor_loss=round(total_creditor_loss, 2),
            total_annual_savings=round(total_savings, 2),
            debt_to_gdp_before=round(dtg_before, 2),
            debt_to_gdp_after=round(dtg_after, 2),
            debt_service_reduction_pct=round(min(debt_service_reduction, 100), 2),
        )

    def _bond_npv(
        self,
        principal: float,
        coupon_rate: float,
        maturity_years: float,
        grace_years: float = 0,
    ) -> float:
        """Compute NPV of bond cash flows using exit yield."""
        r = self.discount_rate
        annual_coupon = principal * coupon_rate / 100
        npv = 0.0

        for year in range(1, int(maturity_years) + 1):
            if year <= grace_years:
                continue  # No payments during grace period
            cf = annual_coupon
            if year == int(maturity_years):
                cf += principal  # Principal repayment at maturity
            npv += cf / ((1 + r) ** year)

        return npv

    def compare_scenarios(
        self,
        instruments: list[dict],
        scenarios: list[dict],
    ) -> list[RestructuringResult]:
        """Compare multiple restructuring scenarios side by side."""
        results = []
        for scenario in scenarios:
            result = self.apply_restructuring(
                instruments,
                haircut_pct=scenario.get("haircut_pct", 0),
                extension_years=scenario.get("extension_years", 0),
                coupon_reduction_bps=scenario.get("coupon_reduction_bps", 0),
                grace_years=scenario.get("grace_years", 0),
            )
            results.append(result)
        return results
