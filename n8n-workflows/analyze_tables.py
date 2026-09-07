"""Analyze which DB tables the workflows reference vs. which schemas define."""
import collections
import glob
import json
import os
import re

os.chdir(os.path.dirname(os.path.abspath(__file__)))

table_refs = collections.defaultdict(set)
for f in sorted(glob.glob("workflows/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    wf = os.path.basename(f)
    for n in d.get("nodes", []):
        ntype = n.get("type", "")
        # v2: SQL lives in native Postgres node query params
        if "postgres" in ntype:
            sql = n.get("parameters", {}).get("query", "")
            for m in re.findall(r"(?:FROM|INTO|UPDATE)\s+([a-z_.]+)", sql, re.I):
                if m.lower() not in ("the", "this", "a", "if", "no", "now"):
                    table_refs[m].add(wf)
        # v1 compat: SQL embedded in Code nodes
        elif "code" in ntype:
            js = n.get("parameters", {}).get("jsCode", "")
            for m in re.findall(r"(?:FROM|INTO|UPDATE)\s+([a-z_]+)", js, re.I):
                if m.lower() not in ("the", "this", "a", "if", "no"):
                    table_refs[m].add(wf)

print("=== Tables referenced by workflows ===")
for t in sorted(table_refs):
    print(f"{t:34s} {sorted(table_refs[t])}")


def tables_in(path):
    with open(path, encoding="utf-8") as fh:
        return set(re.findall(r"CREATE TABLE IF NOT EXISTS ([a-z_.]+)", fh.read()))


def normalize(t):
    """Map schema-qualified names (workflows.x) to bare table names."""
    return t.split(".")[-1] if "." in t else t


db1 = tables_in("schemas/database-schema.sql")

print("\n=== Schema coverage (canonical: schemas/database-schema.sql) ===")
needed = {normalize(t) for t in set(table_refs) if t != "SET"}
schema_norm = {normalize(t) for t in db1}
for label, schema in [("schemas/database-schema.sql", schema_norm)]:
    missing = sorted(needed - schema)
    extra = sorted(schema - needed)
    print(f"--- {label}")
    print(f"    defines {len(schema)} tables | workflows need {len(needed)}")
    print(f"    MISSING (referenced but not defined): {missing or 'none'}")
    print(f"    extra (defined but not referenced): {extra or 'none'}")
