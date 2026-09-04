"""Financial Calculation Validation Layer.

Prevents silent data corruption and rounding errors.
Every financial calculation passes through this validator before returning results.
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Any


# Maximum allowed values for sovereign debt
MAX_PRINCIPAL = Decimal("1000000000000")  #  trillion
MAX_COUPON_RATE = Decimal("0.30")  # 30%
MAX_SPREAD_BPS = Decimal("5000")  # 500 basis points
MAX_MATURITY_YEARS = Decimal("100")  # 100 years


class FinancialValidationError(Exception):
    """Raised when a financial calculation fails validation."""

    def __init__(self, field: str, value: Any, message: str):
        self.field = field
        self.value = value
        self.message = message
        super().__init__(f"Financial validation error on {field}: {message} (value={value})")


def validate_decimal(value: Any, field_name: str, max_value: Decimal = MAX_PRINCIPAL) -> Decimal:
    """Convert and validate a financial value as Decimal."""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise FinancialValidationError(field_name, value, "Cannot convert to Decimal")

    if d < 0:
        raise FinancialValidationError(field_name, value, "Must be non-negative")

    if d > max_value:
        raise FinancialValidationError(field_name, value, f"Exceeds maximum of {max_value}")

    return d


def validate_coupon_rate(rate: Any) -> Decimal:
    """Validate a coupon rate (must be between 0% and 30%)."""
    return validate_decimal(rate, "coupon_rate", MAX_COUPON_RATE)


def validate_principal(amount: Any) -> Decimal:
    """Validate a principal amount."""
    return validate_decimal(amount, "principal", MAX_PRINCIPAL)


def validate_spread(bps: Any) -> Decimal:
    """Validate spread in basis points."""
    return validate_decimal(bps, "spread_bps", MAX_SPREAD_BPS)


def compute_finite_decimal(value: Decimal, places: int = 6) -> Decimal:
    """Round to fixed precision using banker's rounding."""
    return value.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)


def validate_optimization_result(result: dict) -> dict:
    """Validate an entire optimization result for financial accuracy."""
    errors = []

    # Validate allocations sum to ~100%
    if "allocation" in result:
        alloc = result["allocation"]
        total = sum(Decimal(str(v)) for v in alloc.values())
        if abs(total - Decimal("100")) > Decimal("0.01"):
            errors.append(f"Allocations sum to {total}% instead of 100%")

    # Validate no negative values where inappropriate
    for key in ["total_cost", "total_risk", "expected_return"]:
        if key in result:
            try:
                v = Decimal(str(result[key]))
                if v < 0 and key != "total_cost":  # cost can be negative (savings)
                    errors.append(f"{key} should not be negative: {v}")
            except Exception:
                errors.append(f"{key} is not a valid number: {result[key]}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "validated_at": str(__import__("datetime").datetime.now(__import__("datetime").timezone.utc)),
    }
