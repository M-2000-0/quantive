"""Deterministic feasibility repair (classical post-processing).

Stochastic and quantum-inspired solvers optimise a soft-penalty energy; a final
deterministic repair pass restores exact feasibility (debt capacity, caps,
currency/floating/liquidity bounds) with minimal cost damage. This mirrors
real hybrid quantum-classical pipelines where a classical post-processor fixes
constraint violations left by the annealer.
"""
from __future__ import annotations

import numpy as np

from quantive.objectives.spec import ProblemSpec
from quantive.solvers.common import project_box_simplex


def repair_feasibility(spec: ProblemSpec, x: np.ndarray, max_passes: int = 6) -> np.ndarray:
    """Repair an allocation toward exact feasibility.

    Operates greedily: moves money out of violating groups into the cheapest
    compliant instruments with remaining capacity. Returns the repaired vector.
    """
    R = spec.financing_requirement
    caps = spec.capacity
    x = project_box_simplex(np.clip(x, 0.0, caps), caps, R)

    for _ in range(max_passes):
        moved = 0.0
        # foreign currency limit(s)
        if spec.foreign_currency_limit_share is not None:
            foreign_idx = np.flatnonzero(spec.is_foreign)
            excess = float(x[foreign_idx].sum()) - spec.foreign_currency_limit_share * R
            moved += _shed_and_fill(spec, x, foreign_idx, excess, ~spec.is_foreign)
        for ccy, cap_share in spec.per_currency_limits.items():
            idx = np.flatnonzero(spec.currencies == ccy)
            excess = float(x[idx].sum()) - cap_share * R
            moved += _shed_and_fill(spec, x, idx, excess, spec.currencies != ccy)
        # floating rate limit
        if spec.floating_rate_limit_share is not None:
            flt_idx = np.flatnonzero(spec.is_floating)
            excess = float(x[flt_idx].sum()) - spec.floating_rate_limit_share * R
            moved += _shed_and_fill(spec, x, flt_idx, excess, ~spec.is_floating)
        # minimum liquidity (lower bound)
        if spec.min_liquidity_share > 0:
            liq_idx = np.flatnonzero(spec.is_liquid)
            deficit = spec.min_liquidity_share * R - float(x[liq_idx].sum())
            if deficit > 0:
                sources = np.flatnonzero(~spec.is_liquid)
                moved += _transfer(spec, x, sources, liq_idx, deficit)
        # refinancing caps per bucket (upper bound)
        for bucket in set(int(b) for b in spec.year_bucket):
            idx = np.flatnonzero(spec.year_bucket == bucket)
            val = float(x[idx].sum())
            excess = val - spec.refi_cap_share * R
            if excess > 0:
                others = np.flatnonzero(spec.year_bucket != bucket)
                moved += _shed_and_fill(spec, x, idx, excess, np.zeros(spec.n_instruments, dtype=bool), target_set=others)
        if moved < 1e-6:
            break
        x = project_box_simplex(np.clip(x, 0.0, caps), caps, R)
    return project_box_simplex(np.clip(x, 0.0, caps), caps, R)


def _shed_and_fill(spec, x, source_idx, excess, target_mask, target_set=None):
    """Reduce ``excess`` from ``source_idx`` and refill into cheapest targets."""
    if excess <= 0:
        return 0.0
    caps = spec.capacity
    moved = 0.0
    # shed from most expensive sources first
    source_order = sorted(source_idx, key=lambda i: (float(spec.base_cost[i]), float(x[i])), reverse=True)
    need = excess
    for i in source_order:
        if need <= 0:
            break
        take = min(need, float(x[i]))
        x[i] -= take
        need -= take
        moved += take
    # refill into cheapest available targets with capacity
    if target_set is None:
        target_set = np.flatnonzero(target_mask)
    target_order = sorted(target_set, key=lambda i: (float(spec.base_cost[i]), caps[i] - float(x[i])))
    need = excess
    for i in target_order:
        if need <= 0:
            break
        room = caps[i] - x[i]
        if room <= 0:
            continue
        take = min(need, room)
        x[i] += take
        need -= take
    return moved


def _transfer(spec, x, sources, targets, amount):
    """Move ``amount`` from ``sources`` to ``targets`` greedily."""
    if amount <= 0:
        return 0.0
    caps = spec.capacity
    source_order = sorted(sources, key=lambda i: float(spec.base_cost[i]), reverse=True)
    target_order = sorted(targets, key=lambda i: float(spec.base_cost[i]))
    need = amount
    for i in source_order:
        if need <= 0:
            break
        take = min(need, float(x[i]))
        x[i] -= take
        need -= take
    need = amount
    for i in target_order:
        if need <= 0:
            break
        room = caps[i] - x[i]
        if room <= 0:
            continue
        take = min(need, room)
        x[i] += take
        need -= take
    return amount