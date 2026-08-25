"""Immutable Audit Trail — Tamper-Proof Logging for Government Compliance.

Every log entry is chained to the previous one using cryptographic hashes.
If anyone modifies a past entry, the entire chain breaks — making tampering
immediately detectable by auditors.

Architecture:
- Each log entry contains: data + timestamp + previous_hash
- SHA-256 hash of (data + previous_hash) = current_hash
- Verification walks the chain and recomputes hashes
- WORM-style append-only (no updates, no deletes)
- Exportable for SOC 2, ISO 27001, IMF compliance audits
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class AuditEntry:
    """A single immutable audit log entry."""
    index: int                  # Sequential position in chain
    timestamp: str              # ISO 8601
    event_type: str             # "login", "portfolio.create", "optimization.run", etc.
    actor_id: str               # User who performed the action
    actor_email: str
    org_id: str
    resource_type: str          # "portfolio", "optimization", "instrument", etc.
    resource_id: str
    action: str                 # "create", "read", "update", "delete", "execute"
    details: dict               # Arbitrary metadata
    ip_address: Optional[str]
    previous_hash: str          # Hash of the previous entry (genesis = "0")
    data_hash: str              # SHA-256 of this entry's data
    chain_hash: str             # SHA-256 of (data_hash + previous_hash)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "actor_email": self.actor_email,
            "org_id": self.org_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address,
            "previous_hash": self.previous_hash,
            "data_hash": self.data_hash,
            "chain_hash": self.chain_hash,
        }


class ImmutableAuditTrail:
    """Append-only, hash-chained audit log.

    Usage:
        trail = ImmutableAuditTrail()
        trail.append(event_type="portfolio.create", actor_id="user-123", ...)
        trail.append(event_type="optimization.run", actor_id="user-123", ...)

        # Verify integrity
        is_valid, broken_at = trail.verify()
        assert is_valid, f"Chain broken at index {broken_at}"
    """

    def __init__(self):
        self._entries: list[AuditEntry] = []
        self._genesis_hash = "0" * 64  # SHA-256 of nothing = genesis block

    def append(
        self,
        event_type: str,
        actor_id: str,
        actor_email: str,
        org_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> AuditEntry:
        """Append a new entry to the immutable chain."""
        index = len(self._entries)
        timestamp = datetime.now(timezone.utc).isoformat()
        previous_hash = self._entries[-1].chain_hash if self._entries else self._genesis_hash

        # Build data payload (everything except hashes)
        data_payload = {
            "index": index,
            "timestamp": timestamp,
            "event_type": event_type,
            "actor_id": actor_id,
            "actor_email": actor_email,
            "org_id": org_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "details": details or {},
            "ip_address": ip_address,
            "previous_hash": previous_hash,
        }

        # Compute hashes
        data_str = json.dumps(data_payload, sort_keys=True, default=str)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()
        chain_hash = hashlib.sha256(f"{data_hash}{previous_hash}".encode()).hexdigest()

        entry = AuditEntry(
            index=index,
            timestamp=timestamp,
            event_type=event_type,
            actor_id=actor_id,
            actor_email=actor_email,
            org_id=org_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
            ip_address=ip_address,
            previous_hash=previous_hash,
            data_hash=data_hash,
            chain_hash=chain_hash,
        )

        self._entries.append(entry)
        return entry

    def verify(self) -> tuple[bool, Optional[int]]:
        """Verify the entire chain integrity.

        Returns:
            (True, None) if chain is valid
            (False, index) if chain is broken at given index
        """
        prev_hash = self._genesis_hash

        for i, entry in enumerate(self._entries):
            # Verify previous hash links correctly
            if entry.previous_hash != prev_hash:
                return False, i

            # Recompute data hash
            data_payload = {
                "index": entry.index,
                "timestamp": entry.timestamp,
                "event_type": entry.event_type,
                "actor_id": entry.actor_id,
                "actor_email": entry.actor_email,
                "org_id": entry.org_id,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "action": entry.action,
                "details": entry.details,
                "ip_address": entry.ip_address,
                "previous_hash": entry.previous_hash,
            }
            data_str = json.dumps(data_payload, sort_keys=True, default=str)
            expected_data_hash = hashlib.sha256(data_str.encode()).hexdigest()

            if entry.data_hash != expected_data_hash:
                return False, i

            # Recompute chain hash
            expected_chain_hash = hashlib.sha256(
                f"{entry.data_hash}{entry.previous_hash}".encode()
            ).hexdigest()
            if entry.chain_hash != expected_chain_hash:
                return False, i

            prev_hash = entry.chain_hash

        return True, None

    def get_entries(
        self,
        org_id: Optional[str] = None,
        event_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        """Query entries with optional filters."""
        entries = self._entries

        if org_id:
            entries = [e for e in entries if e.org_id == org_id]
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]
        if resource_type:
            entries = [e for e in entries if e.resource_type == resource_type]
        if actor_id:
            entries = [e for e in entries if e.actor_id == actor_id]

        return entries[offset:offset + limit]

    def get_chain_proof(self, index: int) -> dict:
        """Generate a cryptographic proof for a specific entry.

        Returns the entry plus its hash chain context so an auditor
        can independently verify it hasn't been tampered with.
        """
        if index < 0 or index >= len(self._entries):
            raise IndexError(f"Entry index {index} out of range")

        entry = self._entries[index]

        # Get neighbors for chain verification
        prev_entry = self._entries[index - 1] if index > 0 else None
        next_entry = self._entries[index + 1] if index < len(self._entries) - 1 else None

        return {
            "entry": entry.to_dict(),
            "chain_context": {
                "total_entries": len(self._entries),
                "genesis_hash": self._genesis_hash,
                "previous_entry_hash": prev_entry.chain_hash if prev_entry else self._genesis_hash,
                "next_entry_hash": next_entry.chain_hash if next_entry else None,
            },
            "verification": {
                "data_hash": entry.data_hash,
                "chain_hash": entry.chain_hash,
                "previous_hash": entry.previous_hash,
                "can_verify_independently": True,
            },
        }

    def export_for_audit(self, org_id: Optional[str] = None) -> dict:
        """Export the full chain in a format suitable for external auditors.

        Includes the chain, verification data, and summary statistics.
        """
        entries = self._entries
        if org_id:
            entries = [e for e in entries if e.org_id == org_id]

        is_valid, broken_at = self.verify()

        return {
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "chain_status": "VALID" if is_valid else f"BROKEN at index {broken_at}",
            "total_entries": len(entries),
            "genesis_hash": self._genesis_hash,
            "final_hash": entries[-1].chain_hash if entries else self._genesis_hash,
            "entries": [e.to_dict() for e in entries],
            "summary": {
                "unique_actors": len(set(e.actor_id for e in entries)),
                "unique_resources": len(set(f"{e.resource_type}:{e.resource_id}" for e in entries)),
                "event_types": list(set(e.event_type for e in entries)),
                "time_range": {
                    "first": entries[0].timestamp if entries else None,
                    "last": entries[-1].timestamp if entries else None,
                },
            },
            "verification_instructions": (
                "To verify: 1) Rebuild each entry's data_hash from its fields. "
                "2) Verify chain_hash = SHA256(data_hash + previous_hash). "
                "3) Check each entry's previous_hash matches the prior entry's chain_hash. "
                "4) Genesis hash should be '0' * 64."
            ),
        }

    @property
    def length(self) -> int:
        return len(self._entries)

    @property
    def last_hash(self) -> str:
        return self._entries[-1].chain_hash if self._entries else self._genesis_hash


# ── Module-level singleton (production would use database-backed version) ──

_global_trail = ImmutableAuditTrail()


def get_audit_trail() -> ImmutableAuditTrail:
    """Get the global audit trail instance."""
    return _global_trail


def log_audit_event(
    event_type: str,
    actor_id: str,
    actor_email: str,
    org_id: str,
    resource_type: str,
    resource_id: str,
    action: str,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> dict:
    """Convenience function to log an audit event."""
    trail = get_audit_trail()
    entry = trail.append(
        event_type=event_type,
        actor_id=actor_id,
        actor_email=actor_email,
        org_id=org_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        details=details,
        ip_address=ip_address,
    )
    return entry.to_dict()
