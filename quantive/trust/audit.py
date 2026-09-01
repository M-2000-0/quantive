"""Immutable audit trail — Pillar 6, Pillar 5.

Append-only, tamper-evident log. Every action in Quantive must pass through here.
Chain of hashes ensures integrity: entry N's hash includes entry N-1's hash.
No user can create → approve → execute → hide the same action.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    CREATE = "create"
    APPROVE = "approve"
    REJECT = "reject"
    EXECUTE = "execute"
    MODIFY = "modify"
    DELETE = "delete"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"
    SETTINGS_CHANGE = "settings_change"
    OVERRIDE = "override"
    DATA_IMPORT = "data_import"


@dataclass(frozen=True)
class AuditEntry:
    """Single immutable audit record."""
    id: str
    timestamp: datetime
    actor: str
    action: ActionType
    target_type: str          # e.g. "portfolio", "optimization", "assumption"
    target_id: str            # e.g. "portfolio-abc123"
    details: dict = field(default_factory=dict)
    data_sources: list[str] = field(default_factory=list)
    previous_hash: str = ""   # hash of prior entry (chain)
    entry_hash: str = ""      # SHA-256 of this entry (computed after creation)


def _hash_entry(entry_dict: dict, previous_hash: str) -> str:
    """SHA-256 hash of entry contents + previous hash = chain integrity."""
    canonical = json.dumps(entry_dict, sort_keys=True, default=str) + previous_hash
    return hashlib.sha256(canonical.encode()).hexdigest()


class AuditTrail:
    """Append-only audit log with tamper-evident chain.

    In production: backed by append-only database / blockchain / WORM storage.
    Here: in-memory with hash chain for verification.
    """

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._index: dict[str, list[int]] = {}  # target_id → [entry indices]

    @property
    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    @property
    def count(self) -> int:
        return len(self._entries)

    def record(
        self,
        *,
        actor: str,
        action: ActionType,
        target_type: str,
        target_id: str,
        details: dict[str, Any] | None = None,
        data_sources: list[str] | None = None,
    ) -> AuditEntry:
        """Append a new entry. Never modifies previous entries."""
        entry_id = f"audit-{self.count:08d}"
        prev_hash = self._entries[-1].entry_hash if self._entries else "genesis"

        entry = AuditEntry(
            id=entry_id,
            timestamp=datetime.now(timezone.utc),
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
            data_sources=data_sources or [],
            previous_hash=prev_hash,
        )

        # compute hash after construction
        hash_dict = {
            "id": entry.id,
            "timestamp": entry.timestamp.isoformat(),
            "actor": entry.actor,
            "action": entry.action.value,
            "target_type": entry.target_type,
            "target_id": entry.target_id,
            "details": entry.details,
            "data_sources": entry.data_sources,
            "previous_hash": entry.previous_hash,
        }
        entry_hash = _hash_entry(hash_dict, prev_hash)

        # frozen dataclass — rebuild with hash
        entry = AuditEntry(
            id=entry.id,
            timestamp=entry.timestamp,
            actor=entry.actor,
            action=entry.action,
            target_type=entry.target_type,
            target_id=entry.target_id,
            details=entry.details,
            data_sources=entry.data_sources,
            previous_hash=entry.previous_hash,
            entry_hash=entry_hash,
        )

        self._entries.append(entry)
        idx = len(self._entries) - 1
        self._index.setdefault(target_id, []).append(idx)
        return entry

    def query(
        self,
        *,
        target_id: str | None = None,
        actor: str | None = None,
        action: ActionType | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[AuditEntry]:
        """Filter entries. All filters are AND-combined."""
        results = self._entries

        if target_id is not None:
            indices = self._index.get(target_id, [])
            results = [self._entries[i] for i in indices]

        if actor is not None:
            results = [e for e in results if e.actor == actor]

        if action is not None:
            results = [e for e in results if e.action == action]

        if since is not None:
            results = [e for e in results if e.timestamp >= since]

        if until is not None:
            results = [e for e in results if e.timestamp <= until]

        return results

    def verify_chain(self) -> bool:
        """Verify hash chain integrity. Returns False if any entry was tampered."""
        for i, entry in enumerate(self._entries):
            prev_hash = self._entries[i - 1].entry_hash if i > 0 else "genesis"
            if entry.previous_hash != prev_hash:
                return False

            hash_dict = {
                "id": entry.id,
                "timestamp": entry.timestamp.isoformat(),
                "actor": entry.actor,
                "action": entry.action.value,
                "target_type": entry.target_type,
                "target_id": entry.target_id,
                "details": entry.details,
                "data_sources": entry.data_sources,
                "previous_hash": entry.previous_hash,
            }
            expected_hash = _hash_entry(hash_dict, prev_hash)
            if entry.entry_hash != expected_hash:
                return False

        return True

    def separation_of_duty_violation(
        self,
        *,
        creator: str,
        approver: str,
        executor: str,
    ) -> str | None:
        """Pillar 6: No single person can create + approve + execute.
        Returns violation description or None if clean."""
        actors = {creator, approver, executor}
        if len(actors) < 3:
            return (
                f"Separation of duties violated: "
                f"creator={creator}, approver={approver}, executor={executor}. "
                f"All three roles must be held by different people."
            )
        return None
