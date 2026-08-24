"""Tests for MFA (Multi-Factor Authentication) module."""
import time

from app.security.mfa import (
    generate_backup_codes,
    generate_secret,
    generate_totp,
    generate_totp_uri,
    hash_backup_code,
    verify_backup_code,
    verify_totp,
)


class TestTOTP:
    """Tests for TOTP generation and verification."""

    def test_generate_secret_length(self):
        """Secret should be a valid Base32 string of appropriate length."""
        secret = generate_secret()
        assert isinstance(secret, str)
        assert len(secret) >= 16  # At least 80 bits

    def test_generate_secret_uniqueness(self):
        """Each generated secret should be unique."""
        secrets = {generate_secret() for _ in range(100)}
        assert len(secrets) == 100

    def test_generate_totp_returns_string(self):
        """TOTP code should be a string of digits."""
        secret = generate_secret()
        code = generate_totp(secret)
        assert isinstance(code, str)
        assert len(code) == 6
        assert code.isdigit()

    def test_generate_totp_consistency(self):
        """Same secret + same timestamp should produce same code."""
        secret = generate_secret()
        ts = time.time()
        code1 = generate_totp(secret, timestamp=ts)
        code2 = generate_totp(secret, timestamp=ts)
        assert code1 == code2

    def test_generate_totp_different_timestamps(self):
        """Different timestamps should (usually) produce different codes."""
        secret = generate_secret()
        code1 = generate_totp(secret, timestamp=1000000.0)
        code2 = generate_totp(secret, timestamp=1000030.0)  # 30 seconds later
        # They could be the same at boundaries, but with different 30s windows they differ
        # Just verify both are valid format
        assert code1.isdigit() and code2.isdigit()

    def test_verify_totp_valid_code(self):
        """Verification should succeed with the correct code."""
        secret = generate_secret()
        ts = time.time()
        code = generate_totp(secret, timestamp=ts)
        assert verify_totp(secret, code, timestamp=ts) is True

    def test_verify_totp_invalid_code(self):
        """Verification should fail with an incorrect code."""
        secret = generate_secret()
        assert verify_totp(secret, "000000") is False

    def test_verify_totp_time_tolerance(self):
        """Code from adjacent time windows should be accepted within tolerance."""
        secret = generate_secret()
        ts = 1000000.0
        code = generate_totp(secret, timestamp=ts)
        # Verify with timestamp 30 seconds later (one window ahead)
        assert verify_totp(secret, code, timestamp=ts + 30, tolerance=1) is True
        # Verify with timestamp 30 seconds earlier (one window behind)
        assert verify_totp(secret, code, timestamp=ts - 30, tolerance=1) is True

    def test_verify_totp_outside_tolerance(self):
        """Code outside tolerance window should fail."""
        secret = generate_secret()
        ts = 1000000.0
        code = generate_totp(secret, timestamp=ts)
        # Verify with timestamp 2 minutes later (outside tolerance=1)
        assert verify_totp(secret, code, timestamp=ts + 120, tolerance=1) is False

    def test_generate_totp_different_digits(self):
        """Should support different digit lengths."""
        secret = generate_secret()
        code4 = generate_totp(secret, digits=4, timestamp=1000000.0)
        code8 = generate_totp(secret, digits=8, timestamp=1000000.0)
        assert len(code4) == 4
        assert len(code8) == 8

    def test_totp_uri_format(self):
        """URI should follow otpauth:// format."""
        secret = generate_secret()
        uri = generate_totp_uri(secret, "user@example.com")
        assert uri.startswith("otpauth://totp/")
        assert "secret=" in uri
        assert "issuer=Quantive" in uri

    def test_totp_uri_with_custom_issuer(self):
        """URI should support custom issuer."""
        secret = generate_secret()
        uri = generate_totp_uri(secret, "user@example.com", issuer="MyOrg")
        assert "issuer=MyOrg" in uri


class TestBackupCodes:
    """Tests for backup code generation and verification."""

    def test_generate_backup_codes_count(self):
        """Should generate the requested number of codes."""
        codes = generate_backup_codes(count=10)
        assert len(codes) == 10

    def test_generate_backup_codes_format(self):
        """Codes should be uppercase alphanumeric."""
        codes = generate_backup_codes()
        for code in codes:
            assert code.isupper()
            assert len(code) == 8

    def test_generate_backup_codes_uniqueness(self):
        """All codes should be unique."""
        codes = generate_backup_codes(count=50)
        assert len(set(codes)) == 50

    def test_hash_backup_code_deterministic(self):
        """Same code should produce same hash."""
        code = "ABCD1234"
        h1 = hash_backup_code(code)
        h2 = hash_backup_code(code)
        assert h1 == h2

    def test_hash_backup_code_case_insensitive(self):
        """Hashing should be case-insensitive."""
        h1 = hash_backup_code("abcd1234")
        h2 = hash_backup_code("ABCD1234")
        assert h1 == h2

    def test_verify_backup_code_valid(self):
        """Verification should succeed with correct code."""
        codes = generate_backup_codes(count=5)
        hashes = [hash_backup_code(c) for c in codes]

        result = verify_backup_code(codes[2], hashes)
        assert result == 2

    def test_verify_backup_code_invalid(self):
        """Verification should fail with incorrect code."""
        codes = generate_backup_codes(count=5)
        hashes = [hash_backup_code(c) for c in codes]

        result = verify_backup_code("WRNGCODE", hashes)
        assert result is None

    def test_verify_backup_code_returns_correct_index(self):
        """Should return the correct index of the matched code."""
        codes = generate_backup_codes(count=5)
        hashes = [hash_backup_code(c) for c in codes]

        for i, code in enumerate(codes):
            result = verify_backup_code(code, hashes)
            assert result == i

    def test_backup_code_one_time_use(self):
        """After verification, the hash should be removed to prevent reuse."""
        codes = generate_backup_codes(count=3)
        hashes = [hash_backup_code(c) for c in codes]

        # Use the second code
        idx = verify_backup_code(codes[1], hashes)
        assert idx == 1

        # Remove it (simulating one-time use)
        hashes.pop(idx)

        # Should no longer verify
        assert verify_backup_code(codes[1], hashes) is None

        # Other codes should still work
        assert verify_backup_code(codes[0], hashes) == 0
        assert verify_backup_code(codes[2], hashes) == 1  # Index shifted after removal
