"""Procurement mode — Pillar 4.

Build procurement assets from day one so Quantive wins government contracts:
security package, architecture diagrams, compliance matrix, DR plan, accessibility report.

Many projects fail due to procurement readiness, not technical capability.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal


@dataclass
class ComplianceItem:
    control: str
    standard: str            # NIST, ISO 27001, SOC2, GDPR...
    status: Literal["implemented", "partial", "planned", "not_applicable"]
    evidence: str = ""
    notes: str = ""


@dataclass
class ProcurementAsset:
    """A deliverable used in a government RFP/RFI response."""
    asset_id: str
    asset_type: Literal[
        "architecture_diagram",
        "security_package",
        "compliance_matrix",
        "disaster_recovery_plan",
        "accessibility_report",
        "data_residency_statement",
        "supply_chain_disclosure",
        "sf_form",
    ]
    title: str
    status: Literal["ready", "in_progress", "draft", "needs_review"]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    content: dict = field(default_factory=dict)
    related_standards: list[str] = field(default_factory=list)


class ProcurementEngine:
    """Generates and tracks procurement-ready assets for government sales."""

    def __init__(self) -> None:
        self._assets: dict[str, ProcurementAsset] = {}
        self._compliance: list[ComplianceItem] = []

    def add_compliance_item(self, item: ComplianceItem) -> None:
        self._compliance.append(item)

    def compliance_matrix(self) -> list[dict]:
        """Export full compliance matrix — what we meet against each standard."""
        return [
            {
                "control": c.control,
                "standard": c.standard,
                "status": c.status,
                "evidence": c.evidence,
                "notes": c.notes,
            }
            for c in self._compliance
        ]

    def compliance_readiness(self) -> dict:
        """Overall compliance readiness score (0-100 by standard)."""
        from collections import defaultdict
        by_standard: dict[str, list[ComplianceItem]] = defaultdict(list)
        for c in self._compliance:
            by_standard[c.standard].append(c)

        result = {}
        for standard, items in by_standard.items():
            implemented = sum(1 for c in items if c.status == "implemented")
            partial = sum(1 for c in items if c.status == "partial")
            total = len(items)
            score = (implemented + 0.5 * partial) / total if total else 0
            result[standard] = round(score * 100, 1)
        return result

    def register_asset(self, asset: ProcurementAsset) -> ProcurementAsset:
        self._assets[asset.asset_id] = asset
        return asset

    def get_asset(self, asset_id: str) -> ProcurementAsset | None:
        return self._assets.get(asset_id)

    def list_assets(self, asset_type: str | None = None) -> list[ProcurementAsset]:
        if asset_type:
            return [a for a in self._assets.values() if a.asset_type == asset_type]
        return list(self._assets.values())

    def build_security_package(self, *, provider_id: str) -> ProcurementAsset:
        """Pillar 5: security package — the critical RFP deliverable."""
        return ProcurementAsset(
            asset_id=f"sec-{provider_id}",
            asset_type="security_package",
            title=f"Security Package — {provider_id}",
            status="ready",
            related_standards=["NIST SP 800-53", "ISO 27001", "SOC 2 Type II"],
            content={
                "encryption": {
                    "at_rest": "AES-256",
                    "in_transit": "TLS 1.3",
                    "key_management": "HSM / KMS",
                },
                "authentication": {
                    "mfa": True,
                    "hardware_keys": True,
                    "session_management": True,
                },
                "zero_trust": {
                    "microsegmentation": True,
                    "identity_aware_proxies": True,
                    "continuous_verification": True,
                },
                "audit": {
                    "immutable_logs": True,
                    "tamper_evidence": True,
                    "retention": "10 years",
                },
                "vulnerability": {
                    "scan_frequency_days": 7,
                    "patching_sla_days": 7,
                    "pen_test_frequency_years": 1,
                },
            },
        )

    def build_disaster_recovery_plan(self, *, provider_id: str) -> ProcurementAsset:
        """Pillar 4/5: DR plan with RTO/RPO."""
        return ProcurementAsset(
            asset_id=f"dr-{provider_id}",
            asset_type="disaster_recovery_plan",
            title=f"Disaster Recovery Plan — {provider_id}",
            status="ready",
            content={
                "rpo_minutes": 5,
                "rto_hours": 2,
                "backup_frequency": "continuous",
                "backup_locations": ["primary", "geo-redundant"],
                "failover": "automated",
                "tested": True,
                "test_frequency": "quarterly",
                "data_residency": "in-country primary",
            },
        )

    def build_accessibility_report(self, *, provider_id: str) -> ProcurementAsset:
        """Pillar 4/7: accessibility (WCAG)."""
        return ProcurementAsset(
            asset_id=f"a11y-{provider_id}",
            asset_type="accessibility_report",
            title=f"Accessibility Report — {provider_id}",
            status="ready",
            content={
                "standard": "WCAG 2.2 AA",
                "keyboard_navigable": True,
                "screen_reader_support": True,
                "contrast_ratio": ">= 4.5:1",
                "focus_indicators": True,
                "color_blind_safe": True,
                "forms_labeled": True,
                "remediation_sla_days": 14,
            },
        )

    def build_architecture_diagram(self, *, provider_id: str, layers: list[str] | None = None) -> ProcurementAsset:
        """Pillar 4: architecture diagram (textual/structured since no frontend)."""
        return ProcurementAsset(
            asset_id=f"arch-{provider_id}",
            asset_type="architecture_diagram",
            title=f"Architecture — {provider_id}",
            status="ready",
            content={
                "layers": layers or ["UI", "API Gateway", "Services", "Models", "Data", "Security"],
                "zero_trust_boundaries": True,
                "three_layer_ai": True,  # Data → Models → AI Explanation
                "separation_of_duties": True,
                "scalability": "100 countries / millions records / thousands users",
            },
        )

    def procurement_readiness_score(self) -> int:
        """0-100: are we ready to win government contracts?"""
        asset_types_needed = ["security_package", "architecture_diagram", "compliance", "disaster_recovery_plan", "accessibility_report"]
        present = set()
        for a in self._assets.values():
            present.add(a.asset_type)
        # compliance readiness
        comp_ready = self.compliance_readiness()
        avg_comp = sum(comp_ready.values()) / len(comp_ready) if comp_ready else 0
        score = (len(present) / len(asset_types_needed)) * 70 + (avg_comp / 100) * 30
        return int(round(score))
