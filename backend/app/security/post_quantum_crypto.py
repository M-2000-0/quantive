"""Post-Quantum Cryptography (PQC) Readiness Module.

Addresses the "harvest-now, decrypt-later" threat where adversaries
capture encrypted sovereign financial data today and decrypt it when
quantum computers become powerful enough to break RSA/ECC.

NIST Standardized Algorithms (FIPS 203/204/206):
- ML-KEM (Kyber): Key encapsulation for secure key exchange
- ML-DSA (Dilithium): Digital signatures for authentication
- SLH-DSA (SPHINCS+): Hash-based signatures (backup)

This module provides:
- Algorithm selection for data classification levels
- Key generation interface
- Migration roadmap from classical to PQC
- Hybrid mode (classical + PQC) for transition period
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import Base


class PQCAlgorithm(str, Enum):
    # NIST FIPS 203
    ML_KEM_512 = "ML-KEM-512"       # 128-bit security
    ML_KEM_768 = "ML-KEM-768"       # 192-bit security
    ML_KEM_1024 = "ML-KEM-1024"     # 256-bit security
    # NIST FIPS 204
    ML_DSA_44 = "ML-DSA-44"         # 128-bit security
    ML_DSA_65 = "ML-DSA-65"         # 192-bit security
    ML_DSA_87 = "ML-DSA-87"         # 256-bit security
    # NIST FIPS 206
    SLH_DSA_128f = "SLH-DSA-128f"  # Hash-based fallback
    # Classical (for comparison)
    RSA_3072 = "RSA-3072"           # Broken by quantum
    ECDSA_P256 = "ECDSA-P256"       # Broken by quantum


class PQCRecord(Base):
    """Tracks PQC migration status for each data store."""
    __tablename__ = "pqc_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    store_name = Column(String(200), nullable=False, unique=True)
    current_algorithm = Column(String(50), nullable=False)
    target_algorithm = Column(String(50), nullable=False)
    hybrid_mode = Column(Boolean, default=True)  # Classical + PQC during transition
    migration_status = Column(String(20), default="pending")  # pending, in_progress, completed
    migrated_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)


class PostQuantumCryptoManager:
    """Manages post-quantum cryptography migration.

    Addresses the critical threat: nation-state adversaries harvesting
    encrypted sovereign debt data today to decrypt when QPU is available.

    Migration Strategy:
    1. Assess: Identify all encrypted data stores
    2. Plan: Select PQC algorithm based on classification level
    3. Hybrid: Run classical + PQC simultaneously during transition
    4. Cutover: Switch to PQC-only after validation
    5. Verify: Confirm all data re-encrypted with PQC
    """

    # Data classification → recommended PQC algorithm
    ALGORITHM_MAP = {
        "public": None,                    # No encryption needed
        "internal": PQCAlgorithm.ML_KEM_512,
        "confidential": PQCAlgorithm.ML_KEM_768,
        "restricted": PQCAlgorithm.ML_KEM_1024,
        "regulated": PQCAlgorithm.ML_KEM_1024,  # Government classified
    }

    # Signature algorithms by security level
    SIGNATURE_MAP = {
        "low": PQCAlgorithm.ML_DSA_44,
        "medium": PQCAlgorithm.ML_DSA_65,
        "high": PQCAlgorithm.ML_DSA_87,
        "backup": PQCAlgorithm.SLH_DSA_128f,
    }

    # Migration timeline (recommended)
    MIGRATION_PHASES = [
        {"phase": 1, "name": "Assessment", "duration_months": 1,
         "action": "Inventory all encrypted data stores and key management systems"},
        {"phase": 2, "name": "Algorithm Selection", "duration_months": 1,
         "action": "Select ML-KEM variant based on data classification"},
        {"phase": 3, "name": "Hybrid Deployment", "duration_months": 6,
         "action": "Run classical + PQC simultaneously, validate correctness"},
        {"phase": 4, "name": "Cutover", "duration_months": 1,
         "action": "Switch to PQC-only, revoke classical keys"},
        {"phase": 5, "name": "Verification", "duration_months": 1,
         "action": "Audit all stores, confirm no classical encryption remains"},
    ]

    def __init__(self, db: Session):
        self.db = db

    def register_store(
        self,
        store_name: str,
        classification: str,
        current_algorithm: str = "RSA-2048",
    ) -> PQCRecord:
        """Register a data store for PQC migration."""
        target = self.ALGORITHM_MAP.get(classification, PQCAlgorithm.ML_KEM_768)
        if not target:
            raise ValueError(f"Classification '{classification}' does not require encryption")

        record = PQCRecord(
            store_name=store_name,
            current_algorithm=current_algorithm,
            target_algorithm=target.value if isinstance(target, PQCAlgorithm) else target,
            hybrid_mode=True,
            migration_status="pending",
        )
        self.db.add(record)
        self.db.commit()
        return record

    def start_hybrid_mode(self, store_name: str) -> PQCRecord:
        """Enable hybrid classical + PQC mode."""
        record = self._get_record(store_name)
        record.hybrid_mode = True
        record.migration_status = "in_progress"
        self.db.commit()
        return record

    def complete_migration(self, store_name: str) -> PQCRecord:
        """Mark migration as complete."""
        record = self._get_record(store_name)
        record.migration_status = "completed"
        record.hybrid_mode = False
        record.migrated_at = datetime.now(timezone.utc)
        self.db.commit()
        return record

    def get_migration_report(self) -> dict:
        """Generate PQC migration status report."""
        records = self.db.query(PQCRecord).all()
        total = len(records)
        completed = sum(1 for r in records if r.migration_status == "completed")
        in_progress = sum(1 for r in records if r.migration_status == "in_progress")
        pending = sum(1 for r in records if r.migration_status == "pending")

        return {
            "total_stores": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "migration_progress": f"{(completed/total*100):.1f}%" if total > 0 else "0%",
            "readiness_score": round(completed / total * 100, 1) if total > 0 else 0,
            "threat": "Harvest-now, decrypt-later attacks by nation-state adversaries",
            "deadline_recommendation": "Complete migration before QPU availability (est. 2030-2035)",
        }

    def _get_record(self, store_name: str) -> PQCRecord:
        record = self.db.query(PQCRecord).filter(
            PQCRecord.store_name == store_name
        ).first()
        if not record:
            raise ValueError(f"Store '{store_name}' not found")
        return record
