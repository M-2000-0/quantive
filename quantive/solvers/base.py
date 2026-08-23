"""Solver interface and shared result construction.

Every solver consumes a compiled :class:`ProblemSpec` and returns a
:class:`SolveResult` with comparable metrics. Solvers must never fabricate
performance: the execution backend is reported truthfully and optimality
guarantees are only claimed when the underlying method actually establishes
them.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from quantive.models.enums import ExecutionBackend, SolverType
from quantive.models.optimization import SolverConfiguration
from quantive.models.results import ConstraintStatus, RiskMetrics
from quantive.objectives.spec import ProblemSpec


@dataclass
class SolveResult:
    """Canonical output of any solver on the same problem."""

    solver: str
    solver_type: SolverType
    execution_backend: ExecutionBackend
    allocation: Dict[str, float]
    feasible: bool
    objective_value: float
    financing_cost: float
    risk_metrics: RiskMetrics
    constraint_status: List[ConstraintStatus]
    objective_decomposition: Dict[str, float]
    runtime: float
    iterations: Optional[int] = None
    objective_evaluations: Optional[int] = None
    optimality_note: str = ""
    metadata: Dict = field(default_factory=dict)


def build_result(
    spec: ProblemSpec,
    allocation: Dict[str, float],
    solver: str,
    solver_type: SolverType,
    backend: ExecutionBackend,
    runtime: float,
    iterations: Optional[int] = None,
    objective_evaluations: Optional[int] = None,
    optimality_note: str = "",
    metadata: Optional[Dict] = None,
) -> SolveResult:
    """Build a ``SolveResult`` from an allocation, evaluating all canonical metrics."""
    x = np.array([allocation.get(iid, 0.0) for iid in spec.instrument_ids], dtype=float)
    feasible, n_viol, total_viol = spec.feasibility(x)
    statuses = spec.constraint_violations(x)
    if not feasible:
        optimality_note = (optimality_note + " | INFEASIBLE").strip()
    return SolveResult(
        solver=solver,
        solver_type=solver_type,
        execution_backend=backend,
        allocation=dict(allocation),
        feasible=feasible,
        objective_value=spec.objective_value(x),
        financing_cost=spec.expected_cost(x),
        risk_metrics=spec.risk_metrics(x),
        constraint_status=statuses,
        objective_decomposition=spec.objective_decomposition(x),
        runtime=runtime,
        iterations=iterations,
        objective_evaluations=objective_evaluations,
        optimality_note=optimality_note,
        metadata=metadata or {},
    )


class SolverInterface(ABC):
    """Abstract optimization solver."""

    name: str = "solver"
    solver_type: SolverType = SolverType.CLASSICAL
    execution_backend: ExecutionBackend = ExecutionBackend.CLASSICAL_CPU

    @abstractmethod
    def solve(self, spec: ProblemSpec, config: SolverConfiguration) -> SolveResult:
        """Solve the problem and return a canonical result."""
        raise NotImplementedError


def allocation_from_vector(spec: ProblemSpec, x: np.ndarray) -> Dict[str, float]:
    return {iid: float(v) for iid, v in zip(spec.instrument_ids, x) if abs(v) > 1e-9}


def violation_magnitude(spec: ProblemSpec, x: np.ndarray) -> float:
    """Total constraint-violation magnitude (0 when feasible)."""
    return spec.violation_magnitude(x)