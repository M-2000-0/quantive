#!/usr/bin/env python3
"""Fix n8n workflow JSONs from desktop to be import-compatible.

Problems fixed:
1. Switch v3 nodes: convert old `rules.rules[]` format to new `rules.values[]` 
   with proper conditions.{options,conditions,combinator} structure
2. Move retryOnFail/maxTries/onError from parameters to node-level
3. Add missing options/combinator to switch conditions
4. Fix typeVersion mismatches

Run:  python fix_desktop_workflows.py
"""

import json
import os
import shutil
import sys
import uuid
from pathlib import Path

# Workflows on desktop
DESKTOP_DIR = Path(r"C:\Users\HP\OneDrive\Desktop\uncomplete workflows")
BACKUP_DIR = Path(r"C:\Users\HP\OneDrive\Desktop\uncomplete workflows\backup")

# Safe type versions
SAFE_TV = {
    "n8n-nodes-base.code": (1, 2),
    "n8n-nodes-base.httpRequest": (1, 4.1),
    "n8n-nodes-base.postgres": (1, 2.4),
    "n8n-nodes-base.slack": (1, 2.1),
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


def generate_condition_id(node_name: str, rule_idx: int, cond_idx: int) -> str:
    """Generate a deterministic condition ID."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"quantive:{node_name}:{rule_idx}:{cond_idx}"))


def fix_switch_node(node: dict, node_name: str) -> dict:
    """Convert old switch schema to v3 fixedCollection format."""
    params = node.get("parameters", {})
    rules = params.get("rules", {})
    
    # Detect old format: rules.rules[] with {value, output}
    if "rules" in rules and isinstance(rules["rules"], list):
        old_rules = rules["rules"]
        fallback_output = rules.get("fallbackOutput", 5)
        
        # Convert to new format
        new_values = []
        for i, old_rule in enumerate(old_rules):
            value = old_rule.get("value", "")
            output = old_rule.get("output", 0)
            
            # Check if this is a string or number comparison
            data_type = params.get("dataType", "string")
            
            # Extract expression from value1 field
            value1 = params.get('value1', '')
            if value1.startswith('=') and '{{' in value1:
                start = value1.find('{{') + 2
                end = value1.rfind('}}')
                if start > 2 and end > start:
                    expr = value1[start:end].strip()
                else:
                    expr = value1.lstrip('=').strip()
            else:
                expr = value1.lstrip('=').strip()
            
            condition = {
                "id": generate_condition_id(node_name, i, 0),
                "leftValue": "={{ " + expr + " }}",
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
                "outputKey": f"Output {output}" if data_type == "string" else str(output),
                "value": value,
                "output": output
            }
            new_values.append(new_rule)
        
        # Reconstruct parameters
        new_params = {k: v for k, v in params.items() if k != "rules"}
        new_params["rules"] = {
            "values": new_values,
            "fallbackOutput": fallback_output
        }
        
        # Fix value1 field to use proper expression
        if "value1" in params:
            new_params["value1"] = params["value1"]
        
        node["parameters"] = new_params
        
    elif "values" in rules:
        # Already in new format but might be missing options/combinator
        for i, rule in enumerate(rules.get("values", [])):
            conditions = rule.get("conditions", {})
            if "options" not in conditions:
                conditions["options"] = {
                    "caseSensitive": True,
                    "leftValue": "",
                    "typeValidation": "strict"
                }
            if "combinator" not in conditions:
                conditions["combinator"] = "and"
            if "conditions" not in conditions:
                conditions["conditions"] = []
            rule["conditions"] = conditions
            
            if rule.get("renameOutput") and "outputKey" not in rule:
                rule["outputKey"] = f"Output {rule.get('output', i)}"
            
            rules["values"][i] = rule
    
    return node


def fix_node_level_props(node: dict) -> dict:
    """Move node-level properties out of parameters."""
    params = node.get("parameters", {})
    node_level = {}
    
    for key in NODE_LEVEL_ONLY:
        if key in params:
            node_level[key] = params.pop(key)
    
    # Also check for options that should be in parameters
    if "options" in params and isinstance(params["options"], dict):
        # options should stay in parameters
        pass
    
    # Node-level properties
    for key, value in node_level.items():
        node[key] = value
    
    return node


def fix_type_version(node: dict) -> dict:
    """Ensure typeVersion is within safe bounds."""
    ntype = node.get("type", "")
    tv = node.get("typeVersion", 1)
    
    if ntype in SAFE_TV:
        min_tv, max_tv = SAFE_TV[ntype]
        if tv < min_tv:
            node["typeVersion"] = min_tv
        elif tv > max_tv:
            node["typeVersion"] = max_tv
    
    return node


def fix_webhook_node(node: dict) -> dict:
    """Fix webhook node parameters."""
    params = node.get("parameters", {})
    
    # Ensure options exists for webhook v2
    if "options" not in params:
        params["options"] = {}
    
    # Fix responseMode if needed
    if "responseMode" in params:
        if params["responseMode"] == "responseNode":
            params["responseMode"] = "lastNode"
    
    return node


def fix_http_request_node(node: dict) -> dict:
    """Fix httpRequest node parameters."""
    params = node.get("parameters", {})
    
    # Ensure options exists
    if "options" not in params:
        params["options"] = {}
    
    # Ensure options has timeout if retry is set
    if node.get("retryOnFail") and "timeout" not in params.get("options", {}):
        params["options"]["timeout"] = 30000
    
    return node


def fix_postgres_node(node: dict) -> dict:
    """Fix postgres node parameters."""
    params = node.get("parameters", {})
    
    # Ensure options exists
    if "options" not in params:
        params["options"] = {}
    
    return node


def fix_email_node(node: dict) -> dict:
    """Fix emailSend node parameters."""
    params = node.get("parameters", {})
    
    # Ensure options exists
    if "options" not in params:
        params["options"] = {}
    
    # Fix emailType to emailFormat if needed (older format)
    if "emailType" in params and "emailFormat" not in params:
        params["emailFormat"] = params.pop("emailType")
    
    return node


def fix_slack_node(node: dict) -> dict:
    """Fix slack node parameters."""
    params = node.get("parameters", {})
    
    # Ensure otherOptions exists
    if "otherOptions" not in params:
        params["otherOptions"] = {}
    
    return node


def fix_if_node(node: dict) -> dict:
    """Fix if node conditions structure."""
    params = node.get("parameters", {})
    conditions = params.get("conditions", {})
    
    # Ensure options exists
    if "options" not in conditions:
        conditions["options"] = {
            "caseSensitive": True,
            "leftValue": "",
            "typeValidation": "strict"
        }
    
    # Ensure combinator exists
    if "combinator" not in conditions:
        conditions["combinator"] = "and"
    
    params["conditions"] = conditions
    node["parameters"] = params
    
    return node


def fix_schedule_trigger_node(node: dict) -> dict:
    """Fix scheduleTrigger node parameters."""
    params = node.get("parameters", {})
    rule = params.get("rule", {})
    
    # Ensure interval structure
    if "interval" not in rule:
        rule["interval"] = [{"field": "hours", "hoursInterval": 1}]
    
    params["rule"] = rule
    node["parameters"] = params
    
    return node


def fix_split_in_batches_node(node: dict) -> dict:
    """Fix splitInBatches node parameters."""
    params = node.get("parameters", {})
    
    # Ensure options exists
    if "options" not in params:
        params["options"] = {}
    
    return node


def fix_wait_node(node: dict) -> dict:
    """Fix wait node parameters."""
    params = node.get("parameters", {})
    
    # Ensure options exists
    if "options" not in params:
        params["options"] = {}
    
    return node


def fix_respond_to_webhook_node(node: dict) -> dict:
    """Fix respondToWebhook node parameters."""
    params = node.get("parameters", {})
    
    # Ensure options exists
    if "options" not in params:
        params["options"] = {}
    
    return node


def fix_workflow(data: dict, filename: str) -> tuple[dict, list[str]]:
    """Fix all nodes in a workflow."""
    warnings = []
    nodes = data.get("nodes", [])
    
    for node in nodes:
        ntype = node.get("type", "")
        node_name = node.get("name", "unknown")
        
        # Fix switch nodes first (most complex)
        if ntype == "n8n-nodes-base.switch":
            node = fix_switch_node(node, node_name)
        
        # Fix node-level properties
        node = fix_node_level_props(node)
        
        # Fix type version
        node = fix_type_version(node)
        
        # Fix node-specific issues
        if ntype == "n8n-nodes-base.webhook":
            node = fix_webhook_node(node)
        elif ntype == "n8n-nodes-base.httpRequest":
            node = fix_http_request_node(node)
        elif ntype == "n8n-nodes-base.postgres":
            node = fix_postgres_node(node)
        elif ntype == "n8n-nodes-base.emailSend":
            node = fix_email_node(node)
        elif ntype == "n8n-nodes-base.slack":
            node = fix_slack_node(node)
        elif ntype == "n8n-nodes-base.if":
            node = fix_if_node(node)
        elif ntype == "n8n-nodes-base.scheduleTrigger":
            node = fix_schedule_trigger_node(node)
        elif ntype == "n8n-nodes-base.splitInBatches":
            node = fix_split_in_batches_node(node)
        elif ntype == "n8n-nodes-base.wait":
            node = fix_wait_node(node)
        elif ntype == "n8n-nodes-base.respondToWebhook":
            node = fix_respond_to_webhook_node(node)
    
    # Check for orphan nodes (nodes with no incoming connections)
    conns = data.get("connections", {})
    targeted = set()
    for outs in conns.values():
        for out in outs.get("main", []):
            for e in out:
                targeted.add(e.get("node"))
    
    for node in nodes:
        ntype = node.get("type", "")
        node_name = node.get("name", "")
        if "Trigger" in ntype or ntype.endswith("webhook"):
            continue
        if node_name not in targeted:
            warnings.append(f"Orphan node: {node_name} (no inbound connection)")
    
    return data, warnings


def main():
    """Fix all workflows on desktop."""
    if not DESKTOP_DIR.exists():
        print(f"Desktop directory not found: {DESKTOP_DIR}")
        sys.exit(1)
    
    # Create backup
    if not BACKUP_DIR.exists():
        BACKUP_DIR.mkdir(parents=True)
        print(f"Created backup directory: {BACKUP_DIR}")
    
    workflow_files = sorted(DESKTOP_DIR.glob("*.json"))
    
    if not workflow_files:
        print(f"No workflow JSON files found in {DESKTOP_DIR}")
        sys.exit(1)
    
    all_warnings = []
    
    for wf_path in workflow_files:
        print(f"\nProcessing: {wf_path.name}")
        
        # Backup original
        backup_path = BACKUP_DIR / wf_path.name
        if not backup_path.exists():
            shutil.copy2(wf_path, backup_path)
            print(f"  Backed up to: {backup_path}")
        
        # Load workflow
        with open(wf_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Fix workflow
        fixed_data, warnings = fix_workflow(data, wf_path.name)
        all_warnings.extend([f"{wf_path.name}: {w}" for w in warnings])
        
        # Save fixed workflow
        with open(wf_path, "w", encoding="utf-8") as f:
            json.dump(fixed_data, f, indent=2, ensure_ascii=False)
        
        print(f"  Fixed {len(fixed_data.get('nodes', []))} nodes")
        if warnings:
            for w in warnings:
                print(f"  Warning: {w}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Fixed {len(workflow_files)} workflow(s)")
    if all_warnings:
        print(f"Warnings ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"  - {w}")
    else:
        print("No warnings")
    
    print(f"\nBackup saved to: {BACKUP_DIR}")
    print(f"To restore originals, copy files from backup back to desktop")


if __name__ == "__main__":
    main()
