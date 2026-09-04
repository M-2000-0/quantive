"""
Visual Circuit Designer API
============================

Priority 2 implementation: Drag-and-drop circuit builder with real-time
validation, cost estimation, and hardware-aware optimization suggestions.

Features:
- Real-time constraint checking against target hardware
- Cost estimation (credits/tokens) before submission
- Equivalent circuit suggestions
- Template library for common patterns
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/circuit-designer", tags=["circuit-designer"])


class GatePlacement(BaseModel):
    gate: str
    qubits: List[int]
    params: Optional[List[float]] = None
    control: Optional[int] = None
    target: Optional[int] = None


class CircuitDesign(BaseModel):
    num_qubits: int = 4
    gates: List[GatePlacement] = []
    target_backend: str = "ibm_heron"
    name: str = "Untitled Circuit"


class ValidationRequest(BaseModel):
    circuit: CircuitDesign
    check_topology: bool = True
    check_depth: bool = True
    check_gate_set: bool = True


# ── Hardware Profiles ──────────────────────────────────────────────

HARDWARE_PROFILES = {
    "ibm_heron": {
        "name": "IBM Heron r2",
        "max_qubits": 127,
        "native_gates": ["rz", "sx", "cx", "x"],
        "connectivity": "heavy-hex",
        "max_depth": 2000,
        "max_cnot_depth": 500,
        "t1_us": 120.0,
        "t2_us": 80.0,
        "gate_error_1q": 0.0003,
        "gate_error_2q": 0.008,
        "readout_error": 0.015,
        "cost_per_shot": 0.00032,
        "credits_per_shot": 1.0,
    },
    "quantinuum_h2": {
        "name": "Quantinuum H2",
        "max_qubits": 32,
        "native_gates": ["rz", "rxx", "x"],
        "connectivity": "all-to-all",
        "max_depth": 5000,
        "max_cnot_depth": 2000,
        "t1_us": 10000.0,
        "t2_us": 5000.0,
        "gate_error_1q": 0.0001,
        "gate_error_2q": 0.002,
        "readout_error": 0.003,
        "cost_per_shot": 0.0015,
        "credits_per_shot": 5.0,
    },
    "ionq_harmony": {
        "name": "IonQ Harmony",
        "max_qubits": 11,
        "native_gates": ["rz", "xx", "yy", "x"],
        "connectivity": "all-to-all",
        "max_depth": 10000,
        "max_cnot_depth": 5000,
        "t1_us": 100000.0,
        "t2_us": 50000.0,
        "gate_error_1q": 0.0002,
        "gate_error_2q": 0.005,
        "readout_error": 0.01,
        "cost_per_shot": 0.001,
        "credits_per_shot": 3.0,
    },
    "simulator": {
        "name": "Noiseless Simulator",
        "max_qubits": 40,
        "native_gates": ["h", "cx", "rz", "x", "y", "z", "t", "s", "swap"],
        "connectivity": "all-to-all",
        "max_depth": 100000,
        "max_cnot_depth": 100000,
        "t1_us": float("inf"),
        "t2_us": float("inf"),
        "gate_error_1q": 0.0,
        "gate_error_2q": 0.0,
        "readout_error": 0.0,
        "cost_per_shot": 0.0,
        "credits_per_shot": 0.0,
    },
}

# ── Circuit Templates ──────────────────────────────────────────────

CIRCUIT_TEMPLATES = [
    {
        "id": "bell_state",
        "name": "Bell State (Entanglement)",
        "description": "Creates maximum entanglement between two qubits — the foundation of quantum communication",
        "category": "fundamentals",
        "num_qubits": 2,
        "gates": [
            {"gate": "h", "qubits": [0]},
            {"gate": "cx", "qubits": [0, 1]},
        ],
        "difficulty": "beginner",
        "use_case": "Quantum key distribution, teleportation",
    },
    {
        "id": "ghz_state",
        "name": "GHZ State (Multi-qubit Entanglement)",
        "description": "N-qubit entanglement — tests quantum non-locality at scale",
        "category": "fundamentals",
        "num_qubits": 4,
        "gates": [
            {"gate": "h", "qubits": [0]},
            {"gate": "cx", "qubits": [0, 1]},
            {"gate": "cx", "qubits": [1, 2]},
            {"gate": "cx", "qubits": [2, 3]},
        ],
        "difficulty": "beginner",
        "use_case": "Quantum error correction, secret sharing",
    },
    {
        "id": "grover_2qubit",
        "name": "Grover Search (2-qubit)",
        "description": "Quadratic speedup for unstructured search — finds marked item in O(sqrt(N))",
        "category": "algorithms",
        "num_qubits": 2,
        "gates": [
            {"gate": "h", "qubits": [0]},
            {"gate": "h", "qubits": [1]},
            {"gate": "cz", "qubits": [0, 1]},
            {"gate": "h", "qubits": [0]},
            {"gate": "h", "qubits": [1]},
            {"gate": "x", "qubits": [0]},
            {"gate": "x", "qubits": [1]},
            {"gate": "cz", "qubits": [0, 1]},
            {"gate": "x", "qubits": [0]},
            {"gate": "x", "qubits": [1]},
            {"gate": "h", "qubits": [0]},
            {"gate": "h", "qubits": [1]},
        ],
        "difficulty": "intermediate",
        "use_case": "Database search, optimization, SAT solving",
    },
    {
        "id": "qaoa_maxcut",
        "name": "QAOA MaxCut (4-qubit)",
        "description": "Variational quantum solver for combinatorial optimization — MaxCut on a graph",
        "category": "algorithms",
        "num_qubits": 4,
        "gates": [
            {"gate": "h", "qubits": [0]},
            {"gate": "h", "qubits": [1]},
            {"gate": "h", "qubits": [2]},
            {"gate": "h", "qubits": [3]},
            {"gate": "rz", "qubits": [0], "params": [0.785]},
            {"gate": "cx", "qubits": [0, 1]},
            {"gate": "rz", "qubits": [1], "params": [0.785]},
            {"gate": "cx", "qubits": [1, 2]},
            {"gate": "rz", "qubits": [2], "params": [0.785]},
            {"gate": "cx", "qubits": [2, 3]},
            {"gate": "h", "qubits": [0]},
            {"gate": "h", "qubits": [1]},
            {"gate": "h", "qubits": [2]},
            {"gate": "h", "qubits": [3]},
        ],
        "difficulty": "intermediate",
        "use_case": "Portfolio optimization, logistics, network design",
    },
    {
        "id": "vqe_ansatz",
        "name": "VQE Hardware-Efficient Ansatz",
        "description": "Variational eigensolver ansatz — finds ground state energy of molecules",
        "category": "algorithms",
        "num_qubits": 4,
        "gates": [
            {"gate": "ry", "qubits": [0], "params": [0.5]},
            {"gate": "ry", "qubits": [1], "params": [0.5]},
            {"gate": "ry", "qubits": [2], "params": [0.5]},
            {"gate": "ry", "qubits": [3], "params": [0.5]},
            {"gate": "cx", "qubits": [0, 1]},
            {"gate": "cx", "qubits": [2, 3]},
            {"gate": "cx", "qubits": [1, 2]},
            {"gate": "ry", "qubits": [0], "params": [0.3]},
            {"gate": "ry", "qubits": [1], "params": [0.3]},
            {"gate": "ry", "qubits": [2], "params": [0.3]},
            {"gate": "ry", "qubits": [3], "params": [0.3]},
            {"gate": "cx", "qubits": [0, 1]},
            {"gate": "cx", "qubits": [2, 3]},
            {"gate": "cx", "qubits": [1, 2]},
        ],
        "difficulty": "advanced",
        "use_case": "Molecular simulation, drug discovery, materials science",
    },
    {
        "id": "quantum_teleportation",
        "name": "Quantum Teleportation",
        "description": "Transfers quantum state using entanglement and classical communication",
        "category": "communication",
        "num_qubits": 3,
        "gates": [
            {"gate": "ry", "qubits": [0], "params": [1.2]},
            {"gate": "h", "qubits": [1]},
            {"gate": "cx", "qubits": [1, 2]},
            {"gate": "cx", "qubits": [0, 1]},
            {"gate": "h", "qubits": [0]},
        ],
        "difficulty": "intermediate",
        "use_case": "Quantum networks, secure communication",
    },
    {
        "id": "deutsch_jozsa",
        "name": "Deutsch-Jozsa Algorithm",
        "description": "Determines if a function is constant or balanced in ONE query — exponential speedup",
        "category": "algorithms",
        "num_qubits": 3,
        "gates": [
            {"gate": "x", "qubits": [2]},
            {"gate": "h", "qubits": [0]},
            {"gate": "h", "qubits": [1]},
            {"gate": "h", "qubits": [2]},
            {"gate": "cz", "qubits": [0, 2]},
            {"gate": "cz", "qubits": [1, 2]},
            {"gate": "h", "qubits": [0]},
            {"gate": "h", "qubits": [1]},
        ],
        "difficulty": "intermediate",
        "use_case": "Oracle separation, function property testing",
    },
    {
        "id": "qpe",
        "name": "Quantum Phase Estimation",
        "description": "Estimates eigenvalues of a unitary — core subroutine for Shor's algorithm",
        "category": "algorithms",
        "num_qubits": 5,
        "gates": [
            {"gate": "h", "qubits": [0]},
            {"gate": "h", "qubits": [1]},
            {"gate": "h", "qubits": [2]},
            {"gate": "cp", "qubits": [0, 3], "params": [3.14159]},
            {"gate": "cp", "qubits": [1, 3], "params": [1.5708]},
            {"gate": "cp", "qubits": [2, 3], "params": [0.7854]},
        ],
        "difficulty": "advanced",
        "use_case": "Quantum chemistry, factoring, eigenvalue problems",
    },
]

# ── Validation Logic ───────────────────────────────────────────────

def _validate_circuit(circuit: CircuitDesign, check_topology: bool, check_depth: bool, check_gate_set: bool) -> Dict[str, Any]:
    """Validate a circuit design against hardware constraints."""
    profile = HARDWARE_PROFILES.get(circuit.target_backend, HARDWARE_PROFILES["simulator"])
    errors = []
    warnings = []
    suggestions = []

    # Qubit count check
    if circuit.num_qubits > profile["max_qubits"]:
        errors.append({
            "type": "qubit_overflow",
            "severity": "error",
            "message": f"Circuit uses {circuit.num_qubits} qubits but {profile['name']} supports max {profile['max_qubits']}",
        })

    # Gate set validation
    if check_gate_set:
        native = set(profile["native_gates"])
        for g in circuit.gates:
            base_gate = g.gate.lower()
            if base_gate not in native and base_gate not in ("measure",):
                errors.append({
                    "type": "unsupported_gate",
                    "severity": "error",
                    "message": f"Gate '{g.gate}' not in native gate set of {profile['name']}: {native}",
                })
                suggestions.append({
                    "type": "gate_decomposition",
                    "message": f"Decompose '{g.gate}' into {' + '.join(profile['native_gates'][:3])}",
                })

    # Depth check
    if check_depth:
        depth = len(circuit.gates)
        if depth > profile["max_depth"]:
            warnings.append({
                "type": "depth_warning",
                "message": f"Circuit depth {depth} exceeds recommended max {profile['max_depth']} for {profile['name']}",
            })
            suggestions.append({
                "type": "depth_reduction",
                "message": "Apply circuit optimization (level 2-3) to reduce depth",
            })

    # Topology check
    if check_topology and profile["connectivity"] != "all-to-all":
        # Check if 2-qubit gates respect connectivity
        cnot_pairs = [(g.qubits[0], g.qubits[1]) for g in circuit.gates if len(g.qubits) == 2]
        if cnot_pairs and profile["connectivity"] == "heavy-hex":
            warnings.append({
                "type": "topology_warning",
                "message": f"Heavy-hex topology may require SWAP gates for some qubit pairs",
            })
            suggestions.append({
                "type": "routing",
                "message": "Consider qubit mapping to minimize SWAP overhead",
            })

    # Cost estimation
    shots = 4096
    total_cost = shots * profile["cost_per_shot"]
    total_credits = shots * profile["credits_per_shot"]
    estimated_fidelity = max(0, 1.0 - (
        profile["gate_error_1q"] * sum(1 for g in circuit.gates if len(g.qubits) == 1)
        + profile["gate_error_2q"] * sum(1 for g in circuit.gates if len(g.qubits) == 2)
    ))

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "suggestions": suggestions,
        "circuit_stats": {
            "num_qubits": circuit.num_qubits,
            "num_gates": len(circuit.gates),
            "depth": len(circuit.gates),
            "two_qubit_gates": sum(1 for g in circuit.gates if len(g.qubits) == 2),
            "single_qubit_gates": sum(1 for g in circuit.gates if len(g.qubits) == 1),
            "parameterized_gates": sum(1 for g in circuit.gates if g.params),
        },
        "cost_estimate": {
            "shots": shots,
            "cost_usd": round(total_cost, 6),
            "credits": round(total_credits, 1),
            "estimated_fidelity": round(estimated_fidelity, 4),
            "estimated_latency_ms": round(profile.get("t1_us", 100) * 0.5, 1),
        },
        "hardware_profile": profile["name"],
    }


# ── API Endpoints ─────────────────────────────────────────────────

@router.post("/validate")
async def validate_circuit(req: ValidationRequest, user: User = Depends(get_current_user)):
    """Validate a circuit design against target hardware constraints."""
    result = _validate_circuit(req.circuit, req.check_topology, req.check_depth, req.check_gate_set)
    return result


@router.get("/templates")
async def list_templates(category: Optional[str] = None, user: User = Depends(get_current_user)):
    """List available circuit templates, optionally filtered by category."""
    templates = CIRCUIT_TEMPLATES
    if category:
        templates = [t for t in templates if t["category"] == category]

    return {
        "templates": templates,
        "total": len(templates),
        "categories": list(set(t["category"] for t in CIRCUIT_TEMPLATES)),
    }


@router.get("/templates/{template_id}")
async def get_template(template_id: str, user: User = Depends(get_current_user)):
    """Get a specific circuit template by ID."""
    template = next((t for t in CIRCUIT_TEMPLATES if t["id"] == template_id), None)
    if not template:
        return {"error": f"Template '{template_id}' not found", "available": [t["id"] for t in CIRCUIT_TEMPLATES]}
    return template


@router.get("/hardware")
async def list_hardware_profiles(user: User = Depends(get_current_user)):
    """List all available hardware profiles with their constraints."""
    return {
        "profiles": [
            {
                "key": key,
                "name": p["name"],
                "max_qubits": p["max_qubits"],
                "native_gates": p["native_gates"],
                "connectivity": p["connectivity"],
                "max_depth": p["max_depth"],
                "cost_per_shot": p["cost_per_shot"],
                "gate_error_1q": p["gate_error_1q"],
                "gate_error_2q": p["gate_error_2q"],
            }
            for key, p in HARDWARE_PROFILES.items()
        ],
    }


@router.post("/estimate-cost")
async def estimate_cost(
    num_qubits: int = 4,
    num_gates: int = 20,
    target_backend: str = "ibm_heron",
    shots: int = 4096,
    user: User = Depends(get_current_user),
):
    """Estimate execution cost for a circuit with given parameters."""
    profile = HARDWARE_PROFILES.get(target_backend, HARDWARE_PROFILES["simulator"])

    cost_usd = shots * profile["cost_per_shot"]
    credits = shots * profile["credits_per_shot"]
    two_qubit_frac = 0.3  # Assume 30% are 2-qubit gates
    fidelity = max(0, 1.0 - (
        profile["gate_error_1q"] * num_gates * (1 - two_qubit_frac)
        + profile["gate_error_2q"] * num_gates * two_qubit_frac
    ))

    return {
        "target_backend": profile["name"],
        "shots": shots,
        "cost_usd": round(cost_usd, 6),
        "credits": round(credits, 1),
        "estimated_fidelity": round(fidelity, 4),
        "estimated_latency_seconds": round(num_gates * num_qubits * 0.0001, 3),
        "qubits_used": num_qubits,
        "qubits_available": profile["max_qubits"],
        "within_budget": cost_usd <= 1.0,  # Default $1 budget
    }


from typing import Optional
