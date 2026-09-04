"""Marketing Claims Validator."""
import re, logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.marketing")

PROHIBITED_PATTERNS = [
    r"bug[- ]free", r"risk[- ]free", r"guaranteed", r"fully secure",
    r"will never lose data", r"works for every workload", r"government certified",
    r"production[- ]ready", r"error[- ]free", r"100% (accurate|secure|reliable)",
    r"zero (risk|downtime|errors)", r"unbreakable", r"unhackable",
    r"unlimited liability", r"personal guarantee",
]


def validate_claim(text):
    violations = []
    for p in PROHIBITED_PATTERNS:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            violations.append(m.group())
    return {"approved": len(violations) == 0, "violations": violations}


def validate_proposal(db, text, user_id):
    result = validate_claim(text)
    from app.audit.database_audit import append_audit_entry
    append_audit_entry(db=db, event_type="marketing.validation", resource_type="proposal",
        resource_id="review", action="validate", details={"approved": result["approved"], "user_id": user_id})
    return result


def get_approved_language():
    return [
        "Quantive provides decision-support analysis, not financial advice.",
        "Results are based on model assumptions and may not reflect actual outcomes.",
        "The system is experimental and under active development.",
        "All recommendations should be independently verified before action.",
        "Quantive does not guarantee specific financial results.",
        "Customer maintains responsibility for data accuracy and independent backups.",
        "Quantive may suspend operations when safety, security, or integrity is at risk.",
        "Quantive aggregate liability is limited to fees paid under the applicable SOW.",
    ]