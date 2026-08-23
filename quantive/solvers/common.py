"""Shared numeric helpers for stochastic solvers."""
from __future__ import annotations

import numpy as np


def project_box_simplex(x: np.ndarray, caps: np.ndarray, total: float) -> np.ndarray:
    """Project ``x`` onto {0 <= x <= caps, sum(x) == total} by bisection."""
    x = np.clip(x, 0.0, caps)
    if x.sum() <= 0:
        return x
    if abs(x.sum() - total) < 1e-9:
        return x
    lo, hi = -caps.max() - 1.0, caps.max() + 1.0
    for _ in range(120):
        lam = 0.5 * (lo + hi)
        cand = np.clip(x - lam, 0.0, caps)
        s = cand.sum()
        if s > total:
            lo = lam
        else:
            hi = lam
    return np.clip(x - hi, 0.0, caps)


def ladder_initial(spec) -> np.ndarray:
    """Greedy initial allocation: fill the target maturity ladder bucket by
    bucket using the cheapest instruments, then mop up the remainder.

    Produces an allocation close to the target profile with near-minimal
    refinancing risk, giving stochastic solvers a strong starting point.
    """
    R = spec.financing_requirement
    caps = spec.capacity.copy()
    x = np.zeros(spec.n_instruments)
    buckets = {}
    for i, b in enumerate(spec.year_bucket):
        buckets.setdefault(int(b), []).append(i)
    remaining = R
    for bucket, share in spec.target_maturity_share.items():
        target = share * R
        idx = sorted(buckets.get(bucket, []), key=lambda i: float(spec.base_cost[i]))
        alloc = min(target, sum(caps[i] for i in idx))
        for i in idx:
            take = min(caps[i], alloc)
            x[i] += take
            caps[i] -= take
            alloc -= take
            remaining -= take
            if alloc <= 0:
                break
    if remaining > 0:
        for i in sorted(range(spec.n_instruments), key=lambda i: float(spec.base_cost[i])):
            if remaining <= 0:
                break
            take = min(caps[i], remaining)
            x[i] += take
            caps[i] -= take
            remaining -= take
    return project_box_simplex(x, spec.capacity, R)