"""
Quantum Algorithm Marketplace
==============================

Priority 3 implementation: Curated marketplace for quantum algorithms,
templates, and application blueprints.

Features:
- Browse and discover quantum algorithms by category
- Versioning, dependency management, cross-platform compatibility
- Benchmarking data per algorithm across hardware backends
- Publish and share custom algorithms
"""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/algorithm-marketplace", tags=["algorithm-marketplace"])


class AlgorithmPublish(BaseModel):
    name: str
    description: str
    category: str
    qasm3_code: str
    num_qubits: int
    difficulty: str = "intermediate"
    tags: List[str] = []
    dependencies: List[str] = []
    license: str = "MIT"


# ── Curated Algorithm Library ──────────────────────────────────────

ALGORITHMS = [
    {
        "id": "vqe-molecular",
        "name": "VQE Molecular Ground State",
        "version": "2.1.0",
        "author": "Quantive Research",
        "category": "chemistry",
        "description": "Variational Quantum Eigensolver for finding molecular ground state energy. Uses hardware-efficient ansatz with COBYLA optimizer.",
        "num_qubits": 4,
        "difficulty": "advanced",
        "tags": ["variational", "chemistry", "ground-state"],
        "dependencies": [],
        "license": "MIT",
        "platforms": ["ibm_heron", "quantinuum_h2", "ionq_harmony"],
        "benchmarks": {
            "ibm_heron": {"depth": 48, "fidelity": 0.94, "latency_ms": 120, "cost_usd": 0.005},
            "quantinuum_h2": {"depth": 48, "fidelity": 0.98, "latency_ms": 300, "cost_usd": 0.012},
            "ionq_harmony": {"depth": 48, "fidelity": 0.96, "latency_ms": 500, "cost_usd": 0.008},
        },
        "downloads": 1247,
        "rating": 4.7,
        "last_updated": "2026-08-15",
        "qasm3_preview": "OPENQASM 3.0;\n// VQE ansatz - 4 qubits\nqubit[4] q;\nbit[4] c;\nry(0.5) q[0];\nry(0.5) q[1];\n...",
    },
    {
        "id": "qaoa-maxcut",
        "name": "QAOA MaxCut Solver",
        "version": "3.0.1",
        "author": "Quantive Research",
        "category": "optimization",
        "description": "Quantum Approximate Optimization Algorithm for MaxCut on arbitrary graphs. Configurable depth p.",
        "num_qubits": 8,
        "difficulty": "intermediate",
        "tags": ["optimization", "combinatorial", "graph"],
        "dependencies": [],
        "license": "MIT",
        "platforms": ["ibm_heron", "quantinuum_h2", "simulator"],
        "benchmarks": {
            "ibm_heron": {"depth": 120, "fidelity": 0.91, "latency_ms": 250, "cost_usd": 0.012},
            "quantinuum_h2": {"depth": 120, "fidelity": 0.97, "latency_ms": 600, "cost_usd": 0.028},
            "simulator": {"depth": 120, "fidelity": 1.0, "latency_ms": 50, "cost_usd": 0.0},
        },
        "downloads": 2103,
        "rating": 4.8,
        "last_updated": "2026-08-28",
        "qasm3_preview": "OPENQASM 3.0;\n// QAOA p=2 MaxCut\nqubit[8] q;\nbit[8] c;\nh q[0];\n...",
    },
    {
        "id": "grover-search",
        "name": "Grover's Search Algorithm",
        "version": "2.0.0",
        "author": "Quantive Research",
        "category": "search",
        "description": "Quadratic speedup for unstructured search. Finds marked item in O(sqrt(N)) queries.",
        "num_qubits": 6,
        "difficulty": "intermediate",
        "tags": ["search", "oracle", "amplitude-amplification"],
        "dependencies": [],
        "license": "MIT",
        "platforms": ["ibm_heron", "quantinuum_h2", "ionq_harmony", "simulator"],
        "benchmarks": {
            "ibm_heron": {"depth": 84, "fidelity": 0.93, "latency_ms": 180, "cost_usd": 0.008},
            "quantinuum_h2": {"depth": 84, "fidelity": 0.99, "latency_ms": 400, "cost_usd": 0.020},
            "simulator": {"depth": 84, "fidelity": 1.0, "latency_ms": 20, "cost_usd": 0.0},
        },
        "downloads": 3456,
        "rating": 4.9,
        "last_updated": "2026-07-10",
        "qasm3_preview": "OPENQASM 3.0;\n// Grover search 6-qubit\nqubit[6] q;\nbit[6] c;\n...",
    },
    {
        "id": "shor-factoring",
        "name": "Shor's Factoring (Demo)",
        "version": "1.0.0",
        "author": "Quantive Research",
        "category": "cryptography",
        "description": "Demonstration of Shor's algorithm for integer factoring. Uses QPE + modular exponentiation.",
        "num_qubits": 8,
        "difficulty": "advanced",
        "tags": ["factoring", "cryptography", "period-finding"],
        "dependencies": ["qpe"],
        "license": "MIT",
        "platforms": ["simulator"],
        "benchmarks": {
            "simulator": {"depth": 500, "fidelity": 1.0, "latency_ms": 200, "cost_usd": 0.0},
        },
        "downloads": 892,
        "rating": 4.5,
        "last_updated": "2026-06-01",
        "qasm3_preview": "OPENQASM 3.0;\n// Shor's algorithm demo\nqubit[8] q;\nbit[8] c;\n...",
    },
    {
        "id": "qpe-eigenvalue",
        "name": "Quantum Phase Estimation",
        "version": "1.5.0",
        "author": "Quantive Research",
        "category": "primitives",
        "description": "Core subroutine for estimating eigenvalues of unitary operators. Foundation for Shor's, quantum chemistry.",
        "num_qubits": 5,
        "difficulty": "advanced",
        "tags": ["eigenvalue", "phase-estimation", "primitive"],
        "dependencies": [],
        "license": "MIT",
        "platforms": ["ibm_heron", "quantinuum_h2", "simulator"],
        "benchmarks": {
            "ibm_heron": {"depth": 60, "fidelity": 0.95, "latency_ms": 150, "cost_usd": 0.006},
            "quantinuum_h2": {"depth": 60, "fidelity": 0.99, "latency_ms": 350, "cost_usd": 0.015},
            "simulator": {"depth": 60, "fidelity": 1.0, "latency_ms": 30, "cost_usd": 0.0},
        },
        "downloads": 1567,
        "rating": 4.6,
        "last_updated": "2026-08-01",
        "qasm3_preview": "OPENQASM 3.0;\n// QPE 5-qubit\nqubit[5] q;\nbit[5] c;\n...",
    },
    {
        "id": "bernstein-vazirani",
        "name": "Bernstein-Vazirani Algorithm",
        "version": "1.2.0",
        "author": "Quantive Research",
        "category": "primitives",
        "description": "Finds hidden bitstring in ONE query — demonstrates quantum parallelism clearly.",
        "num_qubits": 4,
        "difficulty": "beginner",
        "tags": ["oracle", "hidden-shift", "educational"],
        "dependencies": [],
        "license": "MIT",
        "platforms": ["ibm_heron", "quantinuum_h2", "ionq_harmony", "simulator"],
        "benchmarks": {
            "ibm_heron": {"depth": 20, "fidelity": 0.98, "latency_ms": 80, "cost_usd": 0.003},
            "simulator": {"depth": 20, "fidelity": 1.0, "latency_ms": 10, "cost_usd": 0.0},
        },
        "downloads": 2891,
        "rating": 4.8,
        "last_updated": "2026-07-20",
        "qasm3_preview": "OPENQASM 3.0;\n// Bernstein-Vazirani\nqubit[4] q;\nbit[4] c;\n...",
    },
    {
        "id": "qnn-classifier",
        "name": "Quantum Neural Network Classifier",
        "version": "1.3.0",
        "author": "Quantive Research",
        "category": "machine-learning",
        "description": "Parameterized quantum circuit for binary classification. Uses data re-uploading strategy.",
        "num_qubits": 4,
        "difficulty": "advanced",
        "tags": ["qml", "classification", "neural-network"],
        "dependencies": ["vqe-molecular"],
        "license": "MIT",
        "platforms": ["ibm_heron", "quantinuum_h2", "simulator"],
        "benchmarks": {
            "ibm_heron": {"depth": 80, "fidelity": 0.88, "latency_ms": 200, "cost_usd": 0.010},
            "quantinuum_h2": {"depth": 80, "fidelity": 0.95, "latency_ms": 500, "cost_usd": 0.025},
            "simulator": {"depth": 80, "fidelity": 1.0, "latency_ms": 80, "cost_usd": 0.0},
        },
        "downloads": 678,
        "rating": 4.3,
        "last_updated": "2026-09-01",
        "qasm3_preview": "OPENQASM 3.0;\n// QNN classifier\nqubit[4] q;\nbit[4] c;\n...",
    },
    {
        "id": "portfolio-qaoa",
        "name": "Portfolio Optimization QAOA",
        "version": "2.0.0",
        "author": "Quantive Research",
        "category": "finance",
        "description": "QAOA tailored for portfolio optimization — minimize risk for target return. Integrates with Quantive debt optimizer.",
        "num_qubits": 6,
        "difficulty": "advanced",
        "tags": ["finance", "portfolio", "risk-return"],
        "dependencies": ["qaoa-maxcut"],
        "license": "MIT",
        "platforms": ["ibm_heron", "quantinuum_h2"],
        "benchmarks": {
            "ibm_heron": {"depth": 96, "fidelity": 0.90, "latency_ms": 220, "cost_usd": 0.011},
            "quantinuum_h2": {"depth": 96, "fidelity": 0.97, "latency_ms": 550, "cost_usd": 0.027},
        },
        "downloads": 456,
        "rating": 4.4,
        "last_updated": "2026-08-20",
        "qasm3_preview": "OPENQASM 3.0;\n// Portfolio QAOA\nqubit[6] q;\nbit[6] c;\n...",
    },
]

# ── API Endpoints ─────────────────────────────────────────────────

@router.get("/algorithms")
async def list_algorithms(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    platform: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "downloads",
    user: User = Depends(get_current_user),
):
    """Browse and filter quantum algorithms."""
    results = ALGORITHMS

    if category:
        results = [a for a in results if a["category"] == category]
    if difficulty:
        results = [a for a in results if a["difficulty"] == difficulty]
    if platform:
        results = [a for a in results if platform in a["platforms"]]
    if search:
        search_lower = search.lower()
        results = [
            a for a in results
            if search_lower in a["name"].lower()
            or search_lower in a["description"].lower()
            or any(search_lower in t for t in a["tags"])
        ]

    if sort_by == "downloads":
        results.sort(key=lambda a: a["downloads"], reverse=True)
    elif sort_by == "rating":
        results.sort(key=lambda a: a["rating"], reverse=True)
    elif sort_by == "name":
        results.sort(key=lambda a: a["name"])

    categories = list(set(a["category"] for a in ALGORITHMS))
    difficulties = list(set(a["difficulty"] for a in ALGORITHMS))

    return {
        "algorithms": results,
        "total": len(results),
        "categories": categories,
        "difficulties": difficulties,
        "sort_by": sort_by,
    }


@router.get("/algorithms/{algorithm_id}")
async def get_algorithm(algorithm_id: str, user: User = Depends(get_current_user)):
    """Get full details of a specific algorithm."""
    algo = next((a for a in ALGORITHMS if a["id"] == algorithm_id), None)
    if not algo:
        available = [a["id"] for a in ALGORITHMS]
        return {"error": f"Algorithm '{algorithm_id}' not found", "available": available}
    return algo


@router.get("/algorithms/{algorithm_id}/benchmarks")
async def get_algorithm_benchmarks(algorithm_id: str, user: User = Depends(get_current_user)):
    """Get benchmark data for an algorithm across all platforms."""
    algo = next((a for a in ALGORITHMS if a["id"] == algorithm_id), None)
    if not algo:
        return {"error": f"Algorithm '{algorithm_id}' not found"}

    return {
        "algorithm": algo["name"],
        "version": algo["version"],
        "benchmarks": algo["benchmarks"],
        "best_platform": min(
            algo["benchmarks"].items(),
            key=lambda x: x[1].get("cost_usd", 999)
        )[0] if algo["benchmarks"] else None,
    }


@router.post("/algorithms/publish")
async def publish_algorithm(req: AlgorithmPublish, user: User = Depends(get_current_user)):
    """Publish a new algorithm to the marketplace."""
    algo_id = hashlib.sha256(f"{req.name}_{user.id}".encode()).hexdigest()[:12]

    return {
        "status": "published",
        "algorithm_id": algo_id,
        "name": req.name,
        "version": "1.0.0",
        "author": user.name if hasattr(user, 'name') else "Anonymous",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "message": f"Algorithm '{req.name}' published successfully. Pending review.",
    }


@router.get("/categories")
async def list_categories(user: User = Depends(get_current_user)):
    """List all algorithm categories with counts."""
    categories = {}
    for a in ALGORITHMS:
        cat = a["category"]
        if cat not in categories:
            categories[cat] = {"count": 0, "algorithms": []}
        categories[cat]["count"] += 1
        categories[cat]["algorithms"].append(a["name"])

    return {"categories": categories, "total_algorithms": len(ALGORITHMS)}


@router.get("/trending")
async def get_trending(user: User = Depends(get_current_user)):
    """Get trending algorithms (by recent downloads and ratings)."""
    trending = sorted(ALGORITHMS, key=lambda a: a["downloads"] * a["rating"], reverse=True)[:5]
    return {
        "trending": [
            {
                "id": a["id"],
                "name": a["name"],
                "category": a["category"],
                "downloads": a["downloads"],
                "rating": a["rating"],
                "difficulty": a["difficulty"],
            }
            for a in trending
        ]
    }
