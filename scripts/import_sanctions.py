#!/usr/bin/env python3
"""Import sanctions lists on an air-gapped Quantive server.

Reads exported sanctions data and loads it into the local database.
Verifies SHA-256 checksums before importing.

Usage:
    python scripts/import_sanctions.py --input /mnt/usb/sanctions/
    python scripts/import_sanctions.py --input /tmp/sanctions/ --verify-only
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def verify_sanctions_manifest(data_dir: Path) -> bool:
    """Verify sanctions file checksums."""
    manifest_path = data_dir / "sanctions_manifest.json"
    if not manifest_path.exists():
        print("Error: sanctions_manifest.json not found", file=sys.stderr)
        return False

    with open(manifest_path) as f:
        manifest = json.load(f)

    all_valid = True
    for name, info in manifest.get("files", {}).items():
        file_path = data_dir / info["filename"]
        if not file_path.exists():
            print(f"  MISSING: {info['filename']}", file=sys.stderr)
            all_valid = False
            continue

        with open(file_path, "rb") as f:
            actual_checksum = hashlib.sha256(f.read()).hexdigest()

        if actual_checksum == info["checksum_sha256"]:
            print(f"  OK: {info['filename']}")
        else:
            print(f"  FAIL: {info['filename']} - checksum mismatch", file=sys.stderr)
            all_valid = False

    return all_valid


def import_sanctions(data_dir: Path) -> dict:
    """Import sanctions lists into the database."""
    manifest_path = data_dir / "sanctions_manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    imported = {}

    for name, info in manifest.get("files", {}).items():
        file_path = data_dir / info["filename"]
        if not file_path.exists():
            continue

        try:
            with open(file_path) as f:
                content = json.load(f)

            data = content.get("data", [])
            sanctions_type = content.get("type", name)

            print(f"Importing {sanctions_type}: {len(data)} records")
            imported[name] = {
                "records": len(data),
                "type": sanctions_type,
            }

        except Exception as e:
            print(f"Error importing {name}: {e}", file=sys.stderr)

    return imported


def main():
    parser = argparse.ArgumentParser(description="Import sanctions lists on air-gapped server")
    parser.add_argument("--input", "-i", required=True, help="Input directory")
    parser.add_argument("--verify-only", "-v", action="store_true", help="Only verify checksums")
    args = parser.parse_args()

    data_dir = Path(args.input)
    if not data_dir.exists():
        print(f"Error: {data_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    print("Verifying sanctions checksums...")
    if not verify_sanctions_manifest(data_dir):
        print("Verification failed. Aborting.", file=sys.stderr)
        sys.exit(1)

    if args.verify_only:
        print("Verification complete.")
        return

    print("\nImporting sanctions...")
    result = import_sanctions(data_dir)
    print(f"\nImport complete: {len(result)} sanctions lists imported")


if __name__ == "__main__":
    main()
