"""Histogram helpers for cost distributions."""
from __future__ import annotations

from typing import List

import numpy as np


def cost_histogram(costs: np.ndarray, bins: int = 20) -> List[float]:
    """Return bin counts of the cost distribution (for visualization)."""
    if costs.size == 0:
        return []
    counts, _ = np.histogram(costs, bins=bins)
    return [int(c) for c in counts]