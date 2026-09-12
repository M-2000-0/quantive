"""n8n Workflow Import API — validate and import n8n workflow JSON files.

POST /api/workflows/import  →  upload a workflow JSON, validate it against
the known failure modes that produce "Could not find property option", and
return a clear actionable report (or the cleaned JSON ready for n8n import).
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import get_current_user, log_audit_event, require_role, UserRole

router = APIRouter(prefix="/api/workflows", tags=["workflow-import"])

# Safe typeVersion bounds (mirrors n8n-workflows/validate_import.py)
SAFE_TV: dict[str, tuple[float, float]] = {
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
    "n8n-nodes-base.if": (1, 2.2),
    "n8n-nodes-base.respondToWebhook": (1, 1),
    "n8n-nodes-base.splitInBatches": (1, 1),
    "n8n-nodes-base.wait": (1, 1),
}

NODE_LEVEL_ONLY = {"retryOnFail", "maxTries", "waitBetweenTries", "onError", "alwaysOutputData"}


# ── helpers ────────────────────────────────────────────────────────────────

def _extract_expression(value1: str) -> str:
    """Turn '={{ $json.status }}' into '$json.status'."""
    if not value1:
        return ""
    if value1.startswith("=") and "{{" in value1:
        start = value1.find("{{") + 2
        end = value1.rfind("}}")
        if start > 2 and end > start:
            return value1[start:end].strip()
    return value1.lstrip("=").strip()


def _generate_id(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def _validate_workflow(data: dict) -> list[dict[str, Any]]:
    """Return a list of actionable problems found in *data*.

    Each entry is a dict with keys: node, property, message, fix.
    An empty list means the workflow should import cleanly into n8n.
    """
    problems: list[dict[str, Any]] = []
    nodes = data.get("nodes", [])

    names: set[str] = set()
    ids: set[str] = set()
    webhook_ids: set[str] = set()

    for n in nodes:
        name = n["name"]
        ntype = n.get("type", "")
        tv = n.get("typeVersion", 1)
        params = n.get("parameters", {})

        # ── duplicate names / ids ──
        if name in names:
            problems.append({"node": name, "property": "name",
                             "message": f"Duplicate node name '{name}'",
                             "fix": "Rename one of the duplicate nodes"})
        names.add(name)
        if n["id"] in ids:
            problems.append({"node": name, "property": "id",
                             "message": f"Duplicate node id '{n['id']}'",
                             "fix": "Assign unique ids to each node"})
        ids.add(n["id"])
        if "webhookId" in n:
            if n["webhookId"] in webhook_ids:
                problems.append({"node": name, "property": "webhookId",
                                 "message": f"Duplicate webhookId '{n['webhookId']}'",
                                 "fix": "Use a unique webhookId per webhook node"})
            webhook_ids.add(n["webhookId"])

        # ── typeVersion sanity ──
        if ntype in SAFE_TV:
            lo, hi = SAFE_TV[ntype]
            if not (lo <= tv <= hi):
                problems.append({"node": name, "property": "typeVersion",
                                 "message": f"typeVersion {tv} is outside the safe range {lo}–{hi} for {ntype}",
                                 "fix": f"Set typeVersion to a value in {lo}–{hi}, or update n8n to support {tv}"})

        # ── node-level props must NOT be inside parameters ──
        bad = NODE_LEVEL_ONLY & set(params.keys())
        if bad:
            for key in sorted(bad):
                problems.append({"node": name, "property": f"parameters.{key}",
                                 "message": f"'{key}' is a node-level property but appears inside parameters",
                                 "fix": f"Move '{key}' out of parameters to the node root level"})

        # ── switch v3 schema ──
        if ntype == "n8n-nodes-base.switch":
            rules = params.get("rules", {})
            allowed = {"values", "fallbackOutput"}
            if not isinstance(rules, dict) or "values" not in rules:
                problems.append({"node": name, "property": "parameters.rules",
                                 "message": f"Switch 'rules' must be an object with a 'values' array; got {type(rules).__name__}",
                                 "fix": "Convert to v3 format: rules: { values: [...], fallbackOutput: N }"})
            else:
                if set(rules.keys()) - allowed:
                    extra = set(rules.keys()) - allowed
                    problems.append({"node": name, "property": "parameters.rules",
                                     "message": f"Switch rules has unexpected keys: {sorted(extra)}",
                                     "fix": f"Remove {sorted(extra)} — only 'values' and 'fallbackOutput' are allowed"})
                for i, rule in enumerate(rules["values"]):
                    conds = rule.get("conditions", {})
                    if "options" not in conds:
                        problems.append({"node": name, "property": f"parameters.rules.values[{i}].conditions",
                                         "message": "Missing 'options' in conditions — this is what produces 'Could not find property option'",
                                         "fix": "Add options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' }"})
                    if "combinator" not in conds:
                        problems.append({"node": name, "property": f"parameters.rules.values[{i}].conditions",
                                         "message": "Missing 'combinator' in conditions",
                                         "fix": "Add combinator: 'and' (or 'or')}"})
                    if not isinstance(rule.get("renameOutput"), bool):
                        problems.append({"node": name, "property": f"parameters.rules.values[{i}].renameOutput",
                                         "message": "renameOutput must be a boolean",
                                         "fix": "Set renameOutput to true or false"})
                    if rule.get("renameOutput") and "outputKey" not in rule:
                        problems.append({"node": name, "property": f"parameters.rules.values[{i}].outputKey",
                                         "message": "renameOutput is true but outputKey is missing",
                                         "fix": "Add outputKey: 'Output N'"})
                    for cond in conds.get("conditions", []):
                        if not cond.get("id"):
                            problems.append({"node": name, "property": f"parameters.rules.values[{i}].conditions.conditions",
                                             "message": "A condition is missing its 'id'",
                                             "fix": "Add a unique id string to each condition"})

        # ── stripeTrigger must have empty parameters ──
        if ntype == "n8n-nodes-base.stripeTrigger" and params:
            problems.append({"node": name, "property": "parameters",
                             "message": "stripeTrigger must have empty parameters (no 'events' option)",
                             "fix": "Clear the parameters object: set parameters to {}"})

    # ── connection integrity ──
    conns = data.get("connections", {})
    for src, outs in conns.items():
        if src not in names:
            problems.append({"node": src, "property": "connections",
                             "message": f"Connection source '{src}' does not match any node name",
                             "fix": "Rename the connection source to match an existing node, or add the missing node"})

        for out in outs.get("main", []):
            for edge in out:
                tgt = edge.get("node", "")
                if tgt not in names:
                    problems.append({"node": src, "property": f"connections.{src}",
                                     "message": f"Connection target '{tgt}' does not match any node name",
                                     "fix": "Rename the connection target to match an existing node"})

    # ── orphan nodes ──
    targeted: set[str] = {e["node"] for outs in conns.values() for out in outs.get("main", []) for e in out}
    for n in nodes:
        ntype = n.get("type", "")
        if "Trigger" in ntype or ntype.endswith("webhook"):
            continue
        if n["name"] not in targeted:
            problems.append({"node": n["name"], "property": "connections",
                             "message": f"Node '{n['name']}' has no inbound connections (orphan)",
                             "fix": "Connect a preceding node to this node, or delete it if it is unused"})

    # ── errorWorkflow setting ──
    settings = data.get("settings", {})
    if "errorWorkflow" in settings:
        problems.append({"node": "", "property": "settings.errorWorkflow",
                         "message": "settings.errorWorkflow references a workflow that must be wired in the UI after import",
                         "fix": "After importing, set the error workflow in n8n Settings → Workflow Errors, or remove the setting"})

    return problems


def _apply_fixes(data: dict) -> dict:
    """Return a cleaned copy of *data* with all auto-fixable issues resolved.

    Non-fixable problems (e.g. duplicate names) are left for the user to resolve.
    """
    data = json.loads(json.dumps(data))  # deep copy
    nodes = data.get("nodes", [])

    names = {n["name"] for n in nodes}
    ids = {n["id"]: n["name"] for n in nodes}
    name_to_id = {n["name"]: n["id"] for n in nodes}

    for n in nodes:
        ntype = n.get("type", "")
        name = n["name"]
        params = n.get("parameters", {})

        # 1. Move node-level props out of parameters
        for key in list(params.keys()):
            if key in NODE_LEVEL_ONLY:
                n[key] = params.pop(key)

        # 2. Fix switch v3 structure (handles both old rules.rules[] and new rules.values[])
        if ntype == "n8n-nodes-base.switch":
            rules = params.get("rules", {})
            data_type = params.get("dataType", "string")
            value1_raw = params.get("value1", "")
            expr = _extract_expression(value1_raw) if value1_raw else ""

            # Case A: old format — rules.rules[] (the one that causes "Could not find property option")
            if isinstance(rules, dict) and "rules" in rules and isinstance(rules["rules"], list):
                old_rules = rules["rules"]
                fallback = rules.get("fallbackOutput", 5)
                new_values = []
                for i, old_rule in enumerate(old_rules):
                    value = old_rule.get("value", "")
                    output = old_rule.get("output", 0)
                    cond = {
                        "id": _generate_id(f"{name}:rule:{i}"),
                        "leftValue": f"={{ {expr} }}" if expr else "",
                        "rightValue": value,
                        "operator": {
                            "type": "string" if data_type == "string" else "number",
                            "operation": "equals",
                        },
                    }
                    new_values.append({
                        "conditions": {
                            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                            "conditions": [cond],
                            "combinator": "and",
                        },
                        "renameOutput": True,
                        "outputKey": f"Output {output}",
                        "value": value,
                        "output": output,
                    })
                params["rules"] = {"values": new_values, "fallbackOutput": fallback}

            # Case B: new format — rules.values[] but missing options/combinator
            elif isinstance(rules, dict) and "values" in rules:
                values = rules["values"]
                for i, rule in enumerate(values):
                    conds = rule.get("conditions", {})
                    if "options" not in conds:
                        conds["options"] = {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"}
                    if "combinator" not in conds:
                        conds["combinator"] = "and"
                    if "conditions" not in conds:
                        conds["conditions"] = []
                    for j, cond in enumerate(conds["conditions"]):
                        if "id" not in cond:
                            cond["id"] = _generate_id(f"{name}:rule:{i}:cond:{j}")
                    rule["conditions"] = conds
                    if rule.get("renameOutput"):
                        if "outputKey" not in rule:
                            rule["outputKey"] = f"Output {rule.get('output', i)}"
                    elif "renameOutput" not in rule:
                        rule["renameOutput"] = False
                # Strip unexpected keys
                allowed = {"values", "fallbackOutput"}
                for k in list(rules.keys()):
                    if k not in allowed:
                        del rules[k]

        # 3. Fix if node conditions
        if ntype == "n8n-nodes-base.if":
            conds = params.get("conditions", {})
            if "options" not in conds:
                conds["options"] = {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"}
            if "combinator" not in conds:
                conds["combinator"] = "and"
            for j, cond in enumerate(conds.get("boolean", conds.get("conditions", []))):
                if "id" not in cond:
                    cond["id"] = _generate_id(f"{name}:cond:{j}")
            params["conditions"] = conds

        # 4. Ensure options dict exists for known node types
        if ntype in (
            "n8n-nodes-base.httpRequest", "n8n-nodes-base.postgres",
            "n8n-nodes-base.emailSend", "n8n-nodes-base.webhook",
            "n8n-nodes-base.respondToWebhook", "n8n-nodes-base.splitInBatches",
            "n8n-nodes-base.wait",
        ):
            if "options" not in params or not isinstance(params.get("options"), dict):
                params["options"] = {}

        # 5. Slack otherOptions
        if ntype == "n8n-nodes-base.slack":
            if "otherOptions" not in params or not isinstance(params.get("otherOptions"), dict):
                params["otherOptions"] = {}

        # 6. emailType → emailFormat
        if ntype == "n8n-nodes-base.emailSend":
            if "emailType" in params and "emailFormat" not in params:
                params["emailFormat"] = params.pop("emailType")

        n["parameters"] = params

        # 7. Clamp typeVersion
        tv = n.get("typeVersion", 1)
        if ntype in SAFE_TV:
            lo, hi = SAFE_TV[ntype]
            if tv < lo:
                n["typeVersion"] = lo
            elif tv > hi:
                n["typeVersion"] = hi

    # 8. Fix connection references that use ids instead of names
    conns = data.get("connections", {})
    fixed_conns: dict[str, Any] = {}
    for src, outs in conns.items():
        src_name = src
        if src not in names and src in name_to_id:
            src_name = name_to_id[src]
        if src_name not in names:
            continue
        new_main: list[list[dict]] = []
        for out_list in outs.get("main", []):
            new_edges: list[dict] = []
            for edge in out_list:
                tgt = edge.get("node", "")
                if tgt in name_to_id:
                    tgt = name_to_id[tgt]
                if tgt in names:
                    new_edges.append({"node": tgt, "type": edge.get("type", "main"), "index": edge.get("index", 0)})
            new_main.append(new_edges)
        if new_main:
            fixed_conns[src_name] = {"main": new_main}
    data["connections"] = fixed_conns

    return data


# ── endpoint ────────────────────────────────────────────────────────────────

@router.post("/import", status_code=201)
async def import_workflow(
    file: UploadFile = File(...),
    auto_fix: bool = False,
    user: UserRole = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db),
):
    """Validate (and optionally auto-fix) an n8n workflow JSON for import.

    n8n throws the opaque "Could not find property option" error when a
    workflow's switch/if nodes are missing the `options`/`combinator` fields,
    or when node-level properties like `retryOnFail` are nested inside
    `parameters`.  This endpoint pre-validates the JSON and returns a plain-
    language report naming the exact node and property that would fail.

    Set `auto_fix=true` to get back a cleaned JSON payload ready to re-import
    into n8n (only auto-fixable issues are repaired; duplicates and orphan
    nodes are still reported).
    """
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")

    if not isinstance(data, dict) or "nodes" not in data:
        raise HTTPException(status_code=422, detail="Not a valid n8n workflow JSON — missing 'nodes' key")

    problems = _validate_workflow(data)

    if not problems:
        log_audit_event(db, user, "workflow.imported", "workflow",
                        metadata={"filename": file.filename, "action": "pass", "nodes": len(data.get("nodes", []))})
        return {
            "status": "pass",
            "message": f"Workflow '{file.filename}' is import-clean ({len(data.get('nodes', []))} nodes)",
            "problems": [],
            "node_count": len(data.get("nodes", [])),
        }

    actionable = [p for p in problems if p.get("fix")]

    if auto_fix:
        cleaned = _apply_fixes(data)
        cleaned_problems = _validate_workflow(cleaned)
        still_broken = [p for p in cleaned_problems if not p.get("fix")]
        return {
            "status": "partial_fix" if still_broken else "fixed",
            "message": f"Auto-fixed {len(actionable)} issue(s) in '{file.filename}'. "
                       f"{len(still_broken)} issue(s) remain and need manual attention." if still_broken
                       else f"All issues auto-fixed in '{file.filename}'.",
            "problems": problems,
            "fixed_payload": cleaned,
            "remaining_issues": still_broken,
            "node_count": len(cleaned.get("nodes", [])),
        }

    return {
        "status": "fail",
        "message": f"Workflow '{file.filename}' has {len(problems)} issue(s) that would block n8n import",
        "problems": problems,
        "node_count": len(data.get("nodes", [])),
    }


@router.post("/validate", status_code=200)
async def validate_workflow(
    body: dict,
    user: UserRole = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db),
):
    """Validate an n8n workflow JSON passed in the request body (no file upload).

    Useful for UI inline validation before the user hits import.
    """
    if not isinstance(body, dict) or "nodes" not in body:
        raise HTTPException(status_code=422, detail="Not a valid n8n workflow JSON — missing 'nodes' key")

    problems = _validate_workflow(body)
    actionable = [p for p in problems if p.get("fix")]

    if not problems:
        log_audit_event(db, user, "workflow.validated", "workflow",
                        metadata={"action": "pass", "nodes": len(body.get("nodes", []))})
        return {
            "status": "pass",
            "message": f"Workflow is import-clean ({len(body.get('nodes', []))} nodes)",
            "problems": [],
            "node_count": len(body.get("nodes", [])),
        }

    return {
        "status": "fail",
        "message": f"Workflow has {len(problems)} issue(s) that would block n8n import",
        "problems": problems,
        "actionable_count": len(actionable),
        "node_count": len(body.get("nodes", [])),
    }
