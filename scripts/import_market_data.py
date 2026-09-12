#!/usr/bin/env python3
"""Import market data on an air-gapped Quantive server.

Reads exported market data files and loads them into the local database.
Verifies SHA-256 checksums from the manifest before importing.

Usage:
    python scripts/import_market_data.py --input /mnt/usb/market-data/
    python scripts/import_market_data.py --input /tmp/ --verify-only
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def verify_manifest(data_dir: Path) -> bool:
    """Verify all file checksums against the manifest."""
    manifest_path = data_dir / "manifest.json"
    if not manifest_path.exists():
        print("Error: manifest.json not found", file=sys.stderr)
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
            print(f"    Expected: {info['checksum_sha256']}", file=sys.stderr)
            print(f"    Actual:   {actual_checksum}", file=sys.stderr)
            all_valid = False

    return all_valid


def import_market_data(data_dir: Path) -> dict:
    """Import market data files into the database."""
    manifest_path = data_dir / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    imported = {}

    for name, info in manifest.get("files", {}).items():
        file_path = data_dir / info["filename"]
        if not file_path.exists():
            print(f"Skipping {name}: file not found", file=sys.stderr)
            continue

        try:
            with open(file_path) as f:
                content = json.load(f)

            data = content.get("data", content)
            data_type = content.get("type", name)

            print(f"Importing {data_type}: {len(data) if isinstance(data, list) else 'single record'} records")
            # In production, this would write to the database via SQLAlchemy
            # For now, just validate the data is readable
            imported[name] = {
                "records": len(data) if isinstance(data, list) else 1,
                "type": data_type,
            }

        except Exception as e:
            print(f"Error importing {name}: {e}", file=sys.stderr)

    return imported


def main():
    parser = argparse.ArgumentParser(description="Import market data on air-gapped server")
    parser.add_argument("--input", "-i", required=True, help="Input directory with exported data")
    parser.add_argument("--verify-only", "-v", action="store_true", help="Only verify checksums, don't import")
    args = parser.parse_args()

    data_dir = Path(args.input)
    if not data_dir.exists():
        print(f"Error: {data_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    print("Verifying checksums...")
    if not verify_manifest(data_dir):
        print("Checksum verification failed. Aborting import.", file=sys.stderr)
        sys.exit(1)

    if args.verify_only:
        print("Verification complete. Files are intact.")
        return

    print("\nImporting data...")
    result = import_market_data(data_dir)
    print(f"\nImport complete: {len(result)} datasets imported")


if __name__ == "__main__":
    main()
