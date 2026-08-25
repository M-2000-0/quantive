"""Success-fee calculation based on financing cost savings."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, Optional, Tuple


class SuccessFeeCalculator:
    """
    Calculate success fees based on financing cost savings vs baseline.
    
    Model: fee = percentage_of_savings × (baseline_cost - optimized_cost)
    Conditions:
    - Only charged if savings >= minimum_threshold_percent
    - Fee capped at max_cap_percentage of portfolio notional
    - No fee if savings <= 0
    """
    
    # Class-level defaults (can be overridden per-contract)
    DEFAULT_FEE_PERCENTAGE: Decimal = Decimal("10")   # 10% of savings
    DEFAULT_MIN_SAVINGS_THRESHOLD: Decimal = Decimal("2")  # 2% minimum savings
    DEFAULT_MAX_FEE_CAP_PERCENT: Decimal = Decimal("0.5")  # 0.5% of notional
    DEFAULT_FEE_MINIMUM_AMOUNT: Decimal = Decimal("0")   # No minimum fee
    DEFAULT_FEE_MAXIMUM_AMOUNT: Optional[Decimal] = None  # No maximum by default
    
    @staticmethod
    def calculate_fee(
        baseline_cost: Decimal,
        optimized_cost: Decimal,
        fee_percentage: Optional[Decimal] = None,
        min_savings_threshold: Optional[Decimal] = None,
        max_fee_cap_percentage: Optional[Decimal] = None,
        fee_minimum_amount: Optional[Decimal] = None,
        fee_maximum_amount: Optional[Decimal] = None,
        portfolio_notional: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Calculate success fee with full audit trail.
        
        Returns dict with:
        - fee: The calculated fee amount
        - savings: The absolute cost savings
        - savings_percentage: Percentage reduction
        - eligible: Whether fee is eligible (threshold met)
        - reason: Human-readable explanation
        - breakdown: Detailed calculation steps
        """
        
        # Apply defaults
        fee_pct = fee_percentage or SuccessFeeCalculator.DEFAULT_FEE_PERCENTAGE
        threshold = min_savings_threshold or SuccessFeeCalculator.DEFAULT_MIN_SAVINGS_THRESHOLD
        cap_pct = max_fee_cap_percentage or SuccessFeeCalculator.DEFAULT_MAX_FEE_CAP_PERCENT
        fee_min = fee_minimum_amount or SuccessFeeCalculator.DEFAULT_FEE_MINIMUM_AMOUNT
        fee_max = fee_maximum_amount or SuccessFeeCalculator.DEFAULT_FEE_MAXIMUM_AMOUNT
        
        # === STEP 1: Calculate Raw Savings ===
        raw_savings = baseline_cost - optimized_cost
        
        # === STEP 2: Check if Savings Exist ===
        if raw_savings <= 0:
            return {
                "fee": Decimal("0"),
                "savings": Decimal("0"),
                "savings_percentage": Decimal("0"),
                "eligible": False,
                "reason": "No cost savings achieved - optimized cost >= baseline cost",
                "breakdown": {
                    "baseline_cost": str(baseline_cost),
                    "optimized_cost": str(optimized_cost),
                    "raw_savings": str(raw_savings),
                    "savings_percentage_change": "negative or zero",
                    "threshold_met": False,
                    "fee_applicable": False,
                }
            }
        
        # === STEP 3: Calculate Savings Percentage ===
        if baseline_cost == 0:
            savings_pct = Decimal("0")
        else:
            savings_pct = (raw_savings / baseline_cost) * Decimal("100")
        
        # === STEP 4: Check Minimum Savings Threshold ===
        threshold_met = savings_pct >= threshold
        
        if not threshold_met:
            return {
                "fee": Decimal("0"),
                "savings": raw_savings,
                "savings_percentage": savings_pct,
                "eligible": False,
                "reason": f"Savings {savings_pct:.2f}% below minimum threshold of {threshold:.2f}%",
                "breakdown": {
                    "baseline_cost": str(baseline_cost),
                    "optimized_cost": str(optimized_cost),
                    "raw_savings": str(raw_savings),
                    "savings_percentage": str(savings_pct),
                    "threshold": str(threshold),
                    "threshold_met": False,
                    "fee_applicable": False,
                    "shortfall_pct": str(threshold - savings_pct),
                }
            }
        
        # === STEP 5: Calculate Raw Fee Percentage ===
        raw_fee = (raw_savings * fee_pct) / Decimal("100")
        
        # === STEP 6: Apply Fee Minimum ===
        if fee_min > 0 and raw_fee < fee_min:
            adjusted_fee = fee_min
        else:
            adjusted_fee = raw_fee
        
        # === STEP 7: Apply Fee Maximum (Portfolio Cap) ===
        if portfolio_notional and cap_pct < Decimal("1"):
            # Cap is percentage of portfolio notional
            dollar_cap = portfolio_notional * cap_pct
            if dollar_cap < adjusted_fee:
                adjusted_fee = dollar_cap
        elif fee_max and adjusted_fee > fee_max:
            adjusted_fee = fee_max
        
        # === STEP 8: Final Adjustments ===
        # Ensure fee doesn't exceed raw calculation (unless minimum forced it higher)
        final_fee = min(adjusted_fee, raw_fee) if raw_fee > 0 else adjusted_fee
        
        # === STEP 9: Return Comprehensive Result ===
        return {
            "fee": final_fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "savings": raw_savings.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "savings_percentage": savings_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "eligible": True,
            "reason": "Savings threshold met - success fee applicable",
            "breakdown": {
                "baseline_cost": str(baseline_cost),
                "optimized_cost": str(optimized_cost),
                "raw_savings": str(raw_savings),
                "savings_percentage": str(savings_pct),
                "fee_percentage_applied": str(fee_pct),
                "threshold_percentage": str(threshold),
                "threshold_met": True,
                "raw_fee_before_caps": str(raw_fee),
                "adjusted_fee_after_caps": str(final_fee),
                "portfolio_notional": str(portfolio_notional) if portfolio_notional else "N/A",
            }
        }
    
    @staticmethod
    def calculate_savings_percentage_only(
        baseline_cost: Decimal,
        optimized_cost: Decimal,
    ) -> Decimal:
        """Quick calculation of savings percentage without fee logic."""
        if baseline_cost == 0:
            return Decimal("0")
        return ((baseline_cost - optimized_cost) / baseline_cost) * Decimal("100")
    
    @staticmethod
    def validate_inputs(
        baseline_cost: Decimal,
        optimized_cost: Decimal,
    ) -> Tuple[bool, str]:
        """Validate that inputs are suitable for fee calculation."""
        if baseline_cost < 0:
            return False, "Baseline cost cannot be negative"
        if optimized_cost < 0:
            return False, "Optimized cost cannot be negative"
        if optimized_cost > baseline_cost:
            return False, "Optimized cost cannot exceed baseline cost"
        if baseline_cost == 0:
            return False, "Baseline cost must be greater than zero"
        return True, "Valid"


# Convenience function for fast calculations (no class instantiation needed)
def calculate_fee(
    baseline_cost: Decimal,
    optimized_cost: Decimal,
    fee_percentage: Optional[Decimal] = None,
    min_savings_threshold: Optional[Decimal] = None,
    max_fee_cap_percentage: Optional[Decimal] = None,
    portfolio_notional: Optional[Decimal] = None,
) -> Dict[str, Any]:
    """
    Convenience function for fast success-fee calculation.
    
    Usage:
        from app.services.pay_for_performance import calculate_fee
        result = calculate_fee(
            baseline_cost=Decimal("6420000000"),
            optimized_cost=Decimal("6180000000"),
            portfolio_notional=Decimal("50000000000")
        )
    """
    return SuccessFeeCalculator.calculate_fee(
        baseline_cost=baseline_cost,
        optimized_cost=optimized_cost,
        fee_percentage=fee_percentage,
        min_savings_threshold=min_savings_threshold,
        max_fee_cap_percentage=max_fee_cap_percentage,
        portfolio_notional=portfolio_notional,
    )