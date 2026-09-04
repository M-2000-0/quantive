"""
IMF/World Bank Export Templates
================================
Generates debt data in standard formats:
- IMF MTDS (Medium-Term Debt Strategy) template
- IMF DSA (Debt Sustainability Analysis) format
- World Bank IDS (International Debt Statistics) format
"""

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/exports", tags=["exports"])


# ── Request Models ─────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    format: str  # "csv", "json", "xlsx"
    country_code: str = "MEX"
    fiscal_year: int = 2025
    include_projections: bool = True
    projection_years: int = 5


class MTDSRecord(BaseModel):
    """Single row of the IMF MTDS template."""
    year: int
    total_debt_stock: float
    domestic_debt: float
    external_debt: float
    new_disbursements: float
    amortization: float
    interest_payments: float
    debt_service: float
    primary_balance: float
    gdp: float
    debt_to_gdp: float
    debt_service_to_revenue: float
    debt_service_to_exports: float
    short_term_debt: float
    concessional_share: float
    weighted_avg_maturity: float
    weighted_avg_coupon: float
    currency_composition_usd: float
    currency_composition_eur: float
    currency_composition_local: float
    currency_composition_other: float


class DSARecord(BaseModel):
    """Single row of the IMF DSA framework."""
    year: int
    pvi: float  # Present value of debt / exports
    debt_service_ratio: float
    debt_to_gdp: float
    debt_to_revenue: float
    interest_to_revenue: float
    short_term_to_reserves: float
    residual_maturity: float
    gdp_growth: float
    primary_balance_to_gdp: float
    current_account_to_gdp: float
    international_reserves_months: float
    pvi_threshold: float
    dsr_threshold: float
    debt_gdp_threshold: float
    pvi_status: str  # "pass", "borderline", "fail"
    dsr_status: str
    debt_gdp_status: str
    overall_assessment: str  # "low_risk", "moderate_risk", "high_risk", "in_default"


# ── Export Engine ───────────────────────────────────────────────────────

class IMFExportEngine:
    """Generates standard IMF/World Bank export formats."""

    # DSA thresholds (simplified, based on IMF LIC-DSA and market-access-country frameworks)
    DSA_THRESHOLDS = {
        "lic": {
            "pvi": 140.0,       # PV of debt/exports
            "dsr": 14.0,        # Debt service/exports
            "debt_gdp": 30.0,   # Debt-to-GDP
            "debt_revenue": 140.0,  # Debt/revenue
            "interest_revenue": 14.0,  # Interest/revenue
            "short_reserves": 15.0,   # Short-term/reserves
        },
        "mac": {
            "pvi": 140.0,
            "dsr": 15.0,
            "debt_gdp": 55.0,
            "debt_revenue": 300.0,
            "interest_revenue": 18.0,
            "short_reserves": 100.0,
        },
    }

    def generate_mtds_data(
        self,
        country_code: str,
        fiscal_year: int,
        include_projections: bool = True,
        projection_years: int = 5,
    ) -> list[MTDSRecord]:
        """
        Generate MTDS template data.
        In production: pulls from real IMF MTDS database.
        Currently: generates structured placeholder that matches the exact MTDS format.
        """
        import random
        random.seed(hash(country_code + str(fiscal_year)))

        records = []
        base_debt = 500e9
        base_gdp = 1000e9
        base_revenue = 250e9

        total_years = 1 if not include_projections else 1 + projection_years

        for i in range(total_years):
            year = fiscal_year + i
            gdp_growth = 2.5 - (i * 0.1) + random.uniform(-0.5, 0.5)
            debt_growth = 3.0 + random.uniform(-1, 1)

            domestic_share = 0.45 + random.uniform(-0.05, 0.05)
            external_share = 1 - domestic_share
            usd_share = external_share * 0.55
            eur_share = external_share * 0.25
            other_share = external_share * 0.20

            debt_stock = base_debt * ((1 + debt_growth / 100) ** i)
            gdp = base_gdp * ((1 + gdp_growth / 100) ** i)
            revenue = base_revenue * ((1 + gdp_growth / 100 * 0.7) ** i)

            coupon = 5.5 + random.uniform(-1, 1)
            maturity = 7.2 + random.uniform(-1, 1)

            annual_coupon_payment = debt_stock * coupon / 100
            amortization = debt_stock / maturity
            debt_service = annual_coupon_payment + amortization

            records.append(MTDSRecord(
                year=year,
                total_debt_stock=round(debt_stock, 2),
                domestic_debt=round(debt_stock * domestic_share, 2),
                external_debt=round(debt_stock * external_share, 2),
                new_disbursements=round(debt_stock * 0.12, 2),
                amortization=round(amortization, 2),
                interest_payments=round(annual_coupon_payment, 2),
                debt_service=round(debt_service, 2),
                primary_balance=round(gdp * 0.02, 2),
                gdp=round(gdp, 2),
                debt_to_gdp=round((debt_stock / gdp) * 100, 2),
                debt_service_to_revenue=round((debt_service / revenue) * 100, 2),
                debt_service_to_exports=round((debt_service / (revenue * 0.35)) * 100, 2),
                short_term_debt=round(debt_stock * 0.15, 2),
                concessional_share=round(domestic_share * 0.2 * 100, 2),
                weighted_avg_maturity=round(maturity, 2),
                weighted_avg_coupon=round(coupon, 2),
                currency_composition_usd=round(usd_share * 100, 2),
                currency_composition_eur=round(eur_share * 100, 2),
                currency_composition_local=round(domestic_share * 100, 2),
                currency_composition_other=round(other_share * 100, 2),
            ))

        return records

    def generate_dsa_data(
        self,
        country_code: str,
        fiscal_year: int,
        include_projections: bool = True,
        projection_years: int = 5,
        framework: str = "mac",
    ) -> list[DSARecord]:
        """Generate DSA template data with threshold assessment."""
        import random
        random.seed(hash(country_code + str(fiscal_year) + "dsa"))

        thresholds = self.DSA_THRESHOLDS.get(framework, self.DSA_THRESHOLDS["mac"])
        records = []
        base_debt = 500e9
        base_gdp = 1000e9
        base_exports = 350e9
        base_revenue = 250e9
        base_reserves = 80e9

        total_years = 1 if not include_projections else 1 + projection_years

        for i in range(total_years):
            year = fiscal_year + i
            gdp_growth = 2.5 - (i * 0.15)
            debt_to_gdp = (base_debt / base_gdp) * 100 * (1 + 0.02 * i)
            exports = base_exports * (1 + gdp_growth / 100 * 0.8) ** i
            revenue = base_revenue * (1 + gdp_growth / 100 * 0.7) ** i
            reserves = base_reserves * (1 + random.uniform(-0.02, 0.02)) ** i
            debt = base_debt * (1 + 0.03) ** i
            debt_service = debt * 0.08  # Simplified

            pvi = (debt * 0.85 / exports) * 100  # PV of debt/exports
            dsr = (debt_service / exports) * 100
            interest_to_rev = (debt * 0.055 / revenue) * 100
            short_term = debt * 0.15
            short_to_reserves = (short_term / reserves) * 100
            residual_mat = 6.5 + random.uniform(-1, 1)

            # Threshold assessment
            def assess(value, threshold, direction="below"):
                if direction == "below":
                    if value <= threshold * 0.8:
                        return "pass"
                    elif value <= threshold:
                        return "borderline"
                    return "fail"
                return "pass"

            pvi_status = assess(pvi, thresholds["pvi"])
            dsr_status = assess(dsr, thresholds["dsr"])
            debt_gdp_status = assess(debt_to_gdp, thresholds["debt_gdp"])

            fail_count = [pvi_status, dsr_status, debt_gdp_status].count("fail")
            borderline_count = [pvi_status, dsr_status, debt_gdp_status].count("borderline")

            if fail_count >= 2:
                overall = "high_risk"
            elif fail_count >= 1:
                overall = "moderate_risk"
            elif borderline_count >= 2:
                overall = "moderate_risk"
            else:
                overall = "low_risk"

            records.append(DSARecord(
                year=year,
                pvi=round(pvi, 2),
                debt_service_ratio=round(dsr, 2),
                debt_to_gdp=round(debt_to_gdp, 2),
                debt_to_revenue=round((debt / revenue) * 100, 2),
                interest_to_revenue=round(interest_to_rev, 2),
                short_term_to_reserves=round(short_to_reserves, 2),
                residual_maturity=round(residual_mat, 2),
                gdp_growth=round(gdp_growth, 2),
                primary_balance_to_gdp=round(2.0 - i * 0.1, 2),
                current_account_to_gdp=round(-2.5 + random.uniform(-1, 1), 2),
                international_reserves_months=round(reserves / (base_exports / 12), 2),
                pvi_threshold=thresholds["pvi"],
                dsr_threshold=thresholds["dsr"],
                debt_gdp_threshold=thresholds["debt_gdp"],
                pvi_status=pvi_status,
                dsr_status=dsr_status,
                debt_gdp_status=debt_gdp_status,
                overall_assessment=overall,
            ))

        return records

    def generate_ids_data(
        self,
        country_code: str,
        fiscal_year: int,
    ) -> list[dict]:
        """
        Generate World Bank International Debt Statistics format.
        Reference: https://databank.worldbank.org/source/international-debt-statistics
        """
        import random
        random.seed(hash(country_code + str(fiscal_year) + "ids"))

        return [{
            "country_code": country_code,
            "year": fiscal_year,
            "total_debt_stock": round(500e9 * random.uniform(0.95, 1.05)),
            "short_term_debt": round(500e9 * 0.15 * random.uniform(0.9, 1.1)),
            "long_term_debt": round(500e9 * 0.85 * random.uniform(0.9, 1.1)),
            "public_external_debt": round(250e9 * random.uniform(0.9, 1.1)),
            "private_nonguaranteed": round(50e9 * random.uniform(0.9, 1.1)),
            "total_debt_service": round(500e9 * 0.08 * random.uniform(0.9, 1.1)),
            "principal_repayments": round(500e9 * 0.05 * random.uniform(0.9, 1.1)),
            "interest_payments": round(500e9 * 0.03 * random.uniform(0.9, 1.1)),
            "net_flows": round(50e9 * random.uniform(-1, 1)),
            "net_transfers": round(40e9 * random.uniform(-1, 1)),
            "interest_ratio": round(random.uniform(4.5, 7.0), 2),
            "concessional_ratio": round(random.uniform(30, 50), 2),
            "currency_composition_usd": round(random.uniform(50, 65), 2),
            "currency_composition_eur": round(random.uniform(15, 25), 2),
            "currency_composition_sdr": round(random.uniform(5, 10), 2),
            "currency_composition_other": round(random.uniform(5, 15), 2),
            "multilateral_share": round(random.uniform(15, 30), 2),
            "bilateral_share": round(random.uniform(10, 25), 2),
            "commercial_share": round(random.uniform(20, 40), 2),
        }]


# ── API Endpoints ──────────────────────────────────────────────────────

engine = IMFExportEngine()


@router.post("/mtds")
def export_mtds(request: ExportRequest):
    """Export data in IMF MTDS (Medium-Term Debt Strategy) format."""
    records = engine.generate_mtds_data(
        request.country_code, request.fiscal_year,
        request.include_projections, request.projection_years,
    )

    if request.format == "json":
        return {"format": "mtds", "records": [r.model_dump() for r in records]}
    elif request.format == "csv":
        output = io.StringIO()
        if records:
            writer = csv.DictWriter(output, fieldnames=records[0].model_fields.keys())
            writer.writeheader()
            for r in records:
                writer.writerow(r.model_dump())
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=MTDS_{request.country_code}_{request.fiscal_year}.csv"},
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")


@router.post("/dsa")
def export_dsa(request: ExportRequest):
    """Export data in IMF DSA (Debt Sustainability Analysis) format."""
    records = engine.generate_dsa_data(
        request.country_code, request.fiscal_year,
        request.include_projections, request.projection_years,
    )

    if request.format == "json":
        return {"format": "dsa", "records": [r.model_dump() for r in records]}
    elif request.format == "csv":
        output = io.StringIO()
        if records:
            writer = csv.DictWriter(output, fieldnames=records[0].model_fields.keys())
            writer.writeheader()
            for r in records:
                writer.writerow(r.model_dump())
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=DSA_{request.country_code}_{request.fiscal_year}.csv"},
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")


@router.post("/ids")
def export_ids(request: ExportRequest):
    """Export data in World Bank IDS (International Debt Statistics) format."""
    records = engine.generate_ids_data(request.country_code, request.fiscal_year)

    if request.format == "json":
        return {"format": "ids", "records": records}
    elif request.format == "csv":
        output = io.StringIO()
        if records:
            writer = csv.DictWriter(output, fieldnames=records[0].keys())
            writer.writeheader()
            for r in records:
                writer.writerow(r)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=IDS_{request.country_code}_{request.fiscal_year}.csv"},
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")


@router.get("/formats")
def list_export_formats():
    """List all available export formats and their descriptions."""
    return {
        "formats": [
            {
                "id": "mtds",
                "name": "IMF MTDS",
                "full_name": "Medium-Term Debt Strategy",
                "description": "Standard IMF template for medium-term debt management strategy analysis",
                "supported_formats": ["csv", "json"],
                "fields": [
                    "Year", "Total Debt Stock", "Domestic Debt", "External Debt",
                    "New Disbursements", "Amortization", "Interest Payments", "Debt Service",
                    "Primary Balance", "GDP", "Debt-to-GDP", "DSR/Revenue",
                    "DSR/Exports", "Short-Term Debt", "Concessional Share",
                    "WAM", "WAC", "Currency Composition",
                ],
            },
            {
                "id": "dsa",
                "name": "IMF DSA",
                "full_name": "Debt Sustainability Analysis",
                "description": "IMF/World Bank joint framework for assessing debt sustainability",
                "supported_formats": ["csv", "json"],
                "fields": [
                    "Year", "PV/Exports", "DSR", "Debt-to-GDP", "Debt/Revenue",
                    "Interest/Revenue", "ST/Reserves", "Residual Maturity",
                    "GDP Growth", "Primary Balance/GDP", "CA/GDP", "Reserves Months",
                    "Threshold Assessment", "Overall Assessment",
                ],
            },
            {
                "id": "ids",
                "name": "World Bank IDS",
                "full_name": "International Debt Statistics",
                "description": "World Bank standardized debt statistics format",
                "supported_formats": ["csv", "json"],
                "fields": [
                    "Country Code", "Year", "Total Debt", "Short-Term", "Long-Term",
                    "Public External", "Private Unguaranteed", "Debt Service",
                    "Principal", "Interest", "Net Flows", "Net Transfers",
                    "Interest Ratio", "Concessional Ratio", "Currency Composition",
                    "Creditor Composition",
                ],
            },
        ]
    }
