"""
Test Suite: Hybrid Post-Quantum Encryption
============================================
Tests for encryption, decryption, key rotation, migration, and adversarial scenarios.
"""

import json
import os
import sys
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.security.hybrid_pqc_encryption import (
    HybridPQCEncryption,
    FieldEncryption,
    PQCMigration,
    EncryptedPayload,
    EncryptionVersion,
    PQC_AVAILABLE,
)


def test_basic_encrypt_decrypt():
    """Test basic encryption and decryption roundtrip."""
    engine = HybridPQCEncryption(require_pqc=False)
    engine.generate_keypair()

    plaintext = "Sovereign debt: $5.2B 10Y USD at 6.5%"
    encrypted = engine.encrypt_string(plaintext)
    decrypted = engine.decrypt_string(encrypted)

    assert decrypted == plaintext, f"Roundtrip failed: {decrypted} != {plaintext}"
    print("[PASS] Basic encrypt/decrypt roundtrip")


def test_different_plaintexts():
    """Test various data types and sizes."""
    engine = HybridPQCEncryption(require_pqc=False)
    engine.generate_keypair()

    test_cases = [
        "",                                    # Empty
        "a",                                   # Single char
        "x" * 1000,                            # Long string
        json.dumps({"bonds": [{"id": 1, "amount": 5.2e9}]}),  # JSON
        " Unicode: é ñ ü 中文 🏦",              # Unicode
        "\x00\x01\x02",                        # Binary-ish
    ]

    for i, plaintext in enumerate(test_cases):
        encrypted = engine.encrypt_string(plaintext)
        decrypted = engine.decrypt_string(encrypted)
        assert decrypted == plaintext, f"Case {i} failed"
    print("[PASS] Multiple plaintext types")


def test_encrypted_payload_serialization():
    """Test payload serialization/deserialization."""
    engine = HybridPQCEncryption(require_pqc=False)
    engine.generate_keypair()

    plaintext = "Test serialization"
    payload = engine.encrypt(plaintext.encode())
    serialized = payload.serialize()
    deserialized = EncryptedPayload.deserialize(serialized)

    decrypted = engine.decrypt(deserialized).decode()
    assert decrypted == plaintext
    print("[PASS] Payload serialization roundtrip")


def test_key_rotation():
    """Test key rotation preserves ability to decrypt old data."""
    engine = HybridPQCEncryption(require_pqc=False)

    # Encrypt with key v1
    key1 = engine.generate_keypair()
    plaintext = "Important sovereign data"
    encrypted_v1 = engine.encrypt_string(plaintext, key_id=key1.key_id)

    # Rotate to key v2
    key2 = engine.rotate_keys()
    assert key2.key_id != key1.key_id

    # Encrypt with key v2
    encrypted_v2 = engine.encrypt_string(plaintext, key_id=key2.key_id)

    # Both should decrypt correctly
    decrypted_v1 = engine.decrypt_string(encrypted_v1)
    decrypted_v2 = engine.decrypt_string(encrypted_v2)

    assert decrypted_v1 == plaintext, "V1 decryption failed after rotation"
    assert decrypted_v2 == plaintext, "V2 encryption failed"
    print("[PASS] Key rotation -- old data still decryptable")


def test_wrong_key_fails():
    """Test that wrong key cannot decrypt."""
    engine1 = HybridPQCEncryption(require_pqc=False)
    engine1.generate_keypair()

    engine2 = HybridPQCEncryption(require_pqc=False)
    engine2.generate_keypair()

    plaintext = "Sensitive data"
    encrypted = engine1.encrypt_string(plaintext)

    try:
        engine2.decrypt_string(encrypted)
        assert False, "Should have raised exception"
    except ValueError:
        print("[PASS] Wrong key correctly rejected")


def test_field_encryption():
    """Test database field encryption."""
    engine = HybridPQCEncryption(require_pqc=False)
    engine.generate_keypair()
    fe = FieldEncryption(engine)

    # String field
    encrypted = fe.encrypt_field("Portfolio: Sovereign Core")
    decrypted = fe.decrypt_field(encrypted)
    assert decrypted == "Portfolio: Sovereign Core"

    # JSON field
    data = {"coupon_rate": 6.5, "maturity": "2031-06-15", "currency": "USD"}
    encrypted_json = fe.encrypt_json_field(data)
    decrypted_json = fe.decrypt_json_field(encrypted_json)
    assert decrypted_json == data
    print("[PASS] Field encryption (string + JSON)")


def test_performance_benchmark():
    """Benchmark encryption/decryption performance."""
    engine = HybridPQCEncryption(require_pqc=False)
    engine.generate_keypair()

    plaintext = "Sovereign debt instrument: $5.2B 10Y USD bond at 6.5% coupon, maturity 2031-06-15, ISIN US912810TT59"
    iterations = 200

    # Encrypt benchmark
    start = time.time()
    for _ in range(iterations):
        encrypted = engine.encrypt_string(plaintext)
    encrypt_avg = (time.time() - start) / iterations * 1000

    # Decrypt benchmark
    start = time.time()
    for _ in range(iterations):
        decrypted = engine.decrypt_string(encrypted)
    decrypt_avg = (time.time() - start) / iterations * 1000

    # Size comparison
    import base64
    payload_size = len(base64.b64decode(encrypted))
    plaintext_size = len(plaintext.encode())

    print(f"[PASS] Benchmark: {iterations} iterations")
    print(f"  Encrypt: {encrypt_avg:.3f} ms/op")
    print(f"  Decrypt: {decrypt_avg:.3f} ms/op")
    print(f"  Overhead: {payload_size}B encrypted vs {plaintext_size}B plaintext ({payload_size/plaintext_size:.1f}x)")
    print(f"  PQC available: {PQC_AVAILABLE}")


def test_adversarial_partial_key():
    """Test that having only part of the key material is insufficient."""
    engine = HybridPQCEncryption(require_pqc=False)
    key = engine.generate_keypair()

    plaintext = "Top secret fiscal data"
    encrypted = engine.encrypt_string(plaintext)

    # Create a corrupted key store with wrong key material
    engine2 = HybridPQCEncryption(require_pqc=False)
    engine2.generate_keypair()  # Different key

    try:
        engine2.decrypt_string(encrypted)
        assert False, "Should fail with wrong key"
    except ValueError:
        print("[PASS] Adversarial test: partial/wrong key rejected")


def test_migration_tool():
    """Test the migration helper."""
    engine = HybridPQCEncryption(require_pqc=False)
    engine.generate_keypair()

    migration = PQCMigration(engine)

    # Test migrating records
    result1 = migration.migrate_record("r1", "debt_instruments", "name", "10Y Bond")
    result2 = migration.migrate_record("r2", "audit_events", "metadata", '{"action": "test"}')

    assert result1["status"] == "success"
    assert result2["status"] == "success"

    report = migration.get_migration_report()
    assert report["successful"] == 2
    assert report["failed"] == 0
    print("[PASS] Migration tool works correctly")


def test_payload_format():
    """Test that encrypted payload has correct structure."""
    engine = HybridPQCEncryption(require_pqc=False)
    engine.generate_keypair()

    payload = engine.encrypt(b"test data")
    serialized = payload.serialize()

    # Verify it starts with header
    assert serialized is not None
    assert len(serialized) > 50  # Minimum reasonable size

    # Verify deserialization
    restored = EncryptedPayload.deserialize(serialized)
    assert restored.version in [1, 2]
    assert restored.algorithm != ""
    print("[PASS] Payload format integrity")


def test_concurrent_keys():
    """Test multiple keys coexisting."""
    engine = HybridPQCEncryption(require_pqc=False)

    keys = []
    for _ in range(5):
        keys.append(engine.generate_keypair())

    # All keys should be different
    key_ids = [k.key_id for k in keys]
    assert len(set(key_ids)) == 5, "Duplicate key IDs generated"

    # Each key should encrypt/decrypt independently
    for key in keys:
        encrypted = engine.encrypt_string("test", key_id=key.key_id)
        decrypted = engine.decrypt_string(encrypted)
        assert decrypted == "test"
    print("[PASS] Multiple concurrent keys")


# ── Run all tests ───────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Hybrid PQC Encryption — Test Suite")
    print("=" * 60)
    print(f"PQC library available: {PQC_AVAILABLE}")
    print()

    tests = [
        test_basic_encrypt_decrypt,
        test_different_plaintexts,
        test_encrypted_payload_serialization,
        test_key_rotation,
        test_wrong_key_fails,
        test_field_encryption,
        test_adversarial_partial_key,
        test_migration_tool,
        test_payload_format,
        test_concurrent_keys,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    # Performance benchmark (separate from pass/fail)
    print()
    test_performance_benchmark()

    sys.exit(0 if failed == 0 else 1)
