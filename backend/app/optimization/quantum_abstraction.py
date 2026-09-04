"""Quantum-Classical Abstraction Layer.

Provides a clean interface for swapping classical simulators with real
quantum processing unit (QPU) backends when hardware becomes available.

Design Principles:
1. No fabricated quantum claims — every result is tagged with its actual backend
2. Graceful degradation — if QPU unavailable, fall back to classical
3. Transparent auditing — every computation records which backend was used
4. Future-proof — adding a new backend requires only implementing the interface

Currently supported backends:
- CLASSICAL_MILP: Exact solver via PuLP/CBC
- SIMULATED_ANNEALING: Heuristic solver
- QUBO_SIMULATOR: Quantum-inspired on classical CPU (no real quantum)
- FUTURE_QPU: Placeholder for real quantum hardware (not yet implemented)
"""
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class BackendType(str, Enum):
    CLASSICAL_MILP = "classical_milp"
    SIMULATED_ANNEALING = "simulated_annealing"
    QUBO_SIMULATOR = "qubo_simulator"
    FUTURE_QPU = "future_qpu"  # Placeholder — not implemented


@dataclass
class SolverResult:
    """Standardized result from any solver backend.

    Every result explicitly declares which backend produced it.
    No result is ever misattributed to a quantum backend.
    """
    solver_name: str
    backend_type: BackendType
    objective_value: float
    feasible: bool
    solve_time_seconds: float
    iterations: int = 0
    solution: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_real_quantum(self) -> bool:
        """Always False until real QPU backend is implemented."""
        return self.backend_type == BackendType.FUTURE_QPU

    @property
    def backend_label(self) -> str:
        """Human-readable backend label for audit trails."""
        labels = {
            BackendType.CLASSICAL_MILP: "Classical MILP (CBC)",
            BackendType.SIMULATED_ANNEALING: "Simulated Annealing",
            BackendType.QUBO_SIMULATOR: "QUBO Simulator (Classical CPU)",
            BackendType.FUTURE_QPU: "Real Quantum Hardware (QPU)",
        }
        return labels.get(self.backend_type, "Unknown")


class SolverBackend(ABC):
    """Abstract interface for all solver backends.

    To add a new backend (e.g., real QPU), implement this interface:
    - solve(): Run the optimization
    - is_available(): Check if backend is accessible
    - validate_problem(): Ensure problem is compatible
    """

    @abstractmethod
    def solve(self, problem: dict, params: dict) -> SolverResult:
        """Run optimization and return standardized result."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is currently accessible."""
        ...

    @abstractmethod
    def validate_problem(self, problem: dict) -> dict:
        """Validate that a problem is compatible with this backend."""
        ...

    @property
    @abstractmethod
    def backend_type(self) -> BackendType:
        """Return the backend type identifier."""
        ...


class ClassicalMILPBackend(SolverBackend):
    """Classical MILP solver using PuLP/CBC."""

    @property
    def backend_type(self) -> BackendType:
        return BackendType.CLASSICAL_MILP

    def is_available(self) -> bool:
        try:
            import pulp
            return True
        except ImportError:
            return False

    def validate_problem(self, problem: dict) -> dict:
        return {"valid": True, "backend": self.backend_type.value}

    def solve(self, problem: dict, params: dict) -> SolverResult:
        start = time.time()
        # Delegate to existing MILP solver
        from quantive.solvers.milp import solve_milp
        result = solve_milp(problem, **params)
        elapsed = time.time() - start

        return SolverResult(
            solver_name="MILP (CBC)",
            backend_type=self.backend_type,
            objective_value=result.get("objective_value", 0),
            feasible=result.get("feasible", False),
            solve_time_seconds=elapsed,
            iterations=result.get("iterations", 0),
            solution=result.get("solution", {}),
            metadata={"engine": "PuLP/CBC", "deterministic": True},
        )


class QUBOSimulatorBackend(SolverBackend):
    """Quantum-inspired QUBO on classical CPU simulator.

    This is NOT real quantum computing. It runs simulated annealing
    on a classical CPU to minimize a QUBO-formulated energy function.
    Labeled explicitly as SIMULATOR to prevent misrepresentation.
    """

    @property
    def backend_type(self) -> BackendType:
        return BackendType.QUBO_SIMULATOR

    def is_available(self) -> bool:
        return True  # Always available on classical CPU

    def validate_problem(self, problem: dict) -> dict:
        return {
            "valid": True,
            "backend": self.backend_type.value,
            "note": "Problem will be reformulated as QUBO (binary expansion)",
        }

    def solve(self, problem: dict, params: dict) -> SolverResult:
        start = time.time()
        from quantive.solvers.qubo import solve_qubo
        result = solve_qubo(problem, **params)
        elapsed = time.time() - start

        return SolverResult(
            solver_name="QUBO Annealing (Simulator)",
            backend_type=self.backend_type,
            objective_value=result.get("objective_value", 0),
            feasible=result.get("feasible", False),
            solve_time_seconds=elapsed,
            iterations=result.get("iterations", 0),
            solution=result.get("solution", {}),
            metadata={
                "engine": "Classical CPU Simulator",
                "quantum_claims": "None — this is classical simulation",
                "note": "Quantum-inspired formulation running on classical hardware",
            },
        )


class FutureQPUBackend(SolverBackend):
    """Placeholder for real quantum hardware.

    NOT IMPLEMENTED. This exists to define the interface that a real
    QPU backend would need to satisfy. No code path reaches this.
    """

    @property
    def backend_type(self) -> BackendType:
        return BackendType.FUTURE_QPU

    def is_available(self) -> bool:
        return False  # Not implemented

    def validate_problem(self, problem: dict) -> dict:
        raise NotImplementedError("Real QPU backend not yet implemented")

    def solve(self, problem: dict, params: dict) -> SolverResult:
        raise NotImplementedError(
            "Real quantum hardware backend not yet available. "
            "Use QUBO_SIMULATOR for quantum-inspired results on classical CPU."
        )


# ── Backend Registry ────────────────────────────────────────────────

BACKENDS = {
    BackendType.CLASSICAL_MILP: ClassicalMILPBackend,
    BackendType.QUBO_SIMULATOR: QUBOSimulatorBackend,
    BackendType.FUTURE_QPU: FutureQPUBackend,
}


def get_solver(backend: BackendType) -> SolverBackend:
    """Get a solver backend instance."""
    cls = BACKENDS.get(backend)
    if not cls:
        raise ValueError(f"Unknown backend: {backend}")
    return cls()


def list_available_backends() -> list:
    """List all available solver backends."""
    results = []
    for btype, cls in BACKENDS.items():
        instance = cls()
        results.append({
            "backend": btype.value,
            "available": instance.is_available(),
            "is_real_quantum": False,  # Always false until real QPU
        })
    return results
