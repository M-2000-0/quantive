"""Quantum backend abstraction — §24.

ClassicalSimulator / QuantumInspired / Qiskit backends share one optimize() interface.
No fabricated quantum performance. Comparison is empirical via benchmark.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

import numpy as np


@dataclass
class QuantumProblem:
    """Generic portfolio optimization as QUBO-ish: maximize return - penalties."""
    expected_returns: np.ndarray  # (N,)
    cov: np.ndarray  # (N,N)
    risk_penalty: float = 1.0
    concentration_penalty: float = 0.5
    transaction_cost_penalty: float = 0.1
    max_position: float = 0.3


@dataclass
class QuantumResult:
    weights: np.ndarray
    objective: float
    backend: str
    solver_type: str
    feasible: bool
    metadata: dict


class QuantumBackend(ABC):
    @abstractmethod
    def optimize(self, problem: QuantumProblem) -> QuantumResult: ...

    @property
    @abstractmethod
    def name(self) -> str: ...


class ClassicalSimulatorBackend(QuantumBackend):
    """Exact classical mean-variance via closed form (baseline)."""

    @property
    def name(self) -> str:
        return "classical_simulator"

    def optimize(self, problem: QuantumProblem) -> QuantumResult:
        from quantive.portfolio.optimizer import PortfolioOptimizer
        opt = PortfolioOptimizer()
        w = opt.mean_variance(problem.expected_returns, problem.cov, risk_aversion=problem.risk_penalty)
        # concentration penalty already via box; compute objective
        ret = float(problem.expected_returns @ w)
        risk = float(w @ problem.cov @ w)
        conc = float(np.sum(w**2))
        obj = ret - problem.risk_penalty * risk - problem.concentration_penalty * conc
        return QuantumResult(weights=w, objective=obj, backend="classical_cpu", solver_type="classical", feasible=True, metadata={"method": "mean_variance"})


class QuantumInspiredBackend(QuantumBackend):
    """QUBO-inspired annealing (simulator) — wraps existing qubo solver concept."""

    @property
    def name(self) -> str:
        return "quantum_inspired"

    def optimize(self, problem: QuantumProblem) -> QuantumResult:
        # reuse qubo-style bit annealer at portfolio level (small N)
        n = len(problem.expected_returns)
        rng = np.random.default_rng(42)
        best_w = np.ones(n) / n
        best_obj = -1e9
        # simple random search with annealing (honest simulator, not claimed quantum hardware)
        for _ in range(5000):
            w = rng.dirichlet(np.ones(n) * 2)
            w = np.clip(w, 0, problem.max_position)
            if w.sum() == 0:
                continue
            w = w / w.sum()
            ret = float(problem.expected_returns @ w)
            risk = float(w @ problem.cov @ w)
            conc = float(np.sum(w**2))
            obj = ret - problem.risk_penalty * risk - problem.concentration_penalty * conc
            if obj > best_obj:
                best_obj = obj
                best_w = w
        return QuantumResult(weights=best_w, objective=best_obj, backend="simulator", solver_type="quantum_inspired", feasible=True, metadata={"iterations": 5000, "execution": "SIMULATOR (classical CPU)"})


class QiskitBackend(QuantumBackend):
    """Placeholder for real Qiskit hardware — raises if not installed; never fabricates."""

    @property
    def name(self) -> str:
        return "qiskit"

    def optimize(self, problem: QuantumProblem) -> QuantumResult:
        try:
            import qiskit  # noqa: F401
        except ImportError as e:
            raise RuntimeError("Qiskit not installed — cannot route to real quantum hardware. Install qiskit to enable.") from e
        # Real implementation would build QUBO and call QAOA; stub returns classical
        return ClassicalSimulatorBackend().optimize(problem)


def get_quantum_backend(name: str) -> QuantumBackend:
    mapping = {
        "classical": ClassicalSimulatorBackend(),
        "classical_simulator": ClassicalSimulatorBackend(),
        "quantum_inspired": QuantumInspiredBackend(),
        "qiskit": QiskitBackend(),
    }
    if name not in mapping:
        raise KeyError(f"Unknown quantum backend {name!r}. Choose from {list(mapping)}")
    return mapping[name]
