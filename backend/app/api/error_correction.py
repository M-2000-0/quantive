"""
Production-Grade Error Correction Layer
========================================

Priority 4 implementation: Abstract the complexity of quantum error
correction behind a simple API.

Features:
- Fault-tolerance API: accept logical circuits, handle physical mapping
- Error correction method selection (surface code, repetition code, etc.)
- Reliability scoring per execution
- Hardware-specific QEC parameter tuning
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/error-correction", tags=["error-correction"])


class QECRequest(BaseModel):
    num_logical_qubits: int = 4
    target_logical_error_rate: float = 1e-6
    physical_error_rate: float = 0.001
    method: str = "auto"  # auto, surface_code, repetition_code, color_code
    backend: str = "ibm_heron"


class ReliabilityRequest(BaseModel):
    num_qubits: int = 4
    circuit_depth: int = 50
    physical_error_rate: float = 0.001
    qec_enabled: bool = True
    qec_method: Optional[str] = None
    backend: str = "ibm_heron"


# ── QEC Methods ────────────────────────────────────────────────────

QEC_METHODS = {
    "surface_code": {
        "name": "Surface Code",
        "description": "Leading fault-tolerant error correction code. Uses a 2D lattice of physical qubits to encode each logical qubit.",
        "overhead_factor": 25,  # Physical qubits per logical qubit (distance-5)
        "threshold_error_rate": 0.01,
        "logical_error_rate_formula": "p_L = 0.1 * (p / p_th)^((d+1)/2)",
        "strengths": [
            "Highest known error threshold (~1%)",
            "Local stabilizer measurements",
            "Well-studied decoding algorithms",
        ],
        "weaknesses": [
            "High qubit overhead (17-25 physical per logical at distance 5)",
            "Requires 2D connectivity",
            "Decoding latency can be significant",
        ],
        "best_for": "General-purpose fault-tolerant computation",
        "companies_using": ["Google", "IBM", "Quantinuum"],
        "status": "production_ready",
    },
    "repetition_code": {
        "name": "Repetition Code",
        "description": "Simplest quantum error correction — protects against bit-flip errors only. Good for demonstration and testing.",
        "overhead_factor": 3,
        "threshold_error_rate": 0.5,
        "logical_error_rate_formula": "p_L = C(d, t) * p^t where t = (d+1)/2",
        "strengths": [
            "Minimal overhead (d physical per logical qubit)",
            "Simple implementation and decoding",
            "Fast syndrome extraction",
        ],
        "weaknesses": [
            "Only corrects bit-flip (X) errors",
            "Does not protect against phase-flip (Z) errors",
            "Limited practical utility",
        ],
        "best_for": "Educational purposes, testing, simple memory experiments",
        "companies_using": ["IBM (research)"],
        "status": "research",
    },
    "color_code": {
        "name": "Color Code",
        "description": "Topological code that supports transversal gates for a wider gate set than surface code.",
        "overhead_factor": 18,
        "threshold_error_rate": 0.008,
        "logical_error_rate_formula": "Similar to surface code with improved constant factors",
        "strengths": [
            "Transversal T-gate (no magic state distillation needed)",
            "Higher encoding rate than surface code",
            "Supports fault-tolerant Clifford+T computation",
        ],
        "weaknesses": [
            "Requires 3-colorable lattice connectivity",
            "More complex stabilizer measurements",
            "Slightly lower threshold than surface code",
        ],
        "best_for": "Algorithms requiring T-gates (Shor's, quantum chemistry)",
        "companies_using": ["Quantinuum (research)"],
        "status": "research",
    },
}


# ── QEC Engine ─────────────────────────────────────────────────────

def _select_best_method(
    num_logical_qubits: int, physical_error_rate: float, target_logical_error_rate: float, backend: str
) -> Tuple[str, Dict[str, Any]]:
    """Automatically select the best QEC method."""
    if physical_error_rate > 0.01:
        return "none", {
            "reason": "Physical error rate too high for error correction",
            "recommendation": "Improve hardware before applying QEC",
        }

    # Auto-select based on requirements
    if target_logical_error_rate > 1e-3:
        # Loose requirement — repetition code sufficient
        method = "repetition_code"
    elif target_logical_error_rate > 1e-8:
        # Moderate requirement — surface code
        method = "surface_code"
    else:
        # Tight requirement — surface code with high distance
        method = "surface_code"

    # Backend-specific tuning
    tuning = _get_backend_tuning(method, backend)

    return method, tuning


def _get_backend_tuning(method: str, backend: str) -> Dict[str, Any]:
    """Get hardware-specific QEC parameters."""
    backend_params = {
        "ibm_heron": {
            "physical_error_rate": 0.008,
            "connectivity": "heavy-hex",
            "native_code_distance": 5,
            "max_code_distance": 7,
            "syndrome_extraction_rounds": 10,
            "decoder": "Union-Find",
            "decoder_latency_us": 1.0,
        },
        "quantinuum_h2": {
            "physical_error_rate": 0.002,
            "connectivity": "all-to-all",
            "native_code_distance": 7,
            "max_code_distance": 11,
            "syndrome_extraction_rounds": 5,
            "decoder": "MWPM",
            "decoder_latency_us": 0.5,
        },
        "google_willow": {
            "physical_error_rate": 0.005,
            "connectivity": "heavy-hex",
            "native_code_distance": 5,
            "max_code_distance": 9,
            "syndrome_extraction_rounds": 8,
            "decoder": "PyMatching",
            "decoder_latency_us": 0.8,
        },
    }

    params = backend_params.get(backend, backend_params["ibm_heron"])
    method_info = QEC_METHODS.get(method, QEC_METHODS["surface_code"])

    # Calculate required code distance
    p_phys = params["physical_error_rate"]
    p_th = method_info["threshold_error_rate"]
    if p_phys < p_th:
        # Solve for distance: p_L ≈ 0.1 * (p/p_th)^((d+1)/2)
        # For target p_L, find minimum d
        target_pL = 1e-6
        if p_phys > 0:
            ratio = p_phys / p_th
            if ratio > 0 and ratio < 1:
                d = max(3, int(2 * math.log(target_pL / 0.1) / math.log(ratio)) - 1)
                d = min(d, params["max_code_distance"])
                d = d if d % 2 == 1 else d + 1  # Must be odd
            else:
                d = params["max_code_distance"]
        else:
            d = 3
    else:
        d = params["max_code_distance"]

    physical_qubits_per_logical = d * d  # Surface code: d^2 physical qubits
    if method == "repetition_code":
        physical_qubits_per_logical = d

    return {
        "method": method,
        "method_name": method_info["name"],
        "code_distance": d,
        "physical_qubits_per_logical": physical_qubits_per_logical,
        "total_physical_qubits": physical_qubits_per_logical * 4,  # For 4 logical qubits
        "physical_error_rate": params["physical_error_rate"],
        "threshold_error_rate": method_info["threshold_error_rate"],
        "decoder": params["decoder"],
        "decoder_latency_us": params["decoder_latency_us"],
        "syndrome_extraction_rounds": params["syndrome_extraction_rounds"],
        "estimated_logical_error_rate": _estimate_logical_error_rate(
            params["physical_error_rate"], p_th, d
        ),
        "backend_connectivity": params["connectivity"],
    }


def _estimate_logical_error_rate(p_phys: float, p_th: float, d: int) -> float:
    """Estimate logical error rate from physical error rate and code distance."""
    if p_phys <= 0 or p_th <= 0:
        return 0.0
    ratio = p_phys / p_th
    if ratio >= 1:
        return 1.0  # Above threshold — QEC fails
    return 0.1 * (ratio ** ((d + 1) / 2))


def _compute_reliability(
    num_qubits: int, circuit_depth: int, physical_error_rate: float,
    qec_enabled: bool, qec_method: Optional[str], backend: str,
) -> Dict[str, Any]:
    """Compute reliability metrics for a circuit execution."""
    # Without QEC
    no_qec_fidelity = (1 - physical_error_rate) ** (num_qubits * circuit_depth)
    no_qec_error_rate = 1 - no_qec_fidelity

    if qec_enabled:
        if qec_method and qec_method != "auto":
            method = qec_method
        else:
            method, _ = _select_best_method(num_qubits, physical_error_rate, 1e-6, backend)

        method_info = QEC_METHODS.get(method, QEC_METHODS["surface_code"])
        tuning = _get_backend_tuning(method, backend)

        logical_error_rate = tuning["estimated_logical_error_rate"]
        qec_fidelity = (1 - logical_error_rate) ** (num_qubits * circuit_depth)
        overhead = tuning["physical_qubits_per_logical"]
        total_physical = overhead * num_qubits

        # Syndrome extraction adds to circuit depth
        syndrome_depth = circuit_depth + tuning["syndrome_extraction_rounds"] * circuit_depth
    else:
        logical_error_rate = physical_error_rate
        qec_fidelity = no_qec_fidelity
        overhead = 1
        total_physical = num_qubits
        syndrome_depth = circuit_depth

    improvement = ((qec_fidelity - no_qec_fidelity) / max(no_qec_fidelity, 1e-10)) * 100

    return {
        "reliability_score": round(qec_fidelity * 100, 2),
        "without_qec": {
            "fidelity": round(no_qec_fidelity, 6),
            "error_rate": round(no_qec_error_rate, 6),
        },
        "with_qec": {
            "enabled": qec_enabled,
            "method": method if qec_enabled else "none",
            "fidelity": round(qec_fidelity, 6),
            "logical_error_rate": round(logical_error_rate, 8),
            "code_distance": tuning.get("code_distance", 0) if qec_enabled else 0,
            "physical_qubits_per_logical": overhead,
            "total_physical_qubits": total_physical,
            "syndrome_depth": syndrome_depth,
            "decoder": tuning.get("decoder", "none"),
        },
        "improvement_pct": round(improvement, 1),
        "rating": (
            "production_ready" if qec_fidelity > 0.999
            else "usable" if qec_fidelity > 0.99
            else "marginal" if qec_fidelity > 0.95
            else "insufficient"
        ),
    }


# ── API Endpoints ─────────────────────────────────────────────────

@router.post("/configure")
async def configure_qec(req: QECRequest, user: User = Depends(get_current_user)):
    """Configure error correction for a circuit and get optimal parameters."""
    if req.method == "auto":
        method, tuning = _select_best_method(
            req.num_logical_qubits, req.physical_error_rate,
            req.target_logical_error_rate, req.backend,
        )
    else:
        method = req.method
        tuning = _get_backend_tuning(method, req.backend)

    method_info = QEC_METHODS.get(method, {})

    return {
        "selected_method": method,
        "method_info": method_info,
        "tuning": tuning,
        "estimated_logical_error_rate": tuning.get("estimated_logical_error_rate", 0),
        "physical_qubits_needed": tuning.get("total_physical_qubits", 0),
        "satisfies_target": tuning.get("estimated_logical_error_rate", 1) <= req.target_logical_error_rate,
    }


@router.post("/reliability")
async def compute_reliability(req: ReliabilityRequest, user: User = Depends(get_current_user)):
    """Compute reliability score for a circuit with optional QEC."""
    result = _compute_reliability(
        req.num_qubits, req.circuit_depth, req.physical_error_rate,
        req.qec_enabled, req.qec_method, req.backend,
    )
    return result


@router.get("/methods")
async def list_qec_methods(user: User = Depends(get_current_user)):
    """List all available error correction methods with details."""
    return {
        "methods": [
            {
                "key": key,
                "name": m["name"],
                "description": m["description"],
                "overhead_factor": m["overhead_factor"],
                "threshold_error_rate": m["threshold_error_rate"],
                "strengths": m["strengths"],
                "weaknesses": m["weaknesses"],
                "best_for": m["best_for"],
                "status": m["status"],
            }
            for key, m in QEC_METHODS.items()
        ],
        "default": "surface_code",
        "auto_select": "Automatically choose the best method based on hardware and requirements",
    }


@router.get("/backend-params/{backend}")
async def get_backend_qec_params(backend: str, user: User = Depends(get_current_user)):
    """Get QEC parameters for a specific hardware backend."""
    params = _get_backend_tuning("surface_code", backend)
    return {
        "backend": backend,
        "parameters": params,
        "recommendation": (
            "Use surface code with auto-tuned distance" if params.get("physical_error_rate", 0) < 0.01
            else "Improve hardware error rates before applying QEC"
        ),
    }
