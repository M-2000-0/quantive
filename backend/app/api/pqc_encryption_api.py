"""
Post-Quantum Encryption API
============================
Endpoints for hybrid PQC encryption, key management, and migration.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.security.hybrid_pqc_encryption import (
    HybridPQCEncryption,
    FieldEncryption,
    PQCMigration,
    get_pqc_engine,
    PQC_AVAILABLE,
)

router = APIRouter(prefix="/api/pqc", tags=["pqc-encryption"])


class EncryptRequest(BaseModel):
    plaintext: str
    classification: str = "confidential"


class DecryptRequest(BaseModel):
    encrypted: str


class FieldEncryptRequest(BaseModel):
    value: str
    field_name: str = ""
    classification: str = "confidential"


# ── Encryption Endpoints ────────────────────────────────────────────

@router.post("/encrypt")
def encrypt_data(req: EncryptRequest):
    """Encrypt data using hybrid PQC + AES-256-GCM."""
    engine = get_pqc_engine()
    encrypted = engine.encrypt_string(req.plaintext)
    return {
        "encrypted": encrypted,
        "algorithm": engine.get_security_status()["key_exchange"],
        "key_id": engine._active_key_id,
        "pqc_protected": PQC_AVAILABLE,
    }


@router.post("/decrypt")
def decrypt_data(req: DecryptRequest):
    """Decrypt data encrypted with hybrid PQC."""
    engine = get_pqc_engine()
    try:
        decrypted = engine.decrypt_string(req.encrypted)
        return {"decrypted": decrypted}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Decryption failed: {str(e)}")


@router.post("/encrypt-field")
def encrypt_field(req: FieldEncryptRequest):
    """Encrypt a database field value."""
    engine = get_pqc_engine()
    fe = FieldEncryption(engine)
    encrypted = fe.encrypt_field(req.value, req.classification)
    return {
        "encrypted_hex": encrypted,
        "field_name": req.field_name,
        "classification": req.classification,
    }


@router.post("/decrypt-field")
def decrypt_field(req: DecryptRequest):
    """Decrypt a database field value."""
    engine = get_pqc_engine()
    fe = FieldEncryption(engine)
    try:
        decrypted = fe.decrypt_field(req.encrypted)
        return {"decrypted": decrypted}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Field decryption failed: {str(e)}")


# ── Key Management ──────────────────────────────────────────────────

@router.get("/keys")
def list_keys():
    """List all encryption keys with status."""
    engine = get_pqc_engine()
    return {
        "keys": engine.get_key_inventory(),
        "active_key_id": engine._active_key_id,
    }


@router.post("/keys/rotate")
def rotate_keys():
    """Rotate to a new encryption key pair."""
    engine = get_pqc_engine()
    old_key_id = engine._active_key_id
    new_key = engine.rotate_keys()
    return {
        "rotated": True,
        "old_key_id": old_key_id,
        "new_key_id": new_key.key_id,
        "expires_at": new_key.expires_at,
        "algorithm": new_key.version.name,
    }


@router.post("/keys/generate")
def generate_key():
    """Generate a new key pair (does not activate it)."""
    engine = get_pqc_engine()
    key = engine.generate_keypair()
    return {
        "key_id": key.key_id,
        "version": key.version.name,
        "created_at": key.created_at,
        "expires_at": key.expires_at,
        "has_pqc": bool(key.mlkem_public_key),
    }


# ── Security Status ─────────────────────────────────────────────────

@router.get("/status")
def security_status():
    """Get PQC security status for audit."""
    engine = get_pqc_engine()
    return engine.get_security_status()


# ── Benchmark ───────────────────────────────────────────────────────

@router.get("/benchmark")
def benchmark_encryption():
    """Benchmark encryption/decryption performance."""
    import time as _time
    engine = get_pqc_engine()

    test_data = "Sovereign debt instrument record: $5.2B 10Y USD bond at 6.5% coupon, maturity 2031-06-15"
    iterations = 100

    # Benchmark encrypt
    start = _time.time()
    for _ in range(iterations):
        encrypted = engine.encrypt_string(test_data)
    encrypt_time = (_time.time() - start) / iterations * 1000

    # Benchmark decrypt
    start = _time.time()
    for _ in range(iterations):
        decrypted = engine.decrypt_string(encrypted)
    decrypt_time = (_time.time() - start) / iterations * 1000

    # Verify correctness
    assert decrypted == test_data, "Decryption mismatch!"

    # Measure payload size overhead
    import base64
    payload_size = len(base64.b64decode(encrypted))
    plaintext_size = len(test_data.encode())

    return {
        "iterations": iterations,
        "encrypt_avg_ms": round(encrypt_time, 3),
        "decrypt_avg_ms": round(decrypt_time, 3),
        "plaintext_bytes": plaintext_size,
        "encrypted_bytes": payload_size,
        "overhead_ratio": f"{payload_size / plaintext_size:.1f}x",
        "pqc_available": PQC_AVAILABLE,
        "algorithm": engine.get_security_status()["key_exchange"],
    }


# ── Migration ───────────────────────────────────────────────────────

@router.get("/migration/plan")
def get_migration_plan():
    """Get the PQC migration plan."""
    engine = get_pqc_engine()
    migration = PQCMigration(engine)
    return {"phases": migration.create_migration_plan()}


@router.post("/migration/test")
def test_migration():
    """Test migration with sample data."""
    engine = get_pqc_engine()
    migration = PQCMigration(engine)

    test_records = [
        ("test-001", "debt_instruments", "name", "10Y USD Sovereign 2031"),
        ("test-002", "debt_instruments", "amortization_schedule", '{"payments": [100, 200, 300]}'),
        ("test-003", "audit_events", "metadata_json", '{"action": "create", "user": "admin"}'),
    ]

    results = []
    for record_id, table, field, value in test_records:
        result = migration.migrate_record(record_id, table, field, value)
        results.append(result)

    return {
        "test_results": results,
        "report": migration.get_migration_report(),
    }
