#!/bin/bash
# Dependency Security Scan for Quantive
# Run: bash scripts/dependency_scan.sh

set -e

echo "============================================="
echo "  Quantive Dependency Security Scan"
echo "============================================="
echo ""

# Check if pip-audit is installed
if ! python -m pip_audit --version > /dev/null 2>&1; then
    echo "[INFO] Installing pip-audit..."
    python -m pip install pip-audit -q
fi

echo "[1/2] Scanning installed packages for known vulnerabilities..."
python -m pip_audit --desc --format json 2>/dev/null | python -c "
import json, sys
data = json.load(sys.stdin)
vulns = data.get('dependencies', [])
found = [d for d in vulns if d.get('vulns')]
if found:
    print(f'\n[ALERT] {len(found)} packages with known vulnerabilities:\n')
    for pkg in found:
        print(f'  {pkg[\"name\"]} {pkg[\"version\"]}')
        for v in pkg.get('vulns', []):
            vid = v.get('id', 'unknown')
            fix = v.get('fix_versions', ['unknown'])
            print(f'    - {vid}: fix in {fix}')
    print()
    sys.exit(1)
else:
    print('[OK] No known vulnerabilities found in installed packages.')
    sys.exit(0)
" || echo "[WARN] Some vulnerabilities found — review above."

echo ""
echo "[2/2] Checking for outdated packages with security implications..."
python -m pip list --outdated --format json 2>/dev/null | python -c "
import json, sys
data = json.load(sys.stdin)
if data:
    print(f'[INFO] {len(data)} packages have updates available:')
    for pkg in data[:10]:
        print(f'  {pkg[\"name\"]}: {pkg[\"version\"]} -> {pkg[\"latest_version\"]}')
    if len(data) > 10:
        print(f'  ... and {len(data)-10} more')
else:
    print('[OK] All packages are up to date.')
" 2>/dev/null || echo "[INFO] pip list --outdated not available"

echo ""
echo "============================================="
echo "  Scan complete."
echo "============================================="
