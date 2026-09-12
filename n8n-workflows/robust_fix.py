#!/usr/bin/env python3
"""Robust fix for n8n workflow JSONs from desktop.

Handles:
1. Switch v3: convert old `rules.rules[]` or `rules.values[]` with missing options
2. Node-level props (retryOnFail, maxTries, onError) inside parameters -> move to node
3. TypeVersion clamping to safe ranges
4. Add missing options/combinator to switch/if conditions
5. Fix connection references that don't match node names
"""

import json
import os
import shutil
import sys
import uuid
from pathlib import Path

DESKTOP_DIR = Path(r"C:\Users\HP\OneDrive\Desktop\uncomplete workflows")
BACKUP_DIR = Path(r"C:\Users\HP\OneDrive\Desktop\uncomplete workflows\backup")

# Safe type versions - expanded for newer node versions
SAFE_TV = {
    "n8n-nodes-base.code": (1, 2),
    "n8n-nodes-base.httpRequest": (1, 4.2),  # Allow 4.2
    "n8n-nodes-base.postgres": (1, 2.5),     # Allow 2.5
    "n8n-nodes-base.slack": (1, 2.2),        # Allow 2.2
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


def generate_id(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def extract_expression(value1: str) -> str:
    """Extract n8n expression from value1 like '={{ $json.status }}' -> '$json.status'"""
    if not value1:
        return ""
    # Remove '={{' prefix
    if value1.startswith('=') and '{{' in value1:
        start = value1.find('{{') + 2
        end = value1.rfind('}}')
        if start > 2 and end > start:
            return value1[start:end].strip()
    # Just strip leading '='
    return value1.lstrip('=').strip()


def fix_switch_node(node: dict, node_name: str) -> dict:
    """Fix switch node to v3 format with proper conditions structure."""
    params = node.get("parameters", {})
    rules_container = params.get("rules", {})
    
    # Handle old format: rules.rules[]
    if "rules" in rules_container and isinstance(rules_container["rules"], list):
        old_rules = rules_container["rules"]
        fallback = rules_container.get("fallbackOutput", 5)
        data_type = params.get("dataType", "string")
        value1 = extract_expression(params.get("value1", ""))
        
        new_values = []
        for i, old_rule in enumerate(old_rules):
            value = old_rule.get("value", "")
            output = old_rule.get("output", 0)
            
            condition = {
                "id": generate_id(f"{node_name}:rule:{i}"),
                "leftValue": f"={{ {value1} }}",
                "rightValue": value,
                "operator": {
                    "type": "string" if data_type == "string" else "number",
                    "operation": "equals"
                }
            }
            
            new_rule = {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict"
                    },
                    "conditions": [condition],
                    "combinator": "and"
                },
                "renameOutput": True,
                "outputKey": f"Output {output}",
                "value": value,
                "output": output
            }
            new_values.append(new_rule)
        
        # Rebuild rules container with correct format
        params["rules"] = {
            "values": new_values,
            "fallbackOutput": fallback
        }
        node["parameters"] = params
    
    elif "values" in rules_container:
        # New format but may need fixes
        values = rules_container.get("values", [])
        for i, rule in enumerate(values):
            conds = rule.get("conditions", {})
            
            # Ensure proper structure
            if "options" not in conds:
                conds["options"] = {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"}
            if "combinator" not in conds:
                conds["combinator"] = "and"
            if "conditions" not in conds:
                conds["conditions"] = []
            
            # Ensure each condition has an id
            for j, cond in enumerate(conds["conditions"]):
                if "id" not in cond:
                    cond["id"] = generate_id(f"{node_name}:cond:{i}:{j}")
            
            rule["conditions"] = conds
            
            # Ensure renameOutput is boolean and outputKey exists
            if rule.get("renameOutput"):
                if "outputKey" not in rule:
                    rule["outputKey"] = f"Output {rule.get('output', i)}"
            elif "renameOutput" not in rule:
                rule["renameOutput"] = False
        
        rules_container["values"] = values
    
    return node


def move_node_level_props(node: dict) -> dict:
    """Move retryOnFail, maxTries, onError from parameters to node level."""
    params = node.get("parameters", {})
    
    for key in list(params.keys()):
        if key in NODE_LEVEL_ONLY:
            node[key] = params.pop(key)
    
    return node


def ensure_options(params: dict, key: str = "options") -> dict:
    """Ensure options dict exists in parameters."""
    if key not in params:
        params[key] = {}
    elif not isinstance(params[key], dict):
        params[key] = {}
    return params


def fix_node(node: dict) -> dict:
    """Apply all fixes to a single node."""
    ntype = node.get("type", "")
    node_name = node.get("name", "unknown")
    
    params = node.get("parameters", {})
    
    # 1. Fix switch nodes
    if ntype == "n8n-nodes-base.switch":
        node = fix_switch_node(node, node_name)
        params = node.get("parameters", {})
    
    # 2. Fix if nodes
    if ntype == "n8n-nodes-base.if":
        conds = params.get("conditions", {})
        if "options" not in conds:
            conds["options"] = {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"}
        if "combinator" not in conds:
            conds["combinator"] = "and"
        for j, cond in enumerate(conds.get("boolean", conds.get("conditions", []))):
            if "id" not in cond:
                cond["id"] = generate_id(f"{node_name}:cond:{j}")
        params["conditions"] = conds
    
    # 3. Move node-level props out of parameters
    node = move_node_level_props(node)
    params = node.get("parameters", {})
    
    # 4. Ensure options exists for various node types
    if ntype in ("n8n-nodes-base.httpRequest", "n8n-nodes-base.postgres", 
                 "n8n-nodes-base.emailSend", "n8n-nodes-base.webhook",
                 "n8n-nodes-base.respondToWebhook", "n8n-nodes-base.splitInBatches",
                 "n8n-nodes-base.wait"):
        ensure_options(params)
    
    # 5. Ensure otherOptions for slack
    if ntype == "n8n-nodes-base.slack":
        if "otherOptions" not in params:
            params["otherOptions"] = {}
    
    # 6. Fix emailType -> emailFormat
    if ntype == "n8n-nodes-base.emailSend":
        if "emailType" in params and "emailFormat" not in params:
            params["emailFormat"] = params.pop("emailType")
    
    node["parameters"] = params
    
    # 7. Clamp typeVersion
    tv = node.get("typeVersion", 1)
    if ntype in SAFE_TV:
        min_tv, max_tv = SAFE_TV[ntype]
        if tv < min_tv:
            node["typeVersion"] = min_tv
        elif tv > max_tv:
            node["typeVersion"] = max_tv
    
    return node


def fix_connections(data: dict) -> dict:
    """Fix connection references to match actual node names."""
    nodes = data.get("nodes", [])
    conns = data.get("connections", {})
    
    # Build name -> id mapping
    name_to_info = {n["name"]: n for n in nodes}
    id_to_name = {n["id"]: n["name"] for n in nodes}
    
    fixed_conn = {}
    for src_name, outs in conns.items():
        # Source might be referenced by name or id
        if src_name not in name_to_info and src_name in id_to_name:
            src_name = id_to_name[src_name]
        
        if src_name not in name_to_info:
            continue  # Skip broken connections
        
        new_outs = {"main": []}
        for out_idx, out_list in enumerate(outs.get("main", [])):
            new_targets = []
            for edge in out_list:
                tgt = edge.get("node", "")
                # Target might be referenced by name or id
                if tgt in id_to_name:
                    tgt = id_to_name[tgt]
                if tgt in name_to_info:
                    new_targets.append({
                        "node": tgt,
                        "type": edge.get("type", "main"),
                        "index": edge.get("index", 0)
                    })
            if new_targets:
                while len(new_outs["main"]) <= out_idx:
                    new_outs["main"].append([])
                new_outs["main"][out_idx] = new_targets
        
        if new_outs["main"]:
            fixed_conn[src_name] = new_outs
    
    data["connections"] = fixed_conn
    return data


def fix_workflow(data: dict, filename: str) -> tuple[dict, list[str]]:
    """Fix all issues in a workflow."""
    warnings = []
    nodes = data.get("nodes", [])
    
    # Fix each node
    for node in nodes:
        node = fix_node(node)
    
    # Fix connections
    data = fix_connections(data)
    
    # Check for issues
    nodes_by_name = {n["name"]: n for n in nodes}
    nodes_by_id = {n["id"]: n for n in nodes}
    
    # Check connections reference valid nodes
    conns = data.get("connections", {})
    all_targets = set()
    for src, outs in conns.items():
        if src not in nodes_by_name and src not in nodes_by_id:
            warnings.append(f"Connection source '{src}' not found in nodes")
        for out_list in outs.get("main", []):
            for edge in out_list:
                tgt = edge.get("node", "")
                all_targets.add(tgt)
                if tgt not in nodes_by_name and tgt not in nodes_by_id:
                    warnings.append(f"Connection target '{tgt}' not found in nodes")
    
    # Check for orphan nodes
    targeted = set()
    for src, outs in conns.items():
        if src in nodes_by_name or src in nodes_by_id:
            for out_list in outs.get("main", []):
                for edge in out_list:
                    tgt = edge.get("node", "")
                    if tgt in nodes_by_name or tgt in nodes_by_id:
                        targeted.add(tgt)
    
    for node in nodes:
        ntype = node.get("type", "")
        name = node["name"]
        if "Trigger" in ntype or ntype.endswith("webhook"):
            continue
        if name not in targeted:
            warnings.append(f"Orphan node: {name}")
    
    # Check stripeTrigger has empty params
    for node in nodes:
        if node.get("type") == "n8n-nodes-base.stripeTrigger" and node.get("parameters"):
            warnings.append(f"stripeTrigger '{node['name']}' should have empty parameters")
    
    return data, warnings


def main():
    if not DESKTOP_DIR.exists():
        print(f"Desktop directory not found: {DESKTOP_DIR}")
        sys.exit(1)
    
    if not BACKUP_DIR.exists():
        BACKUP_DIR.mkdir(parents=True)
        print(f"Created backup: {BACKUP_DIR}")
    
    workflow_files = sorted(DESKTOP_DIR.glob("*.json"))
    if not workflow_files:
        print(f"No workflow files found in {DESKTOP_DIR}")
        sys.exit(1)
    
    all_warnings = []
    
    for wf_path in workflow_files:
        print(f"\nProcessing: {wf_path.name}")
        
        # Backup
        backup_path = BACKUP_DIR / wf_path.name
        if not backup_path.exists():
            shutil.copy2(wf_path, backup_path)
        
        with open(wf_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        fixed_data, warnings = fix_workflow(data, wf_path.name)
        all_warnings.extend([f"{wf_path.name}: {w}" for w in warnings])
        
        with open(wf_path, "w", encoding="utf-8") as f:
            json.dump(fixed_data, f, indent=2, ensure_ascii=False)
        
        print(f"  Fixed {len(fixed_data.get('nodes', []))} nodes")
        if warnings:
            for w in warnings[:5]:  # Show first 5
                print(f"  Warning: {w}")
            if len(warnings) > 5:
                print(f"  ... and {len(warnings) - 5} more warnings")
    
    print(f"\n{'='*60}")
    print(f"Fixed {len(workflow_files)} workflow(s)")
    print(f"Total warnings: {len(all_warnings)}")
    print(f"Backup: {BACKUP_DIR}")


if __name__ == "__main__":
    main()
