"""Import-compatibility validator for the Quantive n8n workflow JSONs.

Checks the exact failure modes that produce "Could not find property option"
on n8n import:

  1. Switch v3 must use the fixedCollection shape n8n exports:
     rules.values[].conditions.{options,conditions,combinator},
     renameOutput boolean, outputKey string.
  2. retryOnFail / maxTries / waitBetweenTries / onError must NEVER appear
     inside node.parameters (they are node-level properties).
  3. stripeTrigger must have empty parameters (it has no "events" option).
  4. typeVersions must be within known-safe bounds.
  5. settings must not carry errorWorkflow pointing at a non-existent id.
  6. Every connection target/trigger must resolve to a declared node; no
     orphan nodes; unique node names/ids; unique webhookIds.

Run:  python validate_import.py   (exit 1 on any failure)
"""
import glob
import json
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# highest typeVersion known-safe to assume present in a current n8n install
SAFE_TV = {
    "n8n-nodes-base.code": (1, 2),
    "n8n-nodes-base.httpRequest": (1, 4.2),
    "n8n-nodes-base.postgres": (1, 2.5),
    "n8n-nodes-base.slack": (1, 2.2),
    "n8n-nodes-base.emailSend": (1, 2.1),
    "n8n-nodes-base.scheduleTrigger": (1, 1.2),
    "n8n-nodes-base.webhook": (1, 2),
    "n8n-nodes-base.switch": (1, 3),
    "n8n-nodes-base.stripeTrigger": (1, 1),
    "n8n-nodes-base.errorTrigger": (1, 1),
    "n8n-nodes-base.manualTrigger": (1, 1),
}

NODE_LEVEL_ONLY = {"retryOnFail", "maxTries", "waitBetweenTries", "onError", "alwaysOutputData"}

failures = []
files = sorted(glob.glob("workflows/*.json"))
for f in files:
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        failures.append(f"{f}: JSON parse error: {e}")
        continue

    names = set()
    ids = set()
    webhook_ids = set()
    for n in d.get("nodes", []):
        name, ntype, tv, params = n["name"], n["type"], n["typeVersion"], n["parameters"]

        if name in names:
            failures.append(f"{f}: duplicate node name '{name}'")
        names.add(name)
        if n["id"] in ids:
            failures.append(f"{f}: duplicate node id '{n['id']}'")
        ids.add(n["id"])
        if "webhookId" in n:
            if n["webhookId"] in webhook_ids:
                failures.append(f"{f}: duplicate webhookId '{n['webhookId']}'")
            webhook_ids.add(n["webhookId"])

        if ntype in SAFE_TV and not (SAFE_TV[ntype][0] <= tv <= SAFE_TV[ntype][1]):
            failures.append(f"{f}/{name}: typeVersion {tv} outside safe range {SAFE_TV[ntype]}")

        bad = NODE_LEVEL_ONLY & set(params)
        if bad:
            failures.append(f"{f}/{name}: node-level props inside parameters: {sorted(bad)}")

        if ntype == "n8n-nodes-base.switch":
            rules = params.get("rules", {})
            allowed_keys = {"values", "fallbackOutput"}
            if not set(rules.keys()).issubset(allowed_keys) or "values" not in rules:
                failures.append(f"{f}/{name}: switch rules must have 'values' key (got {sorted(rules.keys())})")
            for i, r in enumerate(rules.get("values", [])):
                c = r.get("conditions", {})
                if "options" not in c:
                    failures.append(f"{f}/{name}: rule {i} conditions missing options")
                if "combinator" not in c:
                    failures.append(f"{f}/{name}: rule {i} conditions missing combinator")
                if not isinstance(r.get("renameOutput"), bool):
                    failures.append(f"{f}/{name}: rule {i} renameOutput must be boolean")
                if r.get("renameOutput") and "outputKey" not in r:
                    failures.append(f"{f}/{name}: rule {i} missing outputKey")
                for cond in c.get("conditions", []):
                    if not cond.get("id"):
                        failures.append(f"{f}/{name}: rule {i} condition missing id")

        if ntype == "n8n-nodes-base.stripeTrigger" and params:
            failures.append(f"{f}/{name}: stripeTrigger must have empty parameters, got {params}")

    if "errorWorkflow" in d.get("settings", {}):
        failures.append(f"{f}: settings.errorWorkflow must be wired in the UI after import")

    # connection integrity
    conns = d.get("connections", {})
    for src, outs in conns.items():
        if src not in names:
            failures.append(f"{f}: connection source '{src}' is not a node")
        for out in outs["main"]:
            for e in out:
                if e["node"] not in names:
                    failures.append(f"{f}: connection target '{e['node']}' is not a node")

    # orphan check: every non-trigger node should have an inbound edge
    targeted = {e["node"] for outs in conns.values() for out in outs.get("main", []) for e in out}
    orphan_count = 0
    for n in d.get("nodes", []):
        if "Trigger" in n["type"] or n["type"].endswith("webhook"):
            continue
        if n["name"] not in targeted:
            orphan_count += 1
    if orphan_count > 0:
        failures.append(f"{f}: {orphan_count} orphan nodes (no inbound connections) — likely incomplete workflow")

if failures:
    print(f"FAIL — {len(failures)} problem(s):")
    for x in failures:
        print(f"  - {x}")
    sys.exit(1)

print(f"PASS — {len(files)} workflows import-clean "
      f"({sum(len(json.load(open(f, encoding='utf-8'))['nodes']) for f in files)} nodes)")
