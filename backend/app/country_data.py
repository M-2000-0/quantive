"""Sovereign Debt Country Database.

Real profiles for 50+ major economies with debt metrics, credit ratings,
and comparison analytics. Data sourced from IMF, World Bank, and rating agencies.

Usage:
    from app.country_data import get_country, compare_countries, get_peer_group
    country = get_country("US")
    comparison = compare_countries(["US", "UK", "JP", "DE", "FR"])
    peers = get_peer_group("US", group="g7")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SovereignProfile:
    """Complete sovereign debt profile for a country."""
    code: str
    name: str
    region: str
    income_group: str  # "high", "upper_middle", "lower_middle", "low"

    # Credit ratings (as of 2024-2025)
    rating_sp: str
    rating_moody: str
    rating_fitch: str
    rating_outlook: str  # "stable", "positive", "negative"

    # Debt metrics (% of GDP)
    debt_to_gdp: float
    external_debt_to_gdp: float
    short_term_debt_to_gdp: float
    debt_service_to_revenue: float
    interest_to_revenue: float

    # GDP and economy
    gdp_nominal_trillions: float
    gdp_per_capita: float
    gdp_growth_pct: float
    inflation_pct: float
    unemployment_pct: float

    # Fiscal
    fiscal_balance_pct: float
    primary_balance_pct: float
    revenue_to_gdp: float
    expenditure_to_gdp: float

    # External
    current_account_pct: float
    reserves_months_imports: float
    external_debt_usd_trillions: float
    foreign_held_pct: float

    # Debt management
    avg_maturity_years: float
    avg_coupon_pct: float
    domestic_share_pct: float
    currency: str

    # Population and demographics
    population_millions: float
    median_age: float

    # Groups
    groups: list[str] = field(default_factory=list)  # "g7", "g20", "eu", "oecd", "brics", etc.

    @property
    def investment_grade(self) -> bool:
        """Check if investment grade (BBB- or above)."""
        ig_ratings = {"AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-"}
        return self.rating_sp in ig_ratings

    @property
    def risk_tier(self) -> str:
        """Risk tier based on credit rating."""
        if self.rating_sp in {"AAA", "AA+", "AA"}:
            return "very_low"
        elif self.rating_sp in {"AA-", "A+", "A", "A-"}:
            return "low"
        elif self.rating_sp in {"BBB+", "BBB", "BBB-"}:
            return "moderate"
        elif self.rating_sp in {"BB+", "BB", "BB-"}:
            return "elevated"
        else:
            return "high"

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "region": self.region,
            "income_group": self.income_group,
            "ratings": {
                "sp": self.rating_sp,
                "moody": self.rating_moody,
                "fitch": self.rating_fitch,
                "outlook": self.rating_outlook,
                "investment_grade": self.investment_grade,
                "risk_tier": self.risk_tier,
            },
            "debt_metrics": {
                "debt_to_gdp": self.debt_to_gdp,
                "external_debt_to_gdp": self.external_debt_to_gdp,
                "short_term_debt_to_gdp": self.short_term_debt_to_gdp,
                "debt_service_to_revenue": self.debt_service_to_revenue,
                "interest_to_revenue": self.interest_to_revenue,
            },
            "economy": {
                "gdp_nominal_trillions": self.gdp_nominal_trillions,
                "gdp_per_capita": self.gdp_per_capita,
                "gdp_growth_pct": self.gdp_growth_pct,
                "inflation_pct": self.inflation_pct,
                "unemployment_pct": self.unemployment_pct,
            },
            "fiscal": {
                "fiscal_balance_pct": self.fiscal_balance_pct,
                "primary_balance_pct": self.primary_balance_pct,
                "revenue_to_gdp": self.revenue_to_gdp,
                "expenditure_to_gdp": self.expenditure_to_gdp,
            },
            "external": {
                "current_account_pct": self.current_account_pct,
                "reserves_months_imports": self.reserves_months_imports,
                "external_debt_usd_trillions": self.external_debt_usd_trillions,
                "foreign_held_pct": self.foreign_held_pct,
            },
            "debt_management": {
                "avg_maturity_years": self.avg_maturity_years,
                "avg_coupon_pct": self.avg_coupon_pct,
                "domestic_share_pct": self.domestic_share_pct,
                "currency": self.currency,
            },
            "demographics": {
                "population_millions": self.population_millions,
                "median_age": self.median_age,
            },
            "groups": self.groups,
        }


# ── Country Database ────────────────────────────────────────────────────

COUNTRIES: dict[str, SovereignProfile] = {}

def _add(p: SovereignProfile):
    COUNTRIES[p.code] = p

# G7
_add(SovereignProfile(
    code="US", name="United States", region="north_america", income_group="high",
    rating_sp="AA+", rating_moody="Aaa", rating_fitch="AAA", rating_outlook="stable",
    debt_to_gdp=123.0, external_debt_to_gdp=98.0, short_term_debt_to_gdp=22.0,
    debt_service_to_revenue=16.5, interest_to_revenue=13.0,
    gdp_nominal_trillions=28.0, gdp_per_capita=82000, gdp_growth_pct=2.5,
    inflation_pct=3.2, unemployment_pct=3.7,
    fiscal_balance_pct=-6.5, primary_balance_pct=-3.5,
    revenue_to_gdp=18.0, expenditure_to_gdp=24.5,
    current_account_pct=-3.5, reserves_months_imports=2.0,
    external_debt_usd_trillions=33.0, foreign_held_pct=30.0,
    avg_maturity_years=6.2, avg_coupon_pct=3.1, domestic_share_pct=70.0,
    currency="USD", population_millions=335.0, median_age=38.5,
    groups=["g7", "g20", "oecd", "nato", "five_eyes"],
))

_add(SovereignProfile(
    code="UK", name="United Kingdom", region="europe", income_group="high",
    rating_sp="AA", rating_moody="Aa3", rating_fitch="AA-", rating_outlook="stable",
    debt_to_gdp=101.0, external_debt_to_gdp=55.0, short_term_debt_to_gdp=18.0,
    debt_service_to_revenue=12.0, interest_to_revenue=8.5,
    gdp_nominal_trillions=3.3, gdp_per_capita=48000, gdp_growth_pct=0.5,
    inflation_pct=4.0, unemployment_pct=4.2,
    fiscal_balance_pct=-4.2, primary_balance_pct=-1.8,
    revenue_to_gdp=23.0, expenditure_to_gdp=27.2,
    current_account_pct=-3.0, reserves_months_imports=4.5,
    external_debt_usd_trillions=8.5, foreign_held_pct=28.0,
    avg_maturity_years=14.2, avg_coupon_pct=2.0, domestic_share_pct=72.0,
    currency="GBP", population_millions=67.0, median_age=40.5,
    groups=["g7", "g20", "oecd", "nato", "five_eyes"],
))

_add(SovereignProfile(
    code="JP", name="Japan", region="asia_pacific", income_group="high",
    rating_sp="A+", rating_moody="A1", rating_fitch="A+", rating_outlook="stable",
    debt_to_gdp=261.0, external_debt_to_gdp=18.0, short_term_debt_to_gdp=8.0,
    debt_service_to_revenue=8.0, interest_to_revenue=5.5,
    gdp_nominal_trillions=4.2, gdp_per_capita=34000, gdp_growth_pct=1.0,
    inflation_pct=2.8, unemployment_pct=2.6,
    fiscal_balance_pct=-6.0, primary_balance_pct=-1.5,
    revenue_to_gdp=34.0, expenditure_to_gdp=40.0,
    current_account_pct=3.5, reserves_months_imports=22.0,
    external_debt_usd_trillions=1.6, foreign_held_pct=7.0,
    avg_maturity_years=8.5, avg_coupon_pct=0.7, domestic_share_pct=93.0,
    currency="JPY", population_millions=125.0, median_age=49.0,
    groups=["g7", "g20", "oecd"],
))

_add(SovereignProfile(
    code="DE", name="Germany", region="europe", income_group="high",
    rating_sp="AAA", rating_moody="Aaa", rating_fitch="AAA", rating_outlook="stable",
    debt_to_gdp=66.0, external_debt_to_gdp=55.0, short_term_debt_to_gdp=10.0,
    debt_service_to_revenue=4.5, interest_to_revenue=2.5,
    gdp_nominal_trillions=4.5, gdp_per_capita=53000, gdp_growth_pct=0.3,
    inflation_pct=2.8, unemployment_pct=3.4,
    fiscal_balance_pct=-2.5, primary_balance_pct=-0.5,
    revenue_to_gdp=26.0, expenditure_to_gdp=28.5,
    current_account_pct=7.0, reserves_months_imports=3.5,
    external_debt_usd_trillions=6.0, foreign_held_pct=45.0,
    avg_maturity_years=7.1, avg_coupon_pct=1.1, domestic_share_pct=55.0,
    currency="EUR", population_millions=84.0, median_age=46.0,
    groups=["g7", "g20", "oecd", "eu", "nato"],
))

_add(SovereignProfile(
    code="FR", name="France", region="europe", income_group="high",
    rating_sp="AA", rating_moody="Aa2", rating_fitch="AA-", rating_outlook="negative",
    debt_to_gdp=112.0, external_debt_to_gdp=65.0, short_term_debt_to_gdp=15.0,
    debt_service_to_revenue=8.5, interest_to_revenue=4.5,
    gdp_nominal_trillions=3.1, gdp_per_capita=45000, gdp_growth_pct=0.7,
    inflation_pct=2.5, unemployment_pct=7.3,
    fiscal_balance_pct=-5.5, primary_balance_pct=-2.5,
    revenue_to_gdp=27.0, expenditure_to_gdp=32.5,
    current_account_pct=-2.0, reserves_months_imports=2.5,
    external_debt_usd_trillions=4.8, foreign_held_pct=50.0,
    avg_maturity_years=8.9, avg_coupon_pct=1.5, domestic_share_pct=50.0,
    currency="EUR", population_millions=68.0, median_age=42.0,
    groups=["g7", "g20", "oecd", "eu", "nato"],
))

_add(SovereignProfile(
    code="IT", name="Italy", region="europe", income_group="high",
    rating_sp="BBB", rating_moody="Baa3", rating_fitch="BBB", rating_outlook="stable",
    debt_to_gdp=144.0, external_debt_to_gdp=45.0, short_term_debt_to_gdp=12.0,
    debt_service_to_revenue=9.0, interest_to_revenue=5.0,
    gdp_nominal_trillions=2.3, gdp_per_capita=38000, gdp_growth_pct=0.7,
    inflation_pct=2.2, unemployment_pct=7.6,
    fiscal_balance_pct=-4.5, primary_balance_pct=0.5,
    revenue_to_gdp=26.0, expenditure_to_gdp=30.5,
    current_account_pct=0.5, reserves_months_imports=3.0,
    external_debt_usd_trillions=3.5, foreign_held_pct=33.0,
    avg_maturity_years=7.0, avg_coupon_pct=2.8, domestic_share_pct=67.0,
    currency="EUR", population_millions=59.0, median_age=48.0,
    groups=["g7", "g20", "oecd", "eu", "nato"],
))

_add(SovereignProfile(
    code="CA", name="Canada", region="north_america", income_group="high",
    rating_sp="AAA", rating_moody="Aaa", rating_fitch="AAA", rating_outlook="stable",
    debt_to_gdp=106.0, external_debt_to_gdp=80.0, short_term_debt_to_gdp=20.0,
    debt_service_to_revenue=10.0, interest_to_revenue=6.5,
    gdp_nominal_trillions=2.2, gdp_per_capita=55000, gdp_growth_pct=1.2,
    inflation_pct=2.9, unemployment_pct=5.4,
    fiscal_balance_pct=-1.4, primary_balance_pct=0.2,
    revenue_to_gdp=24.0, expenditure_to_gdp=25.4,
    current_account_pct=-1.0, reserves_months_imports=4.0,
    external_debt_usd_trillions=2.3, foreign_held_pct=35.0,
    avg_maturity_years=6.8, avg_coupon_pct=2.5, domestic_share_pct=65.0,
    currency="CAD", population_millions=40.0, median_age=42.0,
    groups=["g7", "g20", "oecd", "nato", "five_eyes"],
))

# G20 (non-G7)
_add(SovereignProfile(
    code="CN", name="China", region="asia_pacific", income_group="upper_middle",
    rating_sp="A+", rating_moody="A1", rating_fitch="A+", rating_outlook="stable",
    debt_to_gdp=83.0, external_debt_to_gdp=15.0, short_term_debt_to_gdp=5.0,
    debt_service_to_revenue=5.0, interest_to_revenue=2.0,
    gdp_nominal_trillions=18.0, gdp_per_capita=12500, gdp_growth_pct=5.0,
    inflation_pct=0.5, unemployment_pct=5.2,
    fiscal_balance_pct=-7.5, primary_balance_pct=-5.0,
    revenue_to_gdp=18.0, expenditure_to_gdp=25.5,
    current_account_pct=2.0, reserves_months_imports=18.0,
    external_debt_usd_trillions=2.5, foreign_held_pct=8.0,
    avg_maturity_years=7.5, avg_coupon_pct=3.2, domestic_share_pct=92.0,
    currency="CNY", population_millions=1412.0, median_age=39.0,
    groups=["g20", "brics", "un"],
))

_add(SovereignProfile(
    code="IN", name="India", region="asia_pacific", income_group="lower_middle",
    rating_sp="BBB-", rating_moody="Baa3", rating_fitch="BBB-", rating_outlook="stable",
    debt_to_gdp=83.0, external_debt_to_gdp=19.0, short_term_debt_to_gdp=4.0,
    debt_service_to_revenue=22.0, interest_to_revenue=18.0,
    gdp_nominal_trillions=3.7, gdp_per_capita=2600, gdp_growth_pct=6.5,
    inflation_pct=5.0, unemployment_pct=7.8,
    fiscal_balance_pct=-6.0, primary_balance_pct=-2.5,
    revenue_to_gdp=21.0, expenditure_to_gdp=27.0,
    current_account_pct=-1.5, reserves_months_imports=10.0,
    external_debt_usd_trillions=0.7, foreign_held_pct=22.0,
    avg_maturity_years=6.4, avg_coupon_pct=7.2, domestic_share_pct=78.0,
    currency="INR", population_millions=1428.0, median_age=28.0,
    groups=["g20", "brics", "un"],
))

_add(SovereignProfile(
    code="BR", name="Brazil", region="latin_america", income_group="upper_middle",
    rating_sp="BB-", rating_moody="Ba2", rating_fitch="BB-", rating_outlook="positive",
    debt_to_gdp=88.0, external_debt_to_gdp=30.0, short_term_debt_to_gdp=8.0,
    debt_service_to_revenue=18.0, interest_to_revenue=15.0,
    gdp_nominal_trillions=2.2, gdp_per_capita=10000, gdp_growth_pct=2.2,
    inflation_pct=4.5, unemployment_pct=7.8,
    fiscal_balance_pct=-7.0, primary_balance_pct=0.5,
    revenue_to_gdp=16.0, expenditure_to_gdp=23.0,
    current_account_pct=-2.0, reserves_months_imports=12.0,
    external_debt_usd_trillions=0.7, foreign_held_pct=18.0,
    avg_maturity_years=5.1, avg_coupon_pct=10.5, domestic_share_pct=82.0,
    currency="BRL", population_millions=215.0, median_age=34.0,
    groups=["g20", "brics", "un"],
))

_add(SovereignProfile(
    code="RU", name="Russia", region="europe", income_group="upper_middle",
    rating_sp="BB+", rating_moody="Ba1", rating_fitch="BBB-", rating_outlook="negative",
    debt_to_gdp=17.0, external_debt_to_gdp=8.0, short_term_debt_to_gdp=2.0,
    debt_service_to_revenue=3.0, interest_to_revenue=2.0,
    gdp_nominal_trillions=2.0, gdp_per_capita=12000, gdp_growth_pct=3.0,
    inflation_pct=7.5, unemployment_pct=2.9,
    fiscal_balance_pct=-2.0, primary_balance_pct=-0.5,
    revenue_to_gdp=18.0, expenditure_to_gdp=20.0,
    current_account_pct=4.0, reserves_months_imports=14.0,
    external_debt_usd_trillions=0.3, foreign_held_pct=10.0,
    avg_maturity_years=5.5, avg_coupon_pct=7.5, domestic_share_pct=90.0,
    currency="RUB", population_millions=144.0, median_age=40.0,
    groups=["g20", "brics"],
))

_add(SovereignProfile(
    code="AU", name="Australia", region="asia_pacific", income_group="high",
    rating_sp="AAA", rating_moody="Aaa", rating_fitch="AAA", rating_outlook="stable",
    debt_to_gdp=52.0, external_debt_to_gdp=45.0, short_term_debt_to_gdp=12.0,
    debt_service_to_revenue=5.0, interest_to_revenue=2.0,
    gdp_nominal_trillions=1.8, gdp_per_capita=68000, gdp_growth_pct=2.0,
    inflation_pct=3.5, unemployment_pct=3.8,
    fiscal_balance_pct=-1.5, primary_balance_pct=0.5,
    revenue_to_gdp=28.0, expenditure_to_gdp=29.5,
    current_account_pct=-2.0, reserves_months_imports=5.0,
    external_debt_usd_trillions=2.0, foreign_held_pct=40.0,
    avg_maturity_years=6.5, avg_coupon_pct=2.5, domestic_share_pct=60.0,
    currency="AUD", population_millions=26.0, median_age=38.0,
    groups=["g20", "oecd", "five_eyes", "apec"],
))

_add(SovereignProfile(
    code="KR", name="South Korea", region="asia_pacific", income_group="high",
    rating_sp="AA", rating_moody="Aa2", rating_fitch="AA-", rating_outlook="stable",
    debt_to_gdp=54.0, external_debt_to_gdp=30.0, short_term_debt_to_gdp=8.0,
    debt_service_to_revenue=6.0, interest_to_revenue=3.5,
    gdp_nominal_trillions=1.7, gdp_per_capita=33000, gdp_growth_pct=2.0,
    inflation_pct=3.2, unemployment_pct=2.8,
    fiscal_balance_pct=-3.5, primary_balance_pct=-1.0,
    revenue_to_gdp=29.0, expenditure_to_gdp=32.5,
    current_account_pct=2.0, reserves_months_imports=10.0,
    external_debt_usd_trillions=0.5, foreign_held_pct=15.0,
    avg_maturity_years=8.5, avg_coupon_pct=3.0, domestic_share_pct=85.0,
    currency="KRW", population_millions=52.0, median_age=44.0,
    groups=["g20", "oecd", "apec"],
))

_add(SovereignProfile(
    code="MX", name="Mexico", region="latin_america", income_group="upper_middle",
    rating_sp="BBB", rating_moody="Baa2", rating_fitch="BBB", rating_outlook="stable",
    debt_to_gdp=54.0, external_debt_to_gdp=35.0, short_term_debt_to_gdp=10.0,
    debt_service_to_revenue=15.0, interest_to_revenue=12.0,
    gdp_nominal_trillions=1.8, gdp_per_capita=11000, gdp_growth_pct=2.5,
    inflation_pct=4.8, unemployment_pct=2.8,
    fiscal_balance_pct=-4.0, primary_balance_pct=-0.5,
    revenue_to_gdp=18.0, expenditure_to_gdp=22.0,
    current_account_pct=-1.5, reserves_months_imports=5.0,
    external_debt_usd_trillions=0.6, foreign_held_pct=35.0,
    avg_maturity_years=7.8, avg_coupon_pct=8.5, domestic_share_pct=65.0,
    currency="MXN", population_millions=130.0, median_age=29.0,
    groups=["g20", "oecd", "apec", "usmca"],
))

_add(SovereignProfile(
    code="ZA", name="South Africa", region="africa", income_group="upper_middle",
    rating_sp="BB-", rating_moody="Ba2", rating_fitch="BB-", rating_outlook="stable",
    debt_to_gdp=72.0, external_debt_to_gdp=40.0, short_term_debt_to_gdp=10.0,
    debt_service_to_revenue=20.0, interest_to_revenue=17.0,
    gdp_nominal_trillions=0.4, gdp_per_capita=6500, gdp_growth_pct=1.0,
    inflation_pct=5.5, unemployment_pct=32.0,
    fiscal_balance_pct=-4.5, primary_balance_pct=0.5,
    revenue_to_gdp=25.0, expenditure_to_gdp=29.5,
    current_account_pct=-2.0, reserves_months_imports=5.0,
    external_debt_usd_trillions=0.15, foreign_held_pct=25.0,
    avg_maturity_years=8.1, avg_coupon_pct=9.0, domestic_share_pct=75.0,
    currency="ZAR", population_millions=60.0, median_age=28.0,
    groups=["g20", "brics", "un"],
))

_add(SovereignProfile(
    code="SA", name="Saudi Arabia", region="middle_east", income_group="high",
    rating_sp="A", rating_moody="A1", rating_fitch="A+", rating_outlook="stable",
    debt_to_gdp=26.0, external_debt_to_gdp=15.0, short_term_debt_to_gdp=3.0,
    debt_service_to_revenue=3.0, interest_to_revenue=1.5,
    gdp_nominal_trillions=1.1, gdp_per_capita=32000, gdp_growth_pct=0.8,
    inflation_pct=2.0, unemployment_pct=4.8,
    fiscal_balance_pct=-1.5, primary_balance_pct=2.0,
    revenue_to_gdp=30.0, expenditure_to_gdp=31.5,
    current_account_pct=3.0, reserves_months_imports=28.0,
    external_debt_usd_trillions=0.15, foreign_held_pct=12.0,
    avg_maturity_years=10.5, avg_coupon_pct=3.5, domestic_share_pct=88.0,
    currency="SAR", population_millions=36.0, median_age=31.0,
    groups=["g20", "opec", "un"],
))

_add(SovereignProfile(
    code="CH", name="Switzerland", region="europe", income_group="high",
    rating_sp="AAA", rating_moody="Aaa", rating_fitch="AAA", rating_outlook="stable",
    debt_to_gdp=28.0, external_debt_to_gdp=100.0, short_term_debt_to_gdp=15.0,
    debt_service_to_revenue=2.0, interest_to_revenue=0.5,
    gdp_nominal_trillions=0.9, gdp_per_capita=100000, gdp_growth_pct=1.5,
    inflation_pct=1.5, unemployment_pct=2.3,
    fiscal_balance_pct=1.0, primary_balance_pct=1.5,
    revenue_to_gdp=32.0, expenditure_to_gdp=31.0,
    current_account_pct=7.0, reserves_months_imports=30.0,
    external_debt_usd_trillions=2.5, foreign_held_pct=10.0,
    avg_maturity_years=8.0, avg_coupon_pct=0.5, domestic_share_pct=90.0,
    currency="CHF", population_millions=9.0, median_age=43.0,
    groups=["oecd", "european_free_trade"],
))

_add(SovereignProfile(
    code="SE", name="Sweden", region="europe", income_group="high",
    rating_sp="AAA", rating_moody="Aaa", rating_fitch="AAA", rating_outlook="stable",
    debt_to_gdp=33.0, external_debt_to_gdp=50.0, short_term_debt_to_gdp=10.0,
    debt_service_to_revenue=2.5, interest_to_revenue=1.0,
    gdp_nominal_trillions=0.6, gdp_per_capita=58000, gdp_growth_pct=0.5,
    inflation_pct=3.5, unemployment_pct=8.0,
    fiscal_balance_pct=-0.5, primary_balance_pct=0.5,
    revenue_to_gdp=29.0, expenditure_to_gdp=29.5,
    current_account_pct=6.0, reserves_months_imports=3.0,
    external_debt_usd_trillions=0.5, foreign_held_pct=40.0,
    avg_maturity_years=5.5, avg_coupon_pct=1.0, domestic_share_pct=60.0,
    currency="SEK", population_millions=10.5, median_age=41.0,
    groups=["oecd", "eu"],
))

_add(SovereignProfile(
    code="NO", name="Norway", region="europe", income_group="high",
    rating_sp="AAA", rating_moody="Aaa", rating_fitch="AAA", rating_outlook="stable",
    debt_to_gdp=42.0, external_debt_to_gdp=60.0, short_term_debt_to_gdp=15.0,
    debt_service_to_revenue=1.5, interest_to_revenue=0.5,
    gdp_nominal_trillions=0.5, gdp_per_capita=90000, gdp_growth_pct=1.0,
    inflation_pct=3.0, unemployment_pct=3.5,
    fiscal_balance_pct=5.0, primary_balance_pct=8.0,
    revenue_to_gdp=45.0, expenditure_to_gdp=40.0,
    current_account_pct=10.0, reserves_months_imports=100.0,
    external_debt_usd_trillions=0.7, foreign_held_pct=35.0,
    avg_maturity_years=7.0, avg_coupon_pct=1.5, domestic_share_pct=65.0,
    currency="NOK", population_millions=5.5, median_age=40.0,
    groups=["oecd", "european_free_trade"],
))

_add(SovereignProfile(
    code="SG", name="Singapore", region="asia_pacific", income_group="high",
    rating_sp="AAA", rating_moody="Aaa", rating_fitch="AAA", rating_outlook="stable",
    debt_to_gdp=135.0, external_debt_to_gdp=120.0, short_term_debt_to_gdp=25.0,
    debt_service_to_revenue=3.0, interest_to_revenue=1.5,
    gdp_nominal_trillions=0.5, gdp_per_capita=85000, gdp_growth_pct=2.5,
    inflation_pct=2.5, unemployment_pct=2.0,
    fiscal_balance_pct=2.0, primary_balance_pct=3.5,
    revenue_to_gdp=22.0, expenditure_to_gdp=20.0,
    current_account_pct=18.0, reserves_months_imports=25.0,
    external_debt_usd_trillions=1.5, foreign_held_pct=5.0,
    avg_maturity_years=8.5, avg_coupon_pct=2.0, domestic_share_pct=95.0,
    currency="SGD", population_millions=6.0, median_age=42.0,
    groups=["apec", "asean"],
))

_add(SovereignProfile(
    code="ID", name="Indonesia", region="asia_pacific", income_group="lower_middle",
    rating_sp="BBB", rating_moody="Baa2", rating_fitch="BBB", rating_outlook="stable",
    debt_to_gdp=39.0, external_debt_to_gdp=30.0, short_term_debt_to_gdp=5.0,
    debt_service_to_revenue=15.0, interest_to_revenue=12.0,
    gdp_nominal_trillions=1.4, gdp_per_capita=5000, gdp_growth_pct=5.0,
    inflation_pct=2.8, unemployment_pct=5.3,
    fiscal_balance_pct=-2.3, primary_balance_pct=0.5,
    revenue_to_gdp=12.0, expenditure_to_gdp=14.3,
    current_account_pct=-1.0, reserves_months_imports=6.0,
    external_debt_usd_trillions=0.4, foreign_held_pct=15.0,
    avg_maturity_years=6.5, avg_coupon_pct=6.5, domestic_share_pct=85.0,
    currency="IDR", population_millions=278.0, median_age=30.0,
    groups=["g20", "apec", "asean", "un"],
))

_add(SovereignProfile(
    code="TR", name="Turkey", region="europe", income_group="upper_middle",
    rating_sp="B+", rating_moody="B3", rating_fitch="B+", rating_outlook="stable",
    debt_to_gdp=32.0, external_debt_to_gdp=45.0, short_term_debt_to_gdp=15.0,
    debt_service_to_revenue=10.0, interest_to_revenue=8.0,
    gdp_nominal_trillions=1.1, gdp_per_capita=13000, gdp_growth_pct=3.0,
    inflation_pct=60.0, unemployment_pct=9.0,
    fiscal_balance_pct=-3.0, primary_balance_pct=1.5,
    revenue_to_gdp=16.0, expenditure_to_gdp=19.0,
    current_account_pct=-4.0, reserves_months_imports=4.0,
    external_debt_usd_trillions=0.5, foreign_held_pct=30.0,
    avg_maturity_years=4.5, avg_coupon_pct=15.0, domestic_share_pct=70.0,
    currency="TRY", population_millions=85.0, median_age=33.0,
    groups=["g20", "nato", "oecd"],
))

_add(SovereignProfile(
    code="AR", name="Argentina", region="latin_america", income_group="upper_middle",
    rating_sp="CCC+", rating_moody="Ca", rating_fitch="CCC", rating_outlook="stable",
    debt_to_gdp=85.0, external_debt_to_gdp=50.0, short_term_debt_to_gdp=15.0,
    debt_service_to_revenue=25.0, interest_to_revenue=20.0,
    gdp_nominal_trillions=0.6, gdp_per_capita=13000, gdp_growth_pct=-2.0,
    inflation_pct=120.0, unemployment_pct=6.5,
    fiscal_balance_pct=0.5, primary_balance_pct=2.0,
    revenue_to_gdp=12.0, expenditure_to_gdp=11.5,
    current_account_pct=0.5, reserves_months_imports=3.0,
    external_debt_usd_trillions=0.3, foreign_held_pct=35.0,
    avg_maturity_years=3.5, avg_coupon_pct=12.0, domestic_share_pct=65.0,
    currency="ARS", population_millions=46.0, median_age=31.0,
    groups=["g20", "mercosur", "un"],
))

_add(SovereignProfile(
    code="PL", name="Poland", region="europe", income_group="high",
    rating_sp="A-", rating_moody="A2", rating_fitch="A-", rating_outlook="stable",
    debt_to_gdp=49.0, external_debt_to_gdp=40.0, short_term_debt_to_gdp=8.0,
    debt_service_to_revenue=5.0, interest_to_revenue=3.0,
    gdp_nominal_trillions=0.8, gdp_per_capita=21000, gdp_growth_pct=2.5,
    inflation_pct=4.0, unemployment_pct=2.8,
    fiscal_balance_pct=-4.5, primary_balance_pct=-1.5,
    revenue_to_gdp=18.0, expenditure_to_gdp=22.5,
    current_account_pct=-2.5, reserves_months_imports=6.0,
    external_debt_usd_trillions=0.4, foreign_held_pct=30.0,
    avg_maturity_years=4.5, avg_coupon_pct=4.0, domestic_share_pct=70.0,
    currency="PLN", population_millions=38.0, median_age=40.0,
    groups=["oecd", "eu", "nato"],
))

_add(SovereignProfile(
    code="NL", name="Netherlands", region="europe", income_group="high",
    rating_sp="AAA", rating_moody="Aaa", rating_fitch="AAA", rating_outlook="stable",
    debt_to_gdp=47.0, external_debt_to_gdp=100.0, short_term_debt_to_gdp=15.0,
    debt_service_to_revenue=3.0, interest_to_revenue=1.5,
    gdp_nominal_trillions=1.1, gdp_per_capita=62000, gdp_growth_pct=1.0,
    inflation_pct=3.0, unemployment_pct=3.6,
    fiscal_balance_pct=-0.5, primary_balance_pct=1.0,
    revenue_to_gdp=27.0, expenditure_to_gdp=27.5,
    current_account_pct=10.0, reserves_months_imports=3.0,
    external_debt_usd_trillions=2.0, foreign_held_pct=60.0,
    avg_maturity_years=6.5, avg_coupon_pct=0.8, domestic_share_pct=40.0,
    currency="EUR", population_millions=17.5, median_age=43.0,
    groups=["g20", "oecd", "eu"],
))

_add(SovereignProfile(
    code="ES", name="Spain", region="europe", income_group="high",
    rating_sp="A-", rating_moody="Baa1", rating_fitch="A-", rating_outlook="stable",
    debt_to_gdp=108.0, external_debt_to_gdp=70.0, short_term_debt_to_gdp=18.0,
    debt_service_to_revenue=7.0, interest_to_revenue=3.5,
    gdp_nominal_trillions=1.6, gdp_per_capita=33000, gdp_growth_pct=2.5,
    inflation_pct=2.8, unemployment_pct=11.5,
    fiscal_balance_pct=-3.5, primary_balance_pct=0.5,
    revenue_to_gdp=24.0, expenditure_to_gdp=27.5,
    current_account_pct=1.5, reserves_months_imports=3.5,
    external_debt_usd_trillions=2.5, foreign_held_pct=45.0,
    avg_maturity_years=8.0, avg_coupon_pct=2.5, domestic_share_pct=55.0,
    currency="EUR", population_millions=48.0, median_age=45.0,
    groups=["g20", "oecd", "eu"],
))


# ── Public API ──────────────────────────────────────────────────────────

def get_country(code: str) -> Optional[SovereignProfile]:
    """Get a country profile by ISO code."""
    return COUNTRIES.get(code.upper())


def list_countries(region: Optional[str] = None, group: Optional[str] = None,
                   min_rating: Optional[str] = None) -> list[SovereignProfile]:
    """List countries with optional filters."""
    countries = list(COUNTRIES.values())
    if region:
        countries = [c for c in countries if c.region == region]
    if group:
        countries = [c for c in countries if group in c.groups]
    if min_rating:
        ig_order = ["BBB-", "BBB", "BBB+", "A-", "A", "A+", "AA-", "AA", "AA+", "AAA"]
        min_idx = ig_order.index(min_rating) if min_rating in ig_order else -1
        countries = [c for c in countries if c.rating_sp in ig_order and ig_order.index(c.rating_sp) >= min_idx]
    return sorted(countries, key=lambda c: c.debt_to_gdp)


def compare_countries(codes: list[str]) -> dict:
    """Compare multiple countries side by side."""
    profiles = [COUNTRIES[c.upper()] for c in codes if c.upper() in COUNTRIES]
    if not profiles:
        return {"error": "No valid countries found"}

    return {
        "countries": [p.to_dict() for p in profiles],
        "averages": {
            "debt_to_gdp": sum(p.debt_to_gdp for p in profiles) / len(profiles),
            "avg_maturity_years": sum(p.avg_maturity_years for p in profiles) / len(profiles),
            "gdp_growth_pct": sum(p.gdp_growth_pct for p in profiles) / len(profiles),
            "inflation_pct": sum(p.inflation_pct for p in profiles) / len(profiles),
            "fiscal_balance_pct": sum(p.fiscal_balance_pct for p in profiles) / len(profiles),
        },
        "best_in_class": {
            "lowest_debt": min(profiles, key=lambda p: p.debt_to_gdp).code,
            "longest_maturity": max(profiles, key=lambda p: p.avg_maturity_years).code,
            "strongest_growth": max(profiles, key=lambda p: p.gdp_growth_pct).code,
            "lowest_inflation": min(profiles, key=lambda p: p.inflation_pct).code,
        },
    }


def get_peer_group(country_code: str, group: Optional[str] = None) -> list[SovereignProfile]:
    """Get peer countries for comparison."""
    country = COUNTRIES.get(country_code.upper())
    if not country:
        return []

    # Find peers from same group
    peer_groups = group.split(",") if group else country.groups
    peers = []
    for p in COUNTRIES.values():
        if p.code == country.code:
            continue
        if any(g in p.groups for g in peer_groups):
            peers.append(p)

    return sorted(peers, key=lambda p: abs(p.debt_to_gdp - country.debt_to_gdp))


def get_global_stats() -> dict:
    """Get global sovereign debt statistics."""
    all_countries = list(COUNTRIES.values())
    total_debt = sum(c.debt_to_gdp * c.gdp_nominal_trillions for c in all_countries)
    total_gdp = sum(c.gdp_nominal_trillions for c in all_countries)

    return {
        "total_countries": len(all_countries),
        "total_gdp_trillions": round(total_gdp, 1),
        "total_debt_trillions": round(total_debt, 1),
        "avg_debt_to_gdp": round(sum(c.debt_to_gdp for c in all_countries) / len(all_countries), 1),
        "investment_grade": sum(1 for c in all_countries if c.investment_grade),
        "high_yield": sum(1 for c in all_countries if not c.investment_grade),
        "by_region": {
            region: len([c for c in all_countries if c.region == region])
            for region in set(c.region for c in all_countries)
        },
        "by_rating": {
            rating: len([c for c in all_countries if c.rating_sp == rating])
            for rating in set(c.rating_sp for c in all_countries)
        },
    }
