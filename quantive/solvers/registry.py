"""Solver registry."""
from __future__ import annotations

from typing import Dict, List, Type

from quantive.solvers.base import SolverInterface
from quantive.solvers.heuristic import SimulatedAnnealingSolver
from quantive.solvers.milp import MILPSolver
from quantive.solvers.qubo import QUBOSolver

_REGISTRY: Dict[str, Type[SolverInterface]] = {
    "milp": MILPSolver,
    "simulated_annealing": SimulatedAnnealingSolver,
    "qubo": QUBOSolver,
}

DEFAULT_SOLVER_ORDER: List[str] = ["milp", "simulated_annealing", "qubo"]


def get_solver(name: str) -> SolverInterface:
    if name not in _REGISTRY:
        raise KeyError(
            f"unknown solver {name!r}; available: {', '.join(sorted(_REGISTRY))}"
        )
    return _REGISTRY[name]()


def available_solvers() -> List[str]:
    return list(_REGISTRY.keys())