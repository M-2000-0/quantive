"""Risk enums for the National Risk Operating System."""

from __future__ import annotations

from enum import Enum


class ConflictType(str, Enum):
    """Types of geopolitical conflict or tension."""

    MILITARY_CONFLICT = "military_conflict"
    TRADE_WAR = "trade_war"
    DIPLOMATIC_TENSION = "diplomatic_tension"
    SANCTIONS = "sanctions"
    BORDER_DISPUTE = "border_dispute"
    INFLUENCE_COMPETITION = "influence_competition"
    IDEOLOGICAL_CONFLICT = "ideological_conflict"


class DisruptionType(str, Enum):
    """Types of supply chain disruptions."""

    PORT_CONGESTION = "port_congestion"
    TRANSPORT_DISABLED = "transport_disabled"
    RAW_MATERIAL_SHORTAGE = "raw_material_shortage"
    MANUFACTURING_OUTAGE = "manufacturing_outage"
    LOGISTICS_ROUTE_BLOCKED = "logistics_route_blocked"
    SINGLE_SUPPLIER_FAILURE = "single_supplier_failure"
    GEOPOLITICAL_INTERDICTION = "geopolitical_interdiction"
    CYBER_SUPPLY_CHAIN = "cyber_supply_chain"
    NATURAL_DISASTER = "natural_disaster"
    DEMAND_SPIKE = "demand_spike"


class TierLevel(str, Enum):
    """Tier level of supply chain dependency."""

    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"
    TIER_4_PLUS = "tier_4+"


class RiskCategory(str, Enum):
    """Risk category for classification and filtering."""

    CYBER = "cyber"
    FISCAL = "fiscal"
    CLIMATE = "climate"
    INFRASTRUCTURE = "infrastructure"
    GEOPOLITICAL = "geopolitical"
    SUPPLY_CHAIN = "supply_chain"
    CONTAGION = "contagion"
    LIQUIDITY = "liquidity"
    NATIONAL = "national"


class RiskSeverity(str, Enum):
    """Risk severity level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrendDirection(str, Enum):
    """Trend direction for risk indicators."""

    IMPROVING = "improving"
    STABLE = "stable"
    DETERIORATING = "deteriorating"