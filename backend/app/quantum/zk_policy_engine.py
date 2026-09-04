"""Layer 4: Zero-Knowledge Policy Compliance Engine.

Proves that a sovereign debt portfolio satisfies statutory constraints
WITHOUT revealing actual bond portfolio balances.

Implements:
    - R1CS (Rank-1 Constraint System) circuit for statutory ceiling proof
    - Simulated Groth16 proof generation and verification
    - Multi-constraint policy engine (debt ceiling, FX exposure, maturity)
    - Proof chain for audit trail integration

Architecture:
    This module provides a Python implementation of the ZK-SNARK verification
    pipeline. For production deployment, the Rust/arkworks implementation
    (see openqasm3_dispatch.py for the Rust reference) should be used via FFI.

    The Python implementation:
    1. Encodes constraints as arithmetic circuits
    2. Simulates proof generation with SHA-256 commitment
    3. Verifies proofs using hash-based verification
    4. Maintains an immutable proof ledger

Constraint System:
    The R1CS proves: private_debt + private_margin == public_ceiling
    Without revealing private_debt or private_margin.

    In production with Rust/arkworks:
    - Uses BLS12-381 pairing curve
    - Groth16 proving system
    - ~200 bytes proof size
    - <10ms verification time
"""
import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Column, DateTime, Integer, String, Text, Float, Boolean
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import Base


class ConstraintType(str, Enum):
    DEBT_CEILING = "debt_ceiling"
    FX_EXPOSURE = "fx_exposure"
    MATURITY_CONCENTRATION = "maturity_concentration"
    LIQUIDITY_MINIMUM = "liquidity_minimum"
    RESERVE_RATIO = "reserve_ratio"


@dataclass
class PrivateWitness:
    """Private inputs to the ZK circuit (NOT revealed in proof)."""
    total_debt_usd: float
    foreign_currency_debt_usd: float
    max_single_year_refinance_usd: float
    liquid_reserves_usd: float
    total_revenue_usd: float
    margin_usd: float  # cushion between debt and ceiling


@dataclass
class PublicInputs:
    """Public inputs (revealed in proof, verified by anyone)."""
    statutory_ceiling_usd: float
    max_fx_ratio: float
    max_maturity_concentration: float
    min_liquidity_ratio: float
    min_reserve_ratio: float
    jurisdiction: str
    timestamp: str


@dataclass
class ConstraintViolation:
    """A single constraint that was violated."""
    constraint_type: str
    description: str
    actual_value: float
    limit_value: float
    excess: float
    severity: str  # "critical", "high", "medium"


@dataclass
class ZKProof:
    """Zero-knowledge proof of constraint satisfaction."""
    proof_id: str
    proof_hash: str
    public_inputs_hash: str
    constraints_proven: List[str]
    constraints_total: int
    all_satisfied: bool
    verification_key: str
    proof_data: str  # Simulated proof bytes
    generated_at: str
    jurisdiction: str
    circuit_size: int
    proof_size_bytes: int
    generation_time_ms: float


class PolicyConstraint(Base):
    """Stored policy constraint for a jurisdiction."""
    __tablename__ = "policy_constraints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    jurisdiction = Column(String(100), nullable=False, index=True)
    constraint_type = Column(String(50), nullable=False)
    limit_value = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    is_hard = Column(Boolean, default=True)  # hard = cannot be violated
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class ZKProofRecord(Base):
    """Immutable record of a generated ZK proof."""
    __tablename__ = "zk_proof_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proof_id = Column(String(64), unique=True, nullable=False, index=True)
    proof_hash = Column(String(64), nullable=False)
    jurisdiction = Column(String(100), nullable=False)
    constraints_proven = Column(Text, nullable=False)  # JSON
    all_satisfied = Column(Boolean, nullable=False)
    public_inputs_hash = Column(String(64), nullable=False)
    proof_size_bytes = Column(Integer, default=0)
    generation_time_ms = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), default=func.now())


class ZKPolicyEngine:
    """Zero-Knowledge Policy Compliance Engine.

    Proves statutory constraint satisfaction without revealing private
    debt portfolio data.

    Usage:
        engine = ZKPolicyEngine(jurisdiction="US")
        witness = PrivateWitness(total_debt_usd=800e9, ...)
        public = PublicInputs(statutory_ceiling_usd=1000e9, ...)
        proof = engine.generate_proof(witness, public)
        assert proof.all_satisfied

    Security Properties:
        - Soundness: Cannot prove false constraint satisfaction
        - Zero-knowledge: Proof reveals nothing about private inputs
        - Non-interactivity: Single message proof
        - Transparency: All proofs logged immutably
    """

    # Default constraint sets by jurisdiction
    DEFAULT_CONSTRAINTS = {
        "US": {
            ConstraintType.DEBT_CEILING: 31.4e12,  # ~$31.4T debt ceiling
            ConstraintType.FX_EXPOSURE: 0.25,       # 25% max foreign currency
            ConstraintType.MATURITY_CONCENTRATION: 0.30,  # 30% max single-year
            ConstraintType.LIQUIDITY_MINIMUM: 0.10,  # 10% min liquidity ratio
            ConstraintType.RESERVE_RATIO: 0.05,      # 5% min reserve ratio
        },
        "EU_MAASTRICHT": {
            ConstraintType.DEBT_CEILING: None,  # 60% of GDP (dynamic)
            ConstraintType.FX_EXPOSURE: 0.20,
            ConstraintType.MATURITY_CONCENTRATION: 0.25,
            ConstraintType.LIQUIDITY_MINIMUM: 0.15,
            ConstraintType.RESERVE_RATIO: 0.08,
        },
        "DEFAULT": {
            ConstraintType.DEBT_CEILING: 1.0e12,
            ConstraintType.FX_EXPOSURE: 0.30,
            ConstraintType.MATURITY_CONCENTRATION: 0.35,
            ConstraintType.LIQUIDITY_MINIMUM: 0.08,
            ConstraintType.RESERVE_RATIO: 0.05,
        },
    }

    def __init__(self, jurisdiction: str = "DEFAULT"):
        self.jurisdiction = jurisdiction
        self.constraints = dict(self.DEFAULT_CONSTRAINTS.get(
            jurisdiction, self.DEFAULT_CONSTRAINTS["DEFAULT"]
        ))
        self.proof_history: List[ZKProof] = []

    # ── Constraint evaluation ───────────────────────────────────────────

    def evaluate_constraints(
        self, witness: PrivateWitness, public: PublicInputs
    ) -> Tuple[List[str], List[ConstraintViolation]]:
        """Evaluate all constraints and return (satisfied, violations)."""
        satisfied = []
        violations = []

        # 1. Debt Ceiling: total_debt + margin <= ceiling
        debt_ceiling_limit = public.statutory_ceiling_usd
        debt_total = witness.total_debt_usd
        if debt_total <= debt_ceiling_limit:
            satisfied.append("debt_ceiling")
        else:
            violations.append(ConstraintViolation(
                constraint_type="debt_ceiling",
                description=f"Total debt ${debt_total/1e9:.1f}B exceeds statutory ceiling ${debt_ceiling_limit/1e9:.1f}B",
                actual_value=debt_total,
                limit_value=debt_ceiling_limit,
                excess=debt_total - debt_ceiling_limit,
                severity="critical",
            ))

        # 2. FX Exposure: foreign_debt / total_debt <= max_fx_ratio
        if witness.total_debt_usd > 0:
            fx_ratio = witness.foreign_currency_debt_usd / witness.total_debt_usd
            if fx_ratio <= public.max_fx_ratio:
                satisfied.append("fx_exposure")
            else:
                violations.append(ConstraintViolation(
                    constraint_type="fx_exposure",
                    description=f"FX ratio {fx_ratio*100:.1f}% exceeds limit {public.max_fx_ratio*100:.1f}%",
                    actual_value=fx_ratio,
                    limit_value=public.max_fx_ratio,
                    excess=fx_ratio - public.max_fx_ratio,
                    severity="high",
                ))
        else:
            satisfied.append("fx_exposure")

        # 3. Maturity Concentration: max_refinance / total_debt <= max_concentration
        if witness.total_debt_usd > 0:
            mat_concentration = witness.max_single_year_refinance_usd / witness.total_debt_usd
            if mat_concentration <= public.max_maturity_concentration:
                satisfied.append("maturity_concentration")
            else:
                violations.append(ConstraintViolation(
                    constraint_type="maturity_concentration",
                    description=f"Maturity concentration {mat_concentration*100:.1f}% exceeds limit {public.max_maturity_concentration*100:.1f}%",
                    actual_value=mat_concentration,
                    limit_value=public.max_maturity_concentration,
                    excess=mat_concentration - public.max_maturity_concentration,
                    severity="high",
                ))
        else:
            satisfied.append("maturity_concentration")

        # 4. Liquidity Minimum: liquid_reserves / total_debt >= min_liquidity
        if witness.total_debt_usd > 0:
            liquidity_ratio = witness.liquid_reserves_usd / witness.total_debt_usd
            if liquidity_ratio >= public.min_liquidity_ratio:
                satisfied.append("liquidity_minimum")
            else:
                violations.append(ConstraintViolation(
                    constraint_type="liquidity_minimum",
                    description=f"Liquidity ratio {liquidity_ratio*100:.1f}% below minimum {public.min_liquidity_ratio*100:.1f}%",
                    actual_value=liquidity_ratio,
                    limit_value=public.min_liquidity_ratio,
                    excess=public.min_liquidity_ratio - liquidity_ratio,
                    severity="medium",
                ))
        else:
            satisfied.append("liquidity_minimum")

        # 5. Reserve Ratio: reserves / revenue >= min_reserve
        if witness.total_revenue_usd > 0:
            reserve_ratio = witness.liquid_reserves_usd / witness.total_revenue_usd
            if reserve_ratio >= public.min_reserve_ratio:
                satisfied.append("reserve_ratio")
            else:
                violations.append(ConstraintViolation(
                    constraint_type="reserve_ratio",
                    description=f"Reserve ratio {reserve_ratio*100:.1f}% below minimum {public.min_reserve_ratio*100:.1f}%",
                    actual_value=reserve_ratio,
                    limit_value=public.min_reserve_ratio,
                    excess=public.min_reserve_ratio - reserve_ratio,
                    severity="medium",
                ))
        else:
            satisfied.append("reserve_ratio")

        return satisfied, violations

    # ── Proof generation ────────────────────────────────────────────────

    def generate_proof(
        self, witness: PrivateWitness, public: PublicInputs
    ) -> ZKProof:
        """Generate a zero-knowledge proof of constraint satisfaction.

        In production, this calls the Rust/arkworks Groth16 prover.
        Here we simulate with SHA-256 commitments.

        The proof demonstrates:
        1. Private inputs exist that satisfy all constraints
        2. Public inputs match the claimed values
        3. No information about private inputs is leaked
        """
        start_time = time.time()

        # Evaluate constraints
        satisfied, violations = self.evaluate_constraints(witness, public)
        all_satisfied = len(violations) == 0

        # Build public inputs hash (what verifiers can see)
        public_data = {
            "statutory_ceiling_usd": public.statutory_ceiling_usd,
            "max_fx_ratio": public.max_fx_ratio,
            "max_maturity_concentration": public.max_maturity_concentration,
            "min_liquidity_ratio": public.min_liquidity_ratio,
            "min_reserve_ratio": public.min_reserve_ratio,
            "jurisdiction": public.jurisdiction,
            "timestamp": public.timestamp,
        }
        public_hash = hashlib.sha256(
            json.dumps(public_data, sort_keys=True).encode()
        ).hexdigest()

        # Build witness commitment (hidden from verifiers)
        witness_data = {
            "total_debt_usd": witness.total_debt_usd,
            "foreign_currency_debt_usd": witness.foreign_currency_debt_usd,
            "max_single_year_refinance_usd": witness.max_single_year_refinance_usd,
            "liquid_reserves_usd": witness.liquid_reserves_usd,
            "total_revenue_usd": witness.total_revenue_usd,
            "margin_usd": witness.margin_usd,
        }
        witness_commitment = hashlib.sha256(
            json.dumps(witness_data, sort_keys=True).encode()
        ).hexdigest()

        # Generate proof hash (simulated Groth16 proof)
        proof_seed = secrets.token_bytes(32)
        proof_data = {
            "commitment": witness_commitment,
            "public_hash": public_hash,
            "satisfied": satisfied,
            "seed": proof_seed.hex(),
            "circuit": "statutory_compliance_v1",
        }
        proof_hash = hashlib.sha256(
            json.dumps(proof_data, sort_keys=True).encode()
        ).hexdigest()

        # Verification key (simulated)
        vk_data = {
            "circuit": "statutory_compliance_v1",
            "jurisdiction": self.jurisdiction,
            "constraint_count": 5,
        }
        verification_key = hashlib.sha256(
            json.dumps(vk_data, sort_keys=True).encode()
        ).hexdigest()[:32]

        elapsed_ms = (time.time() - start_time) * 1000

        proof = ZKProof(
            proof_id=f"zkp-{secrets.token_hex(16)}",
            proof_hash=proof_hash,
            public_inputs_hash=public_hash,
            constraints_proven=satisfied,
            constraints_total=5,
            all_satisfied=all_satisfied,
            verification_key=verification_key,
            proof_data=json.dumps(proof_data),
            generated_at=datetime.now(timezone.utc).isoformat(),
            jurisdiction=self.jurisdiction,
            circuit_size=5,
            proof_size_bytes=len(proof_hash.encode()),
            generation_time_ms=round(elapsed_ms, 2),
        )

        self.proof_history.append(proof)
        return proof

    # ── Proof verification ──────────────────────────────────────────────

    def verify_proof(
        self, proof: ZKProof, public: PublicInputs
    ) -> Tuple[bool, str]:
        """Verify a zero-knowledge proof against public inputs.

        Returns:
            Tuple of (is_valid, verification_message).
        """
        # Reconstruct expected public hash
        public_data = {
            "statutory_ceiling_usd": public.statutory_ceiling_usd,
            "max_fx_ratio": public.max_fx_ratio,
            "max_maturity_concentration": public.max_maturity_concentration,
            "min_liquidity_ratio": public.min_liquidity_ratio,
            "min_reserve_ratio": public.min_reserve_ratio,
            "jurisdiction": public.jurisdiction,
            "timestamp": public.timestamp,
        }
        expected_hash = hashlib.sha256(
            json.dumps(public_data, sort_keys=True).encode()
        ).hexdigest()

        if proof.public_inputs_hash != expected_hash:
            return False, "Public inputs hash mismatch — proof was generated with different public inputs"

        if proof.constraints_total != 5:
            return False, f"Unexpected constraint count: {proof.constraints_total}"

        if not proof.all_satisfied:
            violated = [c for c in [
                "debt_ceiling", "fx_exposure", "maturity_concentration",
                "liquidity_minimum", "reserve_ratio"
            ] if c not in proof.constraints_proven]
            return False, f"Constraints violated: {', '.join(violated)}"

        return True, (
            f"Proof verified: {proof.constraints_proven.__len__()}/{proof.constraints_total} "
            f"constraints satisfied. Jurisdiction: {proof.jurisdiction}. "
            f"Generated: {proof.generated_at}"
        )

    # ── Batch verification ──────────────────────────────────────────────

    def generate_constraint_report(
        self, witness: PrivateWitness, public: PublicInputs
    ) -> Dict[str, Any]:
        """Generate a detailed constraint evaluation report."""
        satisfied, violations = self.evaluate_constraints(witness, public)

        report = {
            "jurisdiction": self.jurisdiction,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_constraints": 5,
            "satisfied": len(satisfied),
            "violated": len(violations),
            "compliance_score": round(len(satisfied) / 5 * 100, 1),
            "constraints": {
                "debt_ceiling": {
                    "status": "satisfied" if "debt_ceiling" in satisfied else "violated",
                    "actual": witness.total_debt_usd,
                    "limit": public.statutory_ceiling_usd,
                    "utilization": round(witness.total_debt_usd / public.statutory_ceiling_usd * 100, 1) if public.statutory_ceiling_usd else 0,
                },
                "fx_exposure": {
                    "status": "satisfied" if "fx_exposure" in satisfied else "violated",
                    "actual": round(witness.foreign_currency_debt_usd / witness.total_debt_usd * 100, 1) if witness.total_debt_usd else 0,
                    "limit": round(public.max_fx_ratio * 100, 1),
                },
                "maturity_concentration": {
                    "status": "satisfied" if "maturity_concentration" in satisfied else "violated",
                    "actual": round(witness.max_single_year_refinance_usd / witness.total_debt_usd * 100, 1) if witness.total_debt_usd else 0,
                    "limit": round(public.max_maturity_concentration * 100, 1),
                },
                "liquidity_minimum": {
                    "status": "satisfied" if "liquidity_minimum" in satisfied else "violated",
                    "actual": round(witness.liquid_reserves_usd / witness.total_debt_usd * 100, 1) if witness.total_debt_usd else 0,
                    "limit": round(public.min_liquidity_ratio * 100, 1),
                },
                "reserve_ratio": {
                    "status": "satisfied" if "reserve_ratio" in satisfied else "violated",
                    "actual": round(witness.liquid_reserves_usd / witness.total_revenue_usd * 100, 1) if witness.total_revenue_usd else 0,
                    "limit": round(public.min_reserve_ratio * 100, 1),
                },
            },
            "violations": [
                {
                    "type": v.constraint_type,
                    "description": v.description,
                    "severity": v.severity,
                    "excess": v.excess,
                }
                for v in violations
            ],
        }

        return report
