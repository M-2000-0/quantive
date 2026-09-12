#!/usr/bin/env python3
"""Batch-import the fixed n8n workflows into a local n8n instance.

Configuration (set via environment variables or edit below):
    N8N_URL      - n8n base URL (default: http://localhost:5678)
    N8N_API_KEY  - n8n API key (default: empty = no auth)
    N8N_SIMPLE    - set to 1 to use n8n's simple-mock auth (dev mode)
    DRY_RUN      - set to 1 to validate locally without calling n8n API

The workflows are read from:
    ~/OneDrive/Desktop/uncomplete workflows/*.json

Usage:
    python import_to_n8n.py
    N8N_URL=http://192.168.1.50:5678 N8N_API_KEY=abc123 python import_to_n8n.py
    DRY_RUN=1 python import_to_n8n.py          # validate only, no API calls
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── config ────────────────────────────────────────────────────────────────

N8N_URL = os.environ.get("N8N_URL", "http://localhost:5678").rstrip("/")
N8N_API_KEY = os.environ.get("N8N_API_KEY", "")
N8N_SIMPLE = os.environ.get("N8N_SIMPLE", "0") == "1"
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"

WORKFLOW_DIR = Path(os.path.expanduser("~/OneDrive/Desktop/uncomplete workflows"))

if not N8N_API_KEY and not N8N_SIMPLE:
    print("WARNING: N8N_API_KEY not set. If your n8n requires auth, imports will fail.")
    print("         Set N8N_API_KEY or N8N_SIMPLE=1 (dev mode).")
    print()


# ── helpers ────────────────────────────────────────────────────────────────

def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if N8N_API_KEY:
        h["X-API-Key"] = N8N_API_KEY
    if N8N_SIMPLE:
        h["Authorization"] = "Bearer simple"  # n8n simple-auth dev mode
    return h


def _n8n_import(wf_path: Path) -> tuple[str | None, int, str]:
    """POST a single workflow JSON to n8n /api/workflows.

    Returns (workflow_id, http_status, message).
    On dry-run, returns ('dry-run', 0, 'simulated').
    """
    if DRY_RUN:
        with open(wf_path, encoding="utf-8") as f:
            data = json.load(f)
        node_count = len(data.get("nodes", []))
        return ("dry-run", 0, f"would import {node_count} nodes"), 0, ""

    with open(wf_path, encoding="utf-8") as f:
        data = json.load(f)

    payload = json.dumps([data]).encode("utf-8")
    req = urllib.request.Request(
        f"{N8N_URL}/api/workflows",
        data=payload,
        headers=_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read())
            if isinstance(body, list) and body:
                wf = body[0]
                return wf.get("id"), resp.status, wf.get("name", wf_path.name)
            # some n8n versions return a single object
            return body.get("id"), resp.status, body.get("name", wf_path.name)
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")[:300]
        return None, e.code, f"HTTP {e.code}: {msg}"
    except Exception as e:
        return None, 0, f"Connection error: {e}"


# ── main ───────────────────────────────────────────────────────────────────

def main() -> None:
    if not WORKFLOW_DIR.exists():
        print(f"Workflow directory not found: {WORKFLOW_DIR}")
        print("Expected: ~/OneDrive/Desktop/uncomplete workflows/")
        sys.exit(1)

    files = sorted(f for f in WORKFLOW_DIR.glob("*.json") if not f.name.startswith("backup"))
    if not files:
        print(f"No workflow files found in {WORKFLOW_DIR}")
        sys.exit(1)

    print(f"n8n target : {N8N_URL}")
    print(f"auth       : {'API key' if N8N_API_KEY else 'none' + (' (simple-auth)' if N8N_SIMPLE else '')}")
    print(f"dry_run    : {DRY_RUN}")
    print(f"workflows  : {len(files)}")
    print()

    summary: dict[str, int] = {"ok": 0, "fail": 0}
    details: list[tuple[str, bool, str]] = []

    for wf_path in files:
        wf_id, status, msg = _n8n_import(wf_path)
        if DRY_RUN:
            ok = True
            wf_id = f"dry-run:{wf_path.stem}"
            msg = f"would import {len(json.loads(wf_path.read_text(encoding='utf-8')).get('nodes', []))} nodes"
        else:
            ok = 200 <= status < 300
        summary["ok" if ok else "fail"] += 1
        tag = "OK  " if ok else "FAIL"
        extra = f"id={wf_id}" if wf_id and ok else ""
        print(f"[{tag}] {wf_path.name:40s}  {status or '--':>3}  {msg}  {extra}")
        details.append((wf_path.name, ok, msg))

    print()
    print(f"Results: {summary['ok']}/{len(files)} imported successfully", end="")
    if summary["fail"]:
        print(f", {summary['fail']} failed")
    else:
        print()

    if DRY_RUN:
        print("\nDRY_RUN mode — no API calls were made.")
        print("Remove DRY_RUN=1 to actually import into n8n.")

    # Print config hints if everything failed
    if summary["fail"] == len(files) and not DRY_RUN:
        print()
        print("All imports failed. Check:")
        print(f"  1. Is n8n running at {N8N_URL}?")
        print("  2. Is the API key correct? (N8N_API_KEY)")
        print("  3. Try N8N_SIMPLE=1 if using n8n dev/simple auth mode")
        print("  4. Is there a firewall blocking the connection?")


if __name__ == "__main__":
    main()
