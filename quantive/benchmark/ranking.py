"""Configurable ranking methodology.

Every metric is normalised (min-max, inverted so that larger = better) and
weighted. Feasibility is a hard gate: infeasible solvers rank after all
feasible ones. The ranking weights are configurable so the user can define what
"best" means; Quantive never simply picks the fastest solver.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from quantive.models.results import BenchmarkResult, BenchmarkRow

DEFAULT_RANKING_WEIGHTS: Dict[str, float] = {
    "objective_value": 1.0,
    "feasibility": 2.0,
    "runtime": 0.4,
    "constraint_violations": 1.5,
    "robustness_worst_cost": 0.8,
    "compute_cost": 0.3,
}

# metrics where smaller is better -> invert before scoring
LOWER_IS_BETTER = {"objective_value", "runtime", "constraint_violations",
                   "robustness_worst_cost", "compute_cost", "financing_cost",
                   "risk_total", "constraint_violation_magnitude"}


def _metric_values(rows: List[BenchmarkRow], key: str) -> List[float]:
    return [getattr(r, key) for r in rows]


def _normalize(values: List[float], lower_better: bool) -> List[float]:
    """Min-max normalize into [0,1]; larger = better."""
    vals = np.array(values, dtype=float)
    lo, hi = float(vals.min()), float(vals.max())
    if hi - lo < 1e-12:
        return [0.5] * len(values)
    norm = (vals - lo) / (hi - lo)
    if lower_better:
        norm = 1.0 - norm
    return [float(v) for v in norm]


def rank(rows: List[BenchmarkRow], weights: Dict[str, float] | None = None) -> BenchmarkResult:
    """Rank solver rows using the configurable methodology."""
    weights = dict(DEFAULT_RANKING_WEIGHTS if weights is None else weights)
    if not rows:
        return BenchmarkResult(problem_id="", ranking_weights=weights, rows=[])

    # normalize each scored metric
    scored_metrics = [m for m in weights if any(hasattr(r, m) for r in rows)]
    normalized: Dict[str, List[float]] = {}
    for m in scored_metrics:
        vals = _metric_values(rows, m)
        normalized[m] = _normalize(vals, m in LOWER_IS_BETTER)

    feasible = [r.feasible for r in rows]

    scores: List[float] = []
    for idx, row in enumerate(rows):
        s = 0.0
        wsum = 0.0
        for m in scored_metrics:
            w = weights.get(m, 0.0)
            s += w * normalized[m][idx]
            wsum += w
        if not feasible[idx]:
            s -= 100.0  # feasibility is a hard gate
        scores.append(s)

    order = sorted(range(len(rows)), key=lambda i: (-scores[i], rows[i].objective_value))
    rank_of = {old: pos + 1 for pos, old in enumerate(order)}

    best_by_metric: Dict[str, str] = {}
    for m in scored_metrics:
        vals = _metric_values(rows, m)
        lower_better = m in LOWER_IS_BETTER
        feasible_rows = [i for i in range(len(rows)) if feasible[i]]
        if feasible_rows:
            target = min(feasible_rows, key=lambda i: vals[i]) if lower_better else max(feasible_rows, key=lambda i: vals[i])
            best_by_metric[m] = rows[target].solver

    for i, row in enumerate(rows):
        row.normalized = {m: normalized[m][i] for m in scored_metrics}
        row.score = scores[i]
        row.rank = rank_of[i]
        row.best_for = [m for m, s in best_by_metric.items() if s == row.solver]

    return BenchmarkResult(
        problem_id=rows[0].problem_id if hasattr(rows[0], "problem_id") else "",
        methodology=(
            "Weighted min-max normalized metrics; feasibility is a hard gate. "
            "Lower-is-better metrics are inverted before weighting."
        ),
        ranking_weights=weights,
        rows=rows,
    )