"""Quantum-inspired optimization — §23-24."""

from quantive.quantum.backend import (
    ClassicalSimulatorBackend,
    QuantumBackend,
    QuantumInspiredBackend,
    QuantumProblem,
    QuantumResult,
    QiskitBackend,
    get_quantum_backend,
)

__all__ = [
    "QuantumBackend",
    "QuantumProblem",
    "QuantumResult",
    "ClassicalSimulatorBackend",
    "QuantumInspiredBackend",
    "QiskitBackend",
    "get_quantum_backend",
]
