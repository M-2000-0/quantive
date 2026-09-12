"""Tax Intelligence Score: completeness/readiness only. Never savings."""
from __future__ import annotations


def compute_score(*, facts_count: int, visible_total: int, open_actions: int,
                  doc_gaps: int, needs_review: int) -> dict:
    completeness = 0
    if visible_total:
        completeness = min(100, round(100 * facts_count / max(1, visible_total)))
    # Penalties are small and transparent; score stays a readiness signal.
    score = completeness - min(12, open_actions * 2) - min(8, doc_gaps)
    score = max(0, min(100, score))
    if score >= 85:
        msg = "Your profile is in strong shape. A few reviews remain."
    elif score >= 65:
        msg = "Your profile is mostly complete. Quantive identified several areas that may deserve review."
    elif score >= 35:
        msg = "Good start. Completing onboarding unlocks more precise intelligence."
    else:
        msg = "Let's build your financial profile — about 8 minutes."
    return {"score": score, "completeness": completeness, "message": msg,
            "needs_review": needs_review}
