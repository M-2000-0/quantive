"""Qubo aggregation engine — patterns, not people.

Privacy contract (enforced here, not just documented):
- Only users with an explicit opt-in fact (category=qubo, key=opt_in, value=yes)
  are ever counted.
- Only age-bracket aggregates are exposed — never names, conversations,
  transactions, or individual records.
- Buckets smaller than MIN_BUCKET contributors are suppressed (k-anonymity).
- With no live buckets, callers must show ILLUSTRATIVE trends labeled as such.

Facts read (all from Personal DB, user-owned):
- qubo/opt_in = yes|no (source: qubo, explicit consent)
- profile/age_bracket = 18-24|25-34|35-44|45-54|55-64|65+
- onboarding facts: invest_accounts, investment_income, retirement, housing...
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.personal.models import ProfileFact

AGE_BRACKETS = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]

MIN_BUCKET = 5

PRIVACY_NOTE = (
    "Aggregates only. No names, conversations, or individual records are ever exposed. "
    f"Buckets with fewer than {MIN_BUCKET} contributors are suppressed."
)

ILLUSTRATIVE_TRENDS: list[dict] = [
    {"segment": "25-34", "signal": "investing more in diversified instruments", "direction": "up"},
    {"segment": "35-44", "signal": "spending more on housing-related costs", "direction": "up"},
    {"segment": "45-54", "signal": "allocating more toward retirement contributions", "direction": "flat"},
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_opted_in(db: Session, user_id: str) -> bool:
    row = (
        db.query(ProfileFact)
        .filter(ProfileFact.user_id == user_id,
                ProfileFact.category == "qubo",
                ProfileFact.key == "opt_in")
        .first()
    )
    return bool(row is not None and (row.value or "").strip().lower() == "yes")


def get_bracket(db: Session, user_id: str) -> str | None:
    row = (
        db.query(ProfileFact)
        .filter(ProfileFact.user_id == user_id,
                ProfileFact.category == "profile",
                ProfileFact.key == "age_bracket")
        .first()
    )
    if row and (row.value or "") in AGE_BRACKETS:
        return row.value
    return None


def set_consent(db: Session, user_id: str, opt_in: bool,
                age_bracket: str | None = None) -> dict:
    """Store explicit Qubo consent (+ optional bracket). Validates bracket."""
    if age_bracket is not None and age_bracket not in AGE_BRACKETS:
        raise ValueError(f"Invalid age_bracket: {age_bracket}")
    opt_row = (
        db.query(ProfileFact)
        .filter(ProfileFact.user_id == user_id,
                ProfileFact.category == "qubo",
                ProfileFact.key == "opt_in")
        .first()
    )
    if opt_row is None:
        opt_row = ProfileFact(user_id=user_id, category="qubo", key="opt_in",
                              source="qubo", confidence="user_reported", status="confirmed")
        db.add(opt_row)
    opt_row.value = "yes" if opt_in else "no"
    opt_row.value_json = {"values": [opt_row.value]}
    opt_row.status = "confirmed"
    if age_bracket is not None:
        br_row = (
            db.query(ProfileFact)
            .filter(ProfileFact.user_id == user_id,
                    ProfileFact.category == "profile",
                    ProfileFact.key == "age_bracket")
            .first()
        )
        if br_row is None:
            br_row = ProfileFact(user_id=user_id, category="profile", key="age_bracket",
                                 source="qubo", confidence="user_reported", status="confirmed")
            db.add(br_row)
        br_row.value = age_bracket
        br_row.value_json = {"values": [age_bracket]}
        br_row.status = "confirmed"
    db.commit()
    return {"opt_in": opt_in, "age_bracket": get_bracket(db, user_id)}


def _user_signals(db: Session, user_id: str) -> dict[str, bool]:
    rows = db.query(ProfileFact).filter(ProfileFact.user_id == user_id).all()
    vals: dict[str, set[str]] = {}
    for r in rows:
        s = set()
        if r.value:
            s.add(str(r.value))
        vj = r.value_json or {}
        if isinstance(vj, dict) and isinstance(vj.get("values"), list):
            s.update(str(x) for x in vj["values"])
        vals.setdefault(r.key, set()).update(s)
    investing = bool({"yes"} & vals.get("invest_accounts", set())) or \
        bool({"yes"} & vals.get("investment_income", set()))
    retirement = "yes" in vals.get("retirement", set())
    mortgage = "mortgage" in vals.get("housing", set()) or "yes" in vals.get("mortgage_detail", set())
    return {"investing": investing, "retirement": retirement, "mortgage": mortgage}


def _direction(pct: float) -> str:
    if pct >= 60:
        return "up"
    if pct >= 40:
        return "flat"
    return "down"


def aggregate_trends(db: Session, min_bucket: int = MIN_BUCKET) -> dict:
    """Compute live bracket aggregates over opted-in users only."""
    opt_rows = (
        db.query(ProfileFact)
        .filter(ProfileFact.category == "qubo",
                ProfileFact.key == "opt_in",
                ProfileFact.value == "yes")
        .all()
    )
    opted_ids = sorted({r.user_id for r in opt_rows})
    by_bracket: dict[str, list[str]] = {}
    for uid in opted_ids:
        br = get_bracket(db, uid)
        if br:
            by_bracket.setdefault(br, []).append(uid)
    buckets: list[dict] = []
    suppressed: list[dict] = []
    for bracket in AGE_BRACKETS:
        members = by_bracket.get(bracket, [])
        n = len(members)
        if n < min_bucket or n == 0:
            if n > 0:
                suppressed.append({"segment": bracket, "n": n})
            continue
        inv = ret = mor = 0
        for uid in members:
            sig = _user_signals(db, uid)
            inv += 1 if sig["investing"] else 0
            ret += 1 if sig["retirement"] else 0
            mor += 1 if sig["mortgage"] else 0
        pct_inv = round(100 * inv / n, 1)
        pct_ret = round(100 * ret / n, 1)
        # Lead signal: highest share wins; ties prefer investing > retirement > housing.
        ranked = sorted([("investing", pct_inv), ("retirement", pct_ret)],
                        key=lambda x: -x[1])
        lead, lead_pct = ranked[0]
        if lead == "investing":
            signal = "investing more in diversified instruments"
        else:
            signal = "allocating more toward retirement contributions"
        buckets.append({
            "segment": bracket,
            "n": n,
            "signal": signal,
            "direction": _direction(lead_pct),
            "pct_investing": pct_inv,
            "pct_retirement": pct_ret,
        })
    return {
        "generated_at": _now_iso(),
        "contributors_total": len(opted_ids),
        "buckets": buckets,
        "suppressed_buckets": suppressed,
        "is_live": bool(buckets),
        "min_bucket": min_bucket,
        "privacy": PRIVACY_NOTE,
    }


def public_trends(db: Session) -> dict:
    """Public payload: live buckets when available, else labeled illustrative."""
    agg = aggregate_trends(db)
    trends = [
        {"segment": b["segment"], "signal": b["signal"], "direction": b["direction"]}
        for b in agg["buckets"]
    ]
    if trends:
        return {
            "is_live": True,
            "as_of": agg["generated_at"],
            "contributors_total": agg["contributors_total"],
            "trends": trends,
            "buckets": agg["buckets"],
            "privacy": agg["privacy"],
        }
    return {
        "is_live": False,
        "as_of": agg["generated_at"],
        "contributors_total": agg["contributors_total"],
        "trends": ILLUSTRATIVE_TRENDS,
        "note": (f"Illustrative preview — {agg['contributors_total']} contributors so far; "
                 f"live brackets unlock at {MIN_BUCKET}+ contributors per age group."),
        "privacy": agg["privacy"],
    }
