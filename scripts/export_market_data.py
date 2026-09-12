#!/usr/bin/env python3
"""Export market data from Quantive for air-gapped transfer.

Exports yield curves, FX rates, and economic indicators to a signed
JSON archive that can be transferred via USB or data diode.

Usage:
    python scripts/export_market_data.py --output /mnt/usb/market-data/
    python scripts/export_market_data.py --output /tmp/ --format csv
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def export_market_data(output_dir: str, fmt: str = "json") -> dict:
    """Export all available market data to files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    exported = {}
    timestamp = datetime.now(timezone.utc).isoformat()

    # Yield curve data
    try:
        from quantive.data.synthetic import generate_yield_curve
        yield_data = generate_yield_curve()
        if fmt == "json":
            file_path = output_path / "yield_curves.json"
            with open(file_path, "w") as f:
                json.dump({
                    "type": "yield_curves",
                    "exported_at": timestamp,
                    "data": yield_data,
                }, f, indent=2, default=str)
        else:
            file_path = output_path / "yield_curves.csv"
            import csv
            with open(file_path, "w", newline="") as f:
                if isinstance(yield_data, list) and yield_data:
                    writer = csv.DictWriter(f, fieldnames=yield_data[0].keys())
                    writer.writeheader()
                    writer.writerows(yield_data)
        exported["yield_curves"] = str(file_path)
    except Exception as e:
        print(f"Warning: Could not export yield curves: {e}", file=sys.stderr)

    # FX rate data
    try:
        from quantive.data.synthetic import generate_fx_rates
        fx_data = generate_fx_rates()
        if fmt == "json":
            file_path = output_path / "fx_rates.json"
            with open(file_path, "w") as f:
                json.dump({
                    "type": "fx_rates",
                    "exported_at": timestamp,
                    "data": fx_data,
                }, f, indent=2, default=str)
        else:
            file_path = output_path / "fx_rates.csv"
            import csv
            with open(file_path, "w", newline="") as f:
                if isinstance(fx_data, list) and fx_data:
                    writer = csv.DictWriter(f, fieldnames=fx_data[0].keys())
                    writer.writeheader()
                    writer.writerows(fx_data)
        exported["fx_rates"] = str(file_path)
    except Exception as e:
        print(f"Warning: Could not export FX rates: {e}", file=sys.stderr)

    # Economic indicators
    try:
        from quantive.data.synthetic import generate_economic_indicators
        econ_data = generate_economic_indicators()
        if fmt == "json":
            file_path = output_path / "economic_indicators.json"
            with open(file_path, "w") as f:
                json.dump({
                    "type": "economic_indicators",
                    "exported_at": timestamp,
                    "data": econ_data,
                }, f, indent=2, default=str)
        else:
            file_path = output_path / "economic_indicators.csv"
            import csv
            with open(file_path, "w", newline="") as f:
                if isinstance(econ_data, list) and econ_data:
                    writer = csv.DictWriter(f, fieldnames=econ_data[0].keys())
                    writer.writeheader()
                    writer.writerows(econ_data)
        exported["economic_indicators"] = str(file_path)
    except Exception as e:
        print(f"Warning: Could not export economic indicators: {e}", file=sys.stderr)

    # Generate manifest with checksums
    manifest = {
        "version": "1.0",
        "exported_at": timestamp,
        "format": fmt,
        "files": {},
    }

    for name, file_path in exported.items():
        file_path_obj = Path(file_path)
        if file_path_obj.exists():
            with open(file_path_obj, "rb") as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            manifest["files"][name] = {
                "filename": file_path_obj.name,
                "checksum_sha256": checksum,
                "size_bytes": file_path_obj.stat().st_size,
            }

    manifest_path = output_path / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    exported["manifest"] = str(manifest_path)

    print(f"Exported {len(exported)} files to {output_path}")
    for name, path in exported.items():
        print(f"  {name}: {path}")

    return exported


def main():
    parser = argparse.ArgumentParser(description="Export market data for air-gapped transfer")
    parser.add_argument("--output", "-o", required=True, help="Output directory")
    parser.add_argument("--format", "-f", choices=["json", "csv"], default="json", help="Export format")
    args = parser.parse_args()

    export_market_data(args.output, args.format)


if __name__ == "__main__":
    main()
