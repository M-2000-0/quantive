"""
Data Validation & Reconciliation Layer
=======================================
Cross-checks aggregated cash flows, flags missing/inconsistent fields,
validates instrument data integrity.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ValidationIssue:
    """A single data quality issue."""
    severity: str  # "error", "warning", "info"
    field: str
    message: str
    record_id: str = ""
    suggested_fix: str = ""


@dataclass
class ValidationReport:
    """Complete validation report for a portfolio or instrument set."""
    total_records: int = 0
    issues: list[ValidationIssue] = field(default_factory=list)
    passed: bool = True
    error_count: int = 0
    warning_count: int = 0

    def add(self, issue: ValidationIssue):
        self.issues.append(issue)
        if issue.severity == "error":
            self.error_count += 1
            self.passed = False
        elif issue.severity == "warning":
            self.warning_count += 1

    def to_dict(self) -> dict:
        return {
            "total_records": self.total_records,
            "passed": self.passed,
            "errors": self.error_count,
            "warnings": self.warning_count,
            "issues": [
                {"severity": i.severity, "field": i.field, "message": i.message,
                 "record_id": i.record_id, "suggested_fix": i.suggested_fix}
                for i in self.issues
            ],
        }


class InstrumentValidator:
    """Validate individual debt instrument records."""

    REQUIRED_FIELDS = [
        "name", "instrument_type", "currency", "principal_outstanding",
        "coupon_rate", "maturity_date", "issue_date",
    ]

    VALID_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD",
                        "NGN", "GHS", "KES", "ZAR", "EGP", "BRL", "MXN",
                        "INR", "CNY", "IDR", "TRY", "SAR", "AED", "QAR"}

    def validate(self, instrument: dict) -> list[ValidationIssue]:
        issues = []
        record_id = instrument.get("id", "unknown")

        # 1. Required fields
        for field_name in self.REQUIRED_FIELDS:
            val = instrument.get(field_name)
            if val is None or (isinstance(val, str) and not val.strip()):
                issues.append(ValidationIssue(
                    severity="error", field=field_name,
                    message=f"Required field '{field_name}' is missing or empty",
                    record_id=record_id,
                    suggested_fix=f"Provide a value for {field_name}",
                ))

        # 2. Currency validation
        currency = instrument.get("currency", "")
        if currency and currency.upper() not in self.VALID_CURRENCIES:
            issues.append(ValidationIssue(
                severity="warning", field="currency",
                message=f"Currency '{currency}' not in known currency list",
                record_id=record_id,
            ))

        # 3. Principal > 0
        principal = instrument.get("principal_outstanding")
        if principal is not None:
            try:
                p = float(principal)
                if p <= 0:
                    issues.append(ValidationIssue(
                        severity="error", field="principal_outstanding",
                        message=f"Principal must be positive, got {p}",
                        record_id=record_id,
                    ))
            except (ValueError, TypeError):
                issues.append(ValidationIssue(
                    severity="error", field="principal_outstanding",
                    message=f"Principal must be numeric, got '{principal}'",
                    record_id=record_id,
                ))

        # 4. Coupon rate reasonable (0-30%)
        coupon = instrument.get("coupon_rate")
        if coupon is not None:
            try:
                c = float(coupon)
                if c < 0:
                    issues.append(ValidationIssue(
                        severity="error", field="coupon_rate",
                        message=f"Coupon rate cannot be negative: {c}%",
                        record_id=record_id,
                    ))
                elif c > 30:
                    issues.append(ValidationIssue(
                        severity="warning", field="coupon_rate",
                        message=f"Coupon rate unusually high: {c}% — verify this is correct",
                        record_id=record_id,
                    ))
            except (ValueError, TypeError):
                issues.append(ValidationIssue(
                    severity="error", field="coupon_rate",
                    message=f"Coupon rate must be numeric, got '{coupon}'",
                    record_id=record_id,
                ))

        # 5. Date validation
        maturity = instrument.get("maturity_date", "")
        issue_date = instrument.get("issue_date", "")
        if maturity and issue_date:
            try:
                mat_dt = datetime.strptime(maturity, "%Y-%m-%d")
                iss_dt = datetime.strptime(issue_date, "%Y-%m-%d")
                if mat_dt <= iss_dt:
                    issues.append(ValidationIssue(
                        severity="error", field="maturity_date",
                        message=f"Maturity ({maturity}) must be after issue date ({issue_date})",
                        record_id=record_id,
                    ))
                if mat_dt < datetime.now():
                    issues.append(ValidationIssue(
                        severity="warning", field="maturity_date",
                        message=f"Instrument is already matured ({maturity})",
                        record_id=record_id,
                    ))
            except ValueError:
                issues.append(ValidationIssue(
                    severity="error", field="maturity_date",
                    message=f"Invalid date format: expected YYYY-MM-DD",
                    record_id=record_id,
                ))

        # 6. Callable instrument must have call date
        if instrument.get("is_callable"):
            if not instrument.get("call_date"):
                issues.append(ValidationIssue(
                    severity="warning", field="call_date",
                    message="Instrument is callable but no call date provided",
                    record_id=record_id,
                ))

        return issues


class CashFlowReconciler:
    """Cross-check that aggregated cash flows match reported totals."""

    def reconcile(
        self,
        instruments: list[dict],
        reported_total: Optional[float] = None,
    ) -> ValidationReport:
        report = ValidationReport(total_records=len(instruments))

        # Calculate expected cash flows
        total_annual_interest = 0.0
        total_principal = 0.0

        for inst in instruments:
            principal = float(inst.get("principal_outstanding", 0))
            coupon = float(inst.get("coupon_rate", 0))
            total_annual_interest += principal * coupon / 100
            total_principal += principal

        # Cross-check against reported total
        if reported_total is not None:
            expected = total_annual_interest
            diff = abs(expected - reported_total)
            diff_pct = (diff / max(reported_total, 1)) * 100

            if diff_pct > 5:
                report.add(ValidationIssue(
                    severity="error", field="total_interest",
                    message=f"Reported interest ({reported_total:,.2f}) differs from "
                            f"calculated ({expected:,.2f}) by {diff_pct:.1f}%",
                    suggested_fix="Check coupon rates and principal amounts",
                ))
            elif diff_pct > 1:
                report.add(ValidationIssue(
                    severity="warning", field="total_interest",
                    message=f"Minor discrepancy: reported {reported_total:,.2f} vs "
                            f"calculated {expected:,.2f} ({diff_pct:.1f}%)",
                ))

        # Check for duplicate instruments (same name + maturity)
        seen = {}
        for inst in instruments:
            key = (inst.get("name", ""), inst.get("maturity_date", ""))
            if key in seen:
                report.add(ValidationIssue(
                    severity="warning", field="name",
                    message=f"Possible duplicate: '{key[0]}' with maturity {key[1]}",
                    record_id=inst.get("id", ""),
                    suggested_fix="Verify these are distinct instruments",
                ))
            seen[key] = inst.get("id", "")

        # Summary
        report.add(ValidationIssue(
            severity="info", field="summary",
            message=f"Total principal: ${total_principal:,.2f}, "
                    f"Annual interest: ${total_annual_interest:,.2f}",
        ))

        return report
