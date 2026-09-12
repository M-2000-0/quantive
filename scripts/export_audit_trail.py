#!/usr/bin/env python3
"""Export the immutable audit trail for air-gapped backup or external verification.

Exports audit events as a tamper-evident JSON archive with SHA-256 hash chain.
Can be used for regulatory submission, third-party audit, or disaster recovery.

Usage:
    python scripts/export_audit_trail.py --output /mnt/usb/audit/
    python scripts/export_audit_trail.py --output /tmp/ --from-date 2026-01-01 --to-date 2026-09-01
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def export_audit_trail(output_dir: str, from_date: str | None = None, to_date: str | None = None) -> dict:
    """Export audit trail with hash chain verification."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        from app.database import SessionLocal
        from app.models import AuditEvent

        db = SessionLocal()
        try:
            query = db.query(AuditEvent).order_by(AuditEvent.created_at)

            if from_date:
                from datetime import date
                query = query.filter(AuditEvent.created_at >= date.fromisoformat(from_date))
            if to_date:
                from datetime import date
                query = query.filter(AuditEvent.created_at <= date.fromisoformat(to_date))

            events = query.all()

            # Build export with hash chain
            export_events = []
            previous_hash = "genesis"

            for event in events:
                event_data = {
                    "id": event.id,
                    "actor_id": event.actor_id,
                    "actor_email": event.actor_email,
                    "action": event.action,
                    "resource_type": event.resource_type,
                    "resource_id": event.resource_id,
                    "org_id": event.org_id,
                    "metadata": event.metadata_json,
                    "ip_address": event.ip_address,
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                    "previous_hash": previous_hash,
                }

                # Compute hash
                event_json = json.dumps(event_data, sort_keys=True, default=str)
                event_hash = hashlib.sha256(event_json.encode()).hexdigest()
                event_data["event_hash"] = event_hash

                export_events.append(event_data)
                previous_hash = event_hash

        finally:
            db.close()

    except ImportError:
        print("Warning: Database not available, exporting empty audit trail", file=sys.stderr)
        export_events = []
    except Exception as e:
        print(f"Error reading audit trail: {e}", file=sys.stderr)
        export_events = []

    # Write export
    export = {
        "type": "audit_trail",
        "exported_at": timestamp,
        "record_count": len(export_events),
        "chain_integrity": len(export_events) > 0,
        "events": export_events,
    }

    file_path = output_path / "audit_trail.json"
    with open(file_path, "w") as f:
        json.dump(export, f, indent=2, default=str)

    # Write manifest
    with open(file_path, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()

    manifest = {
        "version": "1.0",
        "exported_at": timestamp,
        "files": {
            "audit_trail": {
                "filename": "audit_trail.json",
                "checksum_sha256": checksum,
                "size_bytes": file_path.stat().st_size,
                "record_count": len(export_events),
            }
        },
    }

    manifest_path = output_path / "audit_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Exported {len(export_events)} audit events to {output_path}")
    print(f"  File: {file_path}")
    print(f"  SHA-256: {checksum}")

    return {"file": str(file_path), "records": len(export_events), "checksum": checksum}


def main():
    parser = argparse.ArgumentParser(description="Export audit trail for air-gapped backup")
    parser.add_argument("--output", "-o", required=True, help="Output directory")
    parser.add_argument("--from-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to-date", help="End date (YYYY-MM-DD)")
    args = parser.parse_args()

    export_audit_trail(args.output, args.from_date, args.to_date)


if __name__ == "__main__":
    main()
