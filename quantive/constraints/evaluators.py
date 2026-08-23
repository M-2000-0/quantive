"""Constraint evaluation and penalty computation.

Constraint semantics live in :class:`ProblemSpec`; this module exposes thin
helpers used by stochastic solvers and the benchmark engine.
"""
from __future__ import annotations

import numpy as np

from quantive.objectives.spec import ProblemSpec


def penalty(x: np.ndarray, spec: ProblemSpec) -> float:
    """Weighted total constraint-violation magnitude for stochastic solvers."""
    total = 0.0
    for s in spec.constraint_violations(x):
        if not s.satisfied:
            total += s.violation
    return total * spec.penalty