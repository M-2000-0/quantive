"""Sovereign Debt Transparency Index scoring engine.

Evaluates countries on 8 dimensions of debt management transparency
and produces a composite score (0-100) with tier classification.

Methodology inspired by IMF SDDS, World Bank debt transparency standards,
and proprietary Quantive indicators.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Tier(str, Enum):
    LEADER = "leader"
    ADVANCED = "advanced"
    DEVELOPING = "developing"
    EMERGING = "emerging"
    LAGGARD = "laggard"


@dataclass
class CategoryScore:
    category: str
    score: float  # 0-100
    weight: float
    weighted_score: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class CountryAssessment:
    country_code: str
    country_name: str
    region: str
    income_group: str
    overall_score: float
    tier: Tier
    rank: int | None
    categories: list[CategoryScore]
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    data_sources: dict[str, Any]
    assessment_date: datetime


# Default category weights (sum = 1.0)
DEFAULT_WEIGHTS = {
    "disclosure": 0.20,       # Public debt reporting quality
    "data_access": 0.15,      # Availability of debt data
    "institutional": 0.15,    # DMO independence and capacity
    "reporting_freq": 0.12,   # Frequency of debt reports
    "audit_trail": 0.12,      # Audit and oversight mechanisms
    "digital_infra": 0.10,    # Digital debt management tools
    "compliance": 0.10,       # International standards adherence
    "stakeholder": 0.06,      # Parliamentary/public engagement
}


# Scoring criteria for each category (0-100 scale)
SCORING_CRITERIA = {
    "disclosure": {
        "debt_stock_publication": {"max_points": 25, "description": "Total debt stock published publicly"},
        "composition_breakdown": {"max_points": 25, "description": "Currency/instrument/maturity breakdown"},
        "contingent_liabilities": {"max_points": 25, "description": "Guarantees and CLs disclosed"},
        "debt_strategy_document": {"max_points": 25, "description": "Medium-term debt strategy published"},
    },
    "data_access": {
        "open_data_portal": {"max_points": 30, "description": "Dedicated debt data portal"},
        "bulk_download": {"max_points": 20, "description": "Machine-readable data downloads"},
        "historical_series": {"max_points": 25, "description": "Multi-year historical data available"},
        "real_time_updates": {"max_points": 25, "description": "Near-real-time debt updates"},
    },
    "institutional": {
        "dmo_independence": {"max_points": 30, "description": "Independent DMO with clear mandate"},
        "staff_capacity": {"max_points": 25, "description": "Professional debt management staff"},
        "risk_management": {"max_points": 25, "description": "Formal risk management framework"},
        "board_oversight": {"max_points": 20, "description": "Board/advisory committee oversight"},
    },
    "reporting_freq": {
        "monthly_reports": {"max_points": 30, "description": "Monthly debt bulletins"},
        "quarterly_reports": {"max_points": 25, "description": "Quarterly comprehensive reports"},
        "annual_reports": {"max_points": 25, "description": "Annual debt management report"},
        "ad_hoc_disclosure": {"max_points": 20, "description": "Ad-hoc material event disclosure"},
    },
    "audit_trail": {
        "external_audit": {"max_points": 30, "description": "Independent external audit"},
        "audit_report_publication": {"max_points": 25, "description": "Audit reports published"},
        "internal_controls": {"max_points": 25, "description": "Internal control framework"},
        "whistleblower_mechanism": {"max_points": 20, "description": "Fraud reporting mechanism"},
    },
    "digital_infra": {
        "debt管理系统": {"max_points": 30, "description": "Modern debt management system"},
        "automation_level": {"max_points": 25, "description": "Automated reporting and alerts"},
        "cyber_security": {"max_points": 25, "description": "Cybersecurity framework"},
        "business_continuity": {"max_points": 20, "description": "BCP/DR for debt operations"},
    },
    "compliance": {
        "sdds_compliance": {"max_points": 30, "description": "IMF SDDS subscriber"},
        "g20_data_gaps": {"max_points": 25, "description": "G20 data gaps initiative adoption"},
        "ipsas_adoption": {"max_points": 25, "description": "IPSAS accounting standards"},
        "bos_calls": {"max_points": 20, "description": "Banks and Offices statistical calls"},
    },
    "stakeholder": {
        "parliamentary_reporting": {"max_points": 30, "description": "Regular parliamentary briefings"},
        "public_consultation": {"max_points": 25, "description": "Public consultation on debt strategy"},
        "civil_society_access": {"max_points": 25, "description": "Civil society debt data access"},
        "media_engagement": {"max_points": 20, "description": "Proactive media communication"},
    },
}


class TransparencyIndexEngine:
    """Computes the Sovereign Debt Transparency Index."""

    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self._countries: dict[str, dict] = {}

    def register_country(self, country_code: str, data: dict) -> None:
        """Register country data for scoring."""
        self._countries[country_code] = data

    def score_category(self, category: str, scores: dict[str, float]) -> CategoryScore:
        """Score a single category based on sub-criteria scores."""
        criteria = SCORING_CRITERIA.get(category, {})
        total_points = 0
        max_points = 0
        details = {}

        for criterion, config in criteria.items():
            achieved = scores.get(criterion, 0)
            max_pts = config["max_points"]
            total_points += achieved
            max_points += max_pts
            details[criterion] = {
                "achieved": achieved,
                "max": max_pts,
                "percentage": round(achieved / max_pts * 100, 1) if max_pts > 0 else 0,
            }

        category_score = (total_points / max_points * 100) if max_points > 0 else 0
        weight = self.weights.get(category, 0)
        weighted_score = category_score * weight

        return CategoryScore(
            category=category,
            score=round(category_score, 1),
            weight=weight,
            weighted_score=round(weighted_score, 2),
            details=details,
        )

    def assess_country(self, country_data: dict) -> CountryAssessment:
        """Produce a full assessment for a single country."""
        categories = []
        for category in self.weights:
            cat_scores = country_data.get(category, {})
            categories.append(self.score_category(category, cat_scores))

        overall = sum(c.weighted_score for c in categories)
        tier = self._score_to_tier(overall)

        strengths = self._identify_strengths(categories)
        weaknesses = self._identify_weaknesses(categories)
        recommendations = self._generate_recommendations(categories)

        return CountryAssessment(
            country_code=country_data["country_code"],
            country_name=country_data["country_name"],
            region=country_data.get("region", "Unknown"),
            income_group=country_data.get("income_group", "Unknown"),
            overall_score=round(overall, 1),
            tier=tier,
            rank=None,
            categories=categories,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            data_sources=country_data.get("data_sources", {}),
            assessment_date=datetime.now(timezone.utc),
        )

    def rank_countries(self, assessments: list[CountryAssessment]) -> list[CountryAssessment]:
        """Rank all assessed countries and assign ranks/tiers."""
        sorted_list = sorted(assessments, key=lambda a: a.overall_score, reverse=True)
        for i, assessment in enumerate(sorted_list):
            assessment.rank = i + 1
            assessment.tier = self._score_to_tier(assessment.overall_score)
        return sorted_list

    def _score_to_tier(self, score: float) -> Tier:
        if score >= 80:
            return Tier.LEADER
        elif score >= 60:
            return Tier.ADVANCED
        elif score >= 40:
            return Tier.DEVELOPING
        elif score >= 20:
            return Tier.EMERGING
        else:
            return Tier.LAGGARD

    def _identify_strengths(self, categories: list[CategoryScore]) -> list[str]:
        strengths = []
        for cat in categories:
            if cat.score >= 80:
                strengths.append(f"Excellent {cat.category.replace('_', ' ')} framework")
            elif cat.score >= 60:
                strengths.append(f"Strong {cat.category.replace('_', ' ')} practices")
        return strengths

    def _identify_weaknesses(self, categories: list[CategoryScore]) -> list[str]:
        weaknesses = []
        for cat in categories:
            if cat.score < 40:
                weaknesses.append(f"Critical gaps in {cat.category.replace('_', ' ')}")
            elif cat.score < 60:
                weaknesses.append(f"Needs improvement in {cat.category.replace('_', ' ')}")
        return weaknesses

    def _generate_recommendations(self, categories: list[CategoryScore]) -> list[str]:
        recommendations = []
        for cat in categories:
            if cat.score < 50:
                category_name = cat.category.replace("_", " ")
                recommendations.append(
                    f"Prioritize {category_name} improvements - currently scoring {cat.score:.0f}/100"
                )
        return recommendations[:5]  # Top 5 recommendations

    def compute_global_stats(self, assessments: list[CountryAssessment]) -> dict:
        """Compute global statistics from all assessments."""
        if not assessments:
            return {}

        scores = [a.overall_score for a in assessments]
        tier_counts = {}
        for a in assessments:
            tier_counts[a.tier.value] = tier_counts.get(a.tier.value, 0) + 1

        region_scores = {}
        for a in assessments:
            if a.region not in region_scores:
                region_scores[a.region] = []
            region_scores[a.region].append(a.overall_score)

        return {
            "total_countries": len(assessments),
            "average_score": round(sum(scores) / len(scores), 1),
            "median_score": round(sorted(scores)[len(scores) // 2], 1),
            "highest_score": round(max(scores), 1),
            "lowest_score": round(min(scores), 1),
            "tier_distribution": tier_counts,
            "regional_averages": {
                region: round(sum(s) / len(s), 1)
                for region, s in region_scores.items()
            },
        }
