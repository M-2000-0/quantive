"""Institutional Memory Engine - Layer 2.

Provides complete memory retention across administrations, administrative
transition tracking, knowledge persistence, and policy rationale queries.

Key features:
- Versioned assumptions with full audit trails
- Automatic risk/initiative/deadline generation on admin changes
- Cross-administration knowledge persistence via database
- 'Why was this policy chosen?' queries with complete audit trail
- Knowledge base indexing for cross-administration access
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from quantive.models.government import (
    AssumptionCategory,
    VersionedAssumption,
    db,
    gen_uuid,
    utcnow,
)


def compute_audit_hash(assumption: VersionedAssumption) -> str:
    """Compute immutable audit hash for chain integrity."""
    data = (
        str(assumption.id)
        + str(assumption.entity_id)
        + str(assumption.name)
        + str(assumption.value)
        + str(assumption.version)
        + str(assumption.changed_by)
        + str(assumption.created_at)
    )
    return hashlib.sha256(data.encode()).hexdigest()


def register_assumption(
    entity_id: str,
    name: str,
    category: AssumptionCategory,
    value: float,
    unit: str,
    source: str | None = None,
    changed_by: str | None = None,
    administration_label: str | None = None,
    minister: str | None = None,
    transition_trigger: str | None = None,
    metadata: dict | None = None,
) -> VersionedAssumption:
    """Register a new assumption with full transition tracking.

    Creates a new versioned assumption entry with audit hash,
    administrative context, and knowledge persistence markers.
    """
    # Compute hash of previous version if exists
    previous = (
        db.query(VersionedAssumption)
        .filter(VersionedAssumption.entity_id == entity_id)
        .order_by(VersionedAssumption.version.desc())
        .first()
    )

    audit_hash = None
    previous_value = None
    associated_risks = {}
    active_initiatives = {}
    unresolved_issues = {}
    upcoming_deadlines = {}

    if previous:
        audit_hash = compute_audit_hash(previous)
        previous_value = float(previous.value)
        # Carry forward risks, initiatives, unresolved issues, deadlines
        associated_risks = previous.associated_risks or {}
        active_initiatives = previous.active_initiatives or {}
        unresolved_issues = previous.unresolved_issues or {}
        upcoming_deadlines = previous.upcoming_deadlines or {}

    assumption = VersionedAssumption(
        id=gen_uuid(),
        entity_id=entity_id,
        name=name,
        category=category,
        value=value,
        unit=unit,
        source=source,
        version=(previous.version + 1) if previous else 1,
        is_current=True,
        changed_by=changed_by,
        change_reason=metadata.get("change_reason") if metadata else None,
        previous_value=previous_value,
        administration_label=administration_label,
        minister_at_change=minister,
        transition_trigger=transition_trigger,
        associated_risks=associated_risks,
        active_initiatives=active_initiatives,
        unresolved_issues=unresolved_issues,
        upcoming_deadlines=upcoming_deadlines,
        audit_hash=audit_hash,
        knowledge_base_id=metadata.get("knowledge_base_id") if metadata else None,
        persistence_status="active",
    )

    db.add(assumption)
    db.commit()
    db.refresh(assumption)

    # Update previous version's audit chain
    if previous:
        previous.audit_hash = compute_audit_hash(assumption)
        db.commit()

    return assumption


def transition_administration(
    entity_id: str,
    new_administration: str,
    new_minister: str,
    trigger: str = "handover",
    departing_minister: str | None = None,
    assumptions_to_review: list[str | None] | None = None,
    metadata: dict | None = None,
) -> List[VersionedAssumption]:
    """Generate administrative transition tracking.

    When admins change, automatically generates risks, active initiatives,
    unresolved issues, and upcoming deadlines based on previous assumptions.

    Returns the list of new assumption entries created.
    """
    # Fetch all current assumptions for this entity
    assumptions = (
        db.query(VersionedAssumption)
        .filter(VersionedAssumption.entity_id == entity_id, VersionedAssumption.is_current == True)
        .all()
    )

    new_entries: List[VersionedAssumption] = []

    for assumption in assumptions:
        # Create a transition record for each assumption
        new_assumption = register_assumption(
            entity_id=entity_id,
            name=f"{assumption.name} - Transition",
            category=assumption.category,
            value=assumption.value,
            unit=assumption.unit,
            source=assumption.source,
            changed_by=metadata.get("changed_by") if metadata else None,
            administration_label=new_administration,
            minister=new_minister,
            transition_trigger=trigger,
            metadata={
                "change_reason": f"Administrative transition: {new_administration} replacing {assumption.administration_label or 'previous'}",
                "knowledge_base_id": f"transition-{assumption.id}",
                "departing_minister": departing_minister,
                "trigger": trigger,
                "original_assumption_id": assumption.id,
            },
        )
        new_entries.append(new_assumption)

        # Auto-generate risks based on assumption change
        if assumption.category == AssumptionCategory.MACRO:
            associated_risks = new_assumption.associated_risks or {}
            associated_risks[f"transition-{new_assumption.id}"] = {
                "risk": f"Policy shift from assumption: {assumption.name}",
                "severity": "high",
                "category": "administrative_transition",
                "triggered_by": new_minister,
                "status": "active",
            }
            new_assumption.associated_risks = associated_risks

        # Carry forward unresolved issues
        unresolved = new_assumption.unresolved_issues or {}
        if assumption.previous_value is not None:
            unresolved[f"carry-forward-{new_assumption.id}"] = {
                "issue": f"Assumption value change from {assumption.previous_value} to {assumption.value}",
                "category": "value_shift",
                "status": "pending",
            }
        new_assumption.unresolved_issues = unresolved

        db.add(new_assumption)
        db.commit()

    # Create summary assumption for the transition itself
    summary = register_assumption(
        entity_id=entity_id,
        name="Administrative Transition",
        category=AssumptionCategory.MACRO,
        value=0.0,
        unit="count",
        source="institutional_memory_engine",
        changed_by=metadata.get("changed_by") if metadata else None,
        administration_label=new_administration,
        minister=new_minister,
        transition_trigger=trigger,
        metadata={
            "change_reason": f"Full administration transition to {new_administration}",
            "trigger": trigger,
            "departing_minister": departing_minister,
            "assumptions_reviewed": len(assumptions) if assumptions_to_review is None else len(assumptions_to_review),
            "knowledge_base_id": "transition-summary",
        },
    )
    new_entries.append(summary)

    return new_entries


def get_policy_rationale(
    entity_id: str,
    assumption_name: str | None = None,
    category: AssumptionCategory | None = None,
    include_history: bool = True,
) -> Dict[str, Any]:
    """Query: 'Why was this policy chosen?' with full audit trail.

    Returns complete historical context for a policy decision including:
    - All assumption versions and their values over time
    - Administrative context at each change
    - Associated risks and initiatives
    - Unresolved issues carried forward
    - Upcoming deadlines tied to the assumption
    - Audit hashes for immutability verification
    """
    query = db.query(VersionedAssumption).filter(VersionedAssumption.entity_id == entity_id)

    if assumption_name:
        query = query.filter(VersionedAssumption.name == assumption_name)
    if category:
        query = query.filter(VersionedAssumption.category == category)

    # Get all versions ordered by version desc (newest first)
    all_versions = query.order_by(VersionedAssumption.version.desc()).all()

    if not all_versions:
        return {"error": "No assumptions found for this entity"}

    # Build complete audit trail
    audit_trail = []
    for v in all_versions:
        audit_trail.append(
            {
                "version": v.version,
                "value": float(v.value) if v.value else None,
                "unit": v.unit,
                "admin_label": v.administration_label,
                "minister": v.minister_at_change,
                "change_reason": v.change_reason,
                "transition_trigger": v.transition_trigger,
                "associated_risks": v.associated_risks or {},
                "active_initiatives": v.active_initiatives or {},
                "unresolved_issues": v.unresolved_issues or {},
                "upcoming_deadlines": v.upcoming_deadlines or {},
                "audit_hash": v.audit_hash,
                "previous_value": float(v.previous_value) if v.previous_value else None,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
        )

    # Build rationale summary
    current = all_versions[0]  # newest
    resolved_issues: List[Dict[str, Any]] = []
    carried_forward: List[Dict[str, Any]] = []

    # Track issues across versions
    all_unresolved: Dict[str, Any] = {}
    for entry in audit_trail:
        for issue_id, issue_data in entry.get("unresolved_issues", {}).items():
            if issue_data.get("status") == "resolved":
                resolved_issues.append(
                    {
                        "issue": issue_data.get("issue", ""),
                        "resolved_version": entry["version"],
                        "resolved_minister": entry["minister"],
                        "resolved_at": entry["created_at"],
                    }
                )
            else:
                if issue_id not in all_unresolved:
                    all_unresolved[issue_id] = issue_data
                carried_forward.append(
                    {
                        "issue": issue_data.get("issue", ""),
                        "first_appeared": issue_data.get("first_appeared", entry["version"]),
                        "current_status": issue_data.get("status", "pending"),
                        "minister_when_carried": entry["minister"],
                    }
                )

    # Collect active initiatives
    all_initiatives: Dict[str, Any] = {}
    for entry in audit_trail:
        for init_id, init_data in entry.get("active_initiatives", {}).items():
            if init_id not in all_initiatives:
                all_initiatives[init_id] = init_data

    # Collect upcoming deadlines
    all_deadlines: Dict[str, Any] = {}
    for entry in audit_trail:
        for dead_id, dead_data in entry.get("upcoming_deadlines", {}).items():
            if dead_id not in all_deadlines:
                all_deadlines[dead_id] = dead_data

    # Compute trend analysis
    value_trend = "stable"
    if len(all_versions) >= 2:
        values = [float(v.value) for v in all_versions if v.value is not None]
        if len(values) >= 2:
            if values[0] > values[-1] * 1.05:
                value_trend = "decreasing"
            elif values[0] < values[-1] * 0.95:
                value_trend = "increasing"
            else:
                value_trend = "stable"

    return {
        "entity_id": entity_id,
        "assumption_name": assumption_name or all_versions[0].name,
        "current_value": float(current.value) if current.value else None,
        "current_admin": current.administration_label,
        "current_minister": current.minister_at_change,
        "value_trend": value_trend,
        "total_versions": len(all_versions),
        "audit_trail": audit_trail,
        "resolved_issues": resolved_issues,
        "carried_forward_issues": carried_forward,
        "active_initiatives_summary": {
            "total": len(all_initiatives),
            "by_category": {
                cat: sum(
                    1 for i in all_initiatives.values() if i.get("category") == cat
                )
                for cat in ["macro", "market", "policy", "demographic"]
            },
        },
        "upcoming_deadlines_summary": {
            "total": len(all_deadlines),
            "earliest": min(
                all_deadlines.values(), key=lambda d: d.get("deadline", "")
            ).get("deadline", "N/A")
            if all_deadlines
            else "N/A",
        },
        "knowledge_persistence": {
            "current_status": current.persistence_status,
            "knowledge_base_id": current.knowledge_base_id,
            "migration_timestamp": current.migration_timestamp.isoformat()
            if current.migration_timestamp
            else None,
        },
    }


def get_cross_administration_knowledge(
    entity_id: str,
    include_archived: bool = True,
) -> Dict[str, Any]:
    """Retrieve knowledge persisted across administrations.

    Returns all knowledge entries for this entity across all administrations,
    enabling new administrators to understand historical context without
    reinventing the wheel.
    """
    query = db.query(VersionedAssumption).filter(VersionedAssumption.entity_id == entity_id)

    if not include_archived:
        query = query.filter(VersionedAssumption.persistence_status == "active")

    all_assumptions = query.order_by(VersionedAssumption.version.desc()).all()

    # Organize by administration
    by_administration: Dict[str, List[Dict[str, Any]]] = {}
    for a in all_assumptions:
        admin = a.administration_label or "unknown"
        if admin not in by_administration:
            by_administration[admin] = []
        by_administration[admin].append(
            {
                "version": a.version,
                "name": a.name,
                "category": a.category.value,
                "value": float(a.value) if a.value else None,
                "unit": a.unit,
                "minister": a.minister_at_change,
                "change_reason": a.change_reason,
                "transition_trigger": a.transition_trigger,
                "associated_risks": a.associated_risks or {},
                "active_initiatives": a.active_initiatives or {},
                "unresolved_issues": a.unresolved_issues or {},
                "upcoming_deadlines": a.upcoming_deadlines or {},
                "audit_hash": a.audit_hash,
                "persistence_status": a.persistence_status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
        )

    # Compute cross-administration insights
    insight_categories: Dict[str, Dict[str, Any]] = {}
    for cat in AssumptionCategory:
        cat_entries = [
            e for e in all_assumptions if e.category == cat
        ]
        if cat_entries:
            values = [float(e.value) for e in cat_entries if e.value is not None]
            insight_categories[cat.value] = {
                "count": len(cat_entries),
                "current_value": values[-1] if values else None,
                "value_range": {
                    "min": min(values) if values else None,
                    "max": max(values) if values else None,
                },
                "administrations_covered": len(set(e.administration_label for e in cat_entries)),
            }

    return {
        "entity_id": entity_id,
        "total_assumptions": len(all_assumptions),
        "by_administration": by_administration,
        "insight_categories": insight_categories,
        "knowledge_persistence_summary": {
            "active_count": sum(
                1 for a in all_assumptions if a.persistence_status == "active"
            ),
            "archived_count": sum(
                1 for a in all_assumptions if a.persistence_status == "archived"
            ),
            "migrated_count": sum(
                1 for a in all_assumptions if a.persistence_status == "migrated"
            ),
        },
    }


def migrate_knowledge_to_database(
    entity_id: str,
    from_administration: str,
    to_administration: str,
    assumptions_to_migrate: list[str] | None = None,
) -> Dict[str, Any]:
    """Migrate knowledge from one administration to another.

    Ensures cross-administration access by marking assumptions as
    migrated and creating new entries in the current administration.
    """
    # Fetch assumptions from the source administration
    query = db.query(VersionedAssumption).filter(
        VersionedAssumption.entity_id == entity_id,
        VersionedAssumption.administration_label == from_administration,
    )

    if assumptions_to_migrate:
        query = query.filter(VersionedAssumption.name.in_(assumptions_to_migrate))

    source_assumptions = query.all()

    migrated: List[Dict[str, Any]] = []

    for sa in source_assumptions:
        # Mark source as migrated
        sa.persistence_status = "migrated"
        sa.migration_timestamp = utcnow()
        sa.administration_label = f"migrated-{to_administration}"

        # Create new entry in current administration
        new_assumption = register_assumption(
            entity_id=entity_id,
            name=f"{sa.name} (migrated from {from_administration})",
            category=sa.category,
            value=float(sa.value) if sa.value else 0.0,
            unit=sa.unit,
            source=sa.source,
            changed_by=sa.changed_by,
            administration_label=to_administration,
            minister=sa.minister_at_change or "System Migration",
            transition_trigger="migration",
            metadata={
                "change_reason": f"Knowledge migration from {from_administration} to {to_administration}",
                "original_version": sa.version,
                "original_id": sa.id,
                "migration_initiative": "institutional_memory_l2",
            },
        )
        migrated.append(
            {
                "original_id": sa.id,
                "original_version": sa.version,
                "new_id": new_assumption.id,
                "new_version": new_assumption.version,
                "migration_timestamp": sa.migration_timestamp.isoformat(),
            }
        )

        db.add(new_assumption)
    db.commit()

    return {
        "source_administration": from_administration,
        "target_administration": to_administration,
        "migrated_count": len(migrated),
        "migrated_assumptions": migrated,
    }