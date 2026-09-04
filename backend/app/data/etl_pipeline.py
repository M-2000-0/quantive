"""
ETL Pipeline — Historical Data Migration
=========================================
Fuzzy matching for duplicate detection, reconciliation reports.
"""

import hashlib
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional


@dataclass
class DuplicateMatch:
    """Two instruments that may be the same."""
    source_id: str
    target_id: str
    similarity: float
    match_fields: list[str]
    recommendation: str  # "merge", "keep_both", "review"


@dataclass
class ETLReport:
    """Migration/reconciliation report."""
    total_imported: int = 0
    duplicates_found: int = 0
    duplicates_merged: int = 0
    validation_errors: int = 0
    matches: list[DuplicateMatch] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_imported": self.total_imported,
            "duplicates_found": self.duplicates_found,
            "duplicates_merged": self.duplicates_merged,
            "validation_errors": self.validation_errors,
            "matches": [
                {"source": m.source_id, "target": m.target_id,
                 "similarity": m.similarity, "fields": m.match_fields,
                 "recommendation": m.recommendation}
                for m in self.matches
            ],
            "errors": self.errors,
        }


def _normalize(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text


def _name_similarity(a: str, b: str) -> float:
    """Compute similarity between two instrument names."""
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


class FuzzyMatcher:
    """Detect potentially duplicate instruments using fuzzy matching."""

    THRESHOLDS = {
        "name": 0.85,        # High bar for name similarity
        "maturity": 0,       # Exact match on maturity date
        "currency": 0,       # Exact match on currency
        "coupon_tolerance": 0.001,  # Within 10bps
    }

    def find_duplicates(
        self,
        source_instruments: list[dict],
        target_instruments: list[dict],
    ) -> list[DuplicateMatch]:
        """Compare two sets of instruments for potential duplicates."""
        matches = []

        for src in source_instruments:
            for tgt in target_instruments:
                similarity, match_fields = self._compare(src, tgt)
                if similarity > 0.7:
                    rec = "merge" if similarity > 0.9 else "review" if similarity > 0.8 else "keep_both"
                    matches.append(DuplicateMatch(
                        source_id=src.get("id", ""),
                        target_id=tgt.get("id", ""),
                        similarity=round(similarity, 3),
                        match_fields=match_fields,
                        recommendation=rec,
                    ))

        # Deduplicate: keep highest similarity per source-target pair
        best = {}
        for m in matches:
            key = (m.source_id, m.target_id)
            if key not in best or m.similarity > best[key].similarity:
                best[key] = m
        return sorted(best.values(), key=lambda x: -x.similarity)

    def _compare(self, a: dict, b: dict) -> tuple[float, list[str]]:
        """Compare two instruments, return (score, matching_fields)."""
        scores = []
        fields = []

        # Name similarity
        name_a = a.get("name", "")
        name_b = b.get("name", "")
        if name_a and name_b:
            ns = _name_similarity(name_a, name_b)
            if ns > self.THRESHOLDS["name"]:
                scores.append(ns)
                fields.append("name")

        # Maturity date exact match
        if a.get("maturity_date") == b.get("maturity_date") and a.get("maturity_date"):
            scores.append(1.0)
            fields.append("maturity_date")

        # Currency match
        if a.get("currency", "").upper() == b.get("currency", "").upper() and a.get("currency"):
            scores.append(1.0)
            fields.append("currency")

        # Coupon rate proximity
        try:
            ca = float(a.get("coupon_rate", 0))
            cb = float(b.get("coupon_rate", 0))
            if abs(ca - cb) < self.THRESHOLDS["coupon_tolerance"]:
                scores.append(1.0)
                fields.append("coupon_rate")
        except (ValueError, TypeError):
            pass

        # Principal proximity (within 10%)
        try:
            pa = float(a.get("principal_outstanding", 0))
            pb = float(b.get("principal_outstanding", 0))
            if pa > 0 and pb > 0:
                ratio = min(pa, pb) / max(pa, pb)
                if ratio > 0.9:
                    scores.append(ratio)
                    fields.append("principal")
        except (ValueError, TypeError):
            pass

        if not scores:
            return 0.0, []
        return max(scores), fields


class ETLPipeline:
    """
    ETL pipeline for instrument data migration.
    Ingest → Validate → Deduplicate → Transform → Load
    """

    def __init__(self):
        from app.data.validation import InstrumentValidator
        self.validator = InstrumentValidator()
        self.matcher = FuzzyMatcher()

    def process(
        self,
        incoming: list[dict],
        existing: list[dict] = None,
    ) -> ETLReport:
        """Run full ETL pipeline."""
        existing = existing or []
        report = ETLReport(total_imported=len(incoming))

        # 1. Validate
        all_issues = []
        for inst in incoming:
            issues = self.validator.validate(inst)
            all_issues.extend(issues)
            for issue in issues:
                if issue.severity == "error":
                    report.validation_errors += 1
                    report.errors.append({
                        "record_id": issue.record_id,
                        "field": issue.field,
                        "message": issue.message,
                    })

        # 2. Fuzzy dedup against existing
        if existing:
            matches = self.matcher.find_duplicates(incoming, existing)
            report.duplicates_found = len(matches)
            report.matches = matches

        # 3. Filter out errored records
        valid = []
        errored_ids = {e["record_id"] for e in report.errors}
        for inst in incoming:
            if inst.get("id") not in errored_ids:
                valid.append(inst)

        return report
