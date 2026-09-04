"""Cyber risk module for the National Risk Operating System."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CyberVulnerability(BaseModel):
    """A cyber vulnerability affecting government systems or critical infrastructure."""

    id: str = Field(..., description="Unique vulnerability identifier")
    name: str = Field(..., description="Human-readable vulnerability name")
    cve_id: Optional[str] = Field(None, description="Common Vulnerabilities and Exposures ID")
    cvss_score: Optional[float] = Field(
        None, ge=0, le=10, description="Common Vulnerability Scoring System score"
    )
    affected_systems: List[str] = Field(
        default_factory=list, description="System identifiers affected"
    )
    exploitation_vector: str = Field(
        ..., description="How the vulnerability can be exploited (e.g., network, local, physical)"
    )
    exploitation_status: str = Field(
        default="unknown",
        description="Status: unknown, proof_of_concept, actively_exploited",
    )
    patch_available: bool = Field(default=False, description="Whether a patch or mitigation exists")
    affected_assets: List[str] = Field(
        default_factory=list, description="Critical asset identifiers"
    )
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    severity: str = Field(
        default="medium",
        description="Severity: low, medium, high, critical",
    )
    asset_criticality: str = Field(
        default="medium",
        description="Criticality of affected asset: low, medium, high, essential",
    )
    targeted_sector: str = Field(
        default="government",
        description="Targeted sector: government, energy, finance, health, transport",
    )


class CyberThreat(BaseModel):
    """A cyber threat actor or campaign targeting government entities."""

    id: str = Field(..., description="Unique threat identifier")
    name: str = Field(..., description="Threat actor or campaign name")
    threat_type: str = Field(
        ...,
        description="Type: state_sponsored, criminal, hacktivist, insider",
    )
    target_governments: List[str] = Field(
        default_factory=list, description="Targeted government identifiers"
    )
    target_systems: List[str] = Field(
        default_factory=list, description="Targeted system identifiers"
    )
    activity_level: str = Field(
        default="monitoring",
        description="Activity level: dormant, monitoring, active, escalating",
    )
    last_activity: Optional[datetime] = Field(None, description="Last observed activity")
    indicators_of_compromise: List[str] = Field(
        default_factory=list, description="IOC hashes, IPs, domains"
    )
    motivation: str = Field(
        default="ideological",
        description="Motivation: financial, ideological, espionage, disruption",
    )
    severity: str = Field(default="medium", description="Severity: low, medium, high, critical")
    confidence: float = Field(
        ge=0, le=1, description="Intelligence confidence (0.0 to 1.0)"
    )
    origin_country: Optional[str] = Field(
        None, description="Origin country code of the threat actor"
    )
    target_country: Optional[str] = Field(
        None, description="Target country code"
    )


class CyberRisk(BaseModel):
    """Overall cyber risk assessment for a government or portfolio."""

    id: str = Field(..., description="Unique risk assessment identifier")
    entity_id: str = Field(..., description="Government or portfolio identifier")
    entity_type: str = Field(
        default="government",
        description="Entity type: government, portfolio, agency",
    )
    overall_score: float = Field(
        ge=0, le=100, description="Composite cyber risk score (0-100)"
    )
    vulnerability_score: float = Field(
        ge=0, le=100, description="Weighted vulnerability exposure (0-100)"
    )
    threat_score: float = Field(
        ge=0, le=100, description="Active threat landscape score (0-100)"
    )
    resilience_score: float = Field(
        ge=0, le=100, description="Defensive posture resilience (0-100)"
    )
    last_assessed: datetime = Field(default_factory=datetime.utcnow)
    vulnerabilities: List[CyberVulnerability] = Field(
        default_factory=list
    )
    active_threats: List[CyberThreat] = Field(
        default_factory=list
    )
    risk_factors: Dict[str, float] = Field(
        default_factory=dict, description="Component scores by factor"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Top remediation recommendations"
    )
    assessment_standards: List[str] = Field(
        default_factory=list, description="Frameworks used (e.g., NIST, ISO27001)"
    )
    related_contagion_ids: List[str] = Field(
        default_factory=list, description="Related contagion risk assessment IDs"
    )
    related_liquidity_ids: List[str] = Field(
        default_factory=list, description="Related liquidity risk assessment IDs"
    )


class CyberRiskSummary(BaseModel):
    """Summary view for dashboard display."""

    risk_id: str
    overall_score: float
    threat_level: str  # low, medium, high, critical
    active_threats_count: int
    critical_vulnerabilities: int
    last_assessed: datetime
    trending: str  # improving, stable, deteriorating
    related_risk_count: int