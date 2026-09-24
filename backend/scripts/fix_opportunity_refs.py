"""One-off: convert hardcoded rule_refs lists and _ref() calls in
opportunity_engine.py to jurisdiction-aware _juris_refs() calls.
"""
import re

p = "app/personal/opportunity_engine.py"
with open(p, encoding="utf-8") as f:
    src = f.read()

# 1. "rule_refs": [...] -> "rule_refs": _juris_refs(juris, [...])
src, n1 = re.subn(r'"rule_refs":\s*(\[(?:[^\[\]]|\[[^\]]*\])*\])',
                  r'"rule_refs": _juris_refs(juris, \1)', src)

# 2. _ref(juris, A, B, C) -> _juris_refs(juris, [A, B, C])
def _ref_repl(m):
    args = m.group(1)
    parts = [a.strip() for a in args.split(",")]
    if parts and parts[0] == "juris":
        parts = parts[1:]
    return "_juris_refs(juris, [" + ", ".join(parts) + "])"

src, n2 = re.subn(r'_ref\(juris, ([^)]+)\)', _ref_repl, src)

# 3. rule_refs": _ref(juris, X) (already covered by #2)
#    f-string forms like _ref(juris, f"{juris}-2026-mortgage-interest", "GEN-...")
#    -> replace with the US id: f-strings resolved to "US-2026-mortgage-interest"
src = src.replace('_juris_refs(juris, [f"{juris}-2026-mortgage-interest", "GEN-2026-housing-interest"])',
                  '_juris_refs(juris, ["US-2026-mortgage-interest", "GEN-2026-housing-interest"])')

with open(p, "w", encoding="utf-8", newline="") as f:
    f.write(src)

print(f"rule_refs lists wrapped: {n1}")
print(f"_ref() calls converted: {n2}")
