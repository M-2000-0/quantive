"""Multi-Factor Authentication (MFA) module.

Provides TOTP (Time-based One-Time Password) MFA with:
- Secret generation
- QR code generation (base64 PNG)
- Code verification with time-window tolerance
- Backup codes (one-time use recovery)
"""
import hashlib
import hmac
import secrets
import struct
import time
from base64 import b32decode, b32encode, b64encode
from datetime import datetime, timezone
from typing import Optional

# ── TOTP Implementation ─────────────────────────────────────────────────────

# Base32 alphabet for secret encoding
B32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def generate_secret(length: int = 20) -> str:
    """Generate a random TOTP secret (Base32 encoded)."""
    secret_bytes = secrets.token_bytes(length)
    return b32encode(secret_bytes).decode("utf-8").rstrip("=")


def _int_to_bytes(n: int) -> bytes:
    """Convert integer to big-endian bytes."""
    return struct.pack(">Q", n)


def _hmac_sha1(key: bytes, message: bytes) -> bytes:
    """Compute HMAC-SHA1."""
    return hmac.new(key, message, hashlib.sha1).digest()


def _dynamic_truncation(hmac_result: bytes) -> int:
    """Dynamic truncation as per RFC 4226."""
    offset = hmac_result[-1] & 0x0F
    code = struct.unpack(">I", hmac_result[offset:offset + 4])[0]
    code = code & 0x7FFFFFFF
    return code


def generate_totp(
    secret: str,
    time_step: int = 30,
    digits: int = 6,
    timestamp: Optional[float] = None,
) -> str:
    """Generate a TOTP code.

    Args:
        secret: Base32-encoded secret
        time_step: Time step in seconds (default 30)
        digits: Number of digits in the code (default 6)
        timestamp: Unix timestamp (default: now)

    Returns:
        TOTP code as string
    """
    if timestamp is None:
        timestamp = time.time()

    # Decode the secret
    # Add padding if needed
    padding = (8 - len(secret) % 8) % 8
    secret_padded = secret + "=" * padding
    key = b32decode(secret_padded)

    # Calculate time counter
    counter = int(timestamp // time_step)

    # Compute HMAC-SHA1
    hmac_result = _hmac_sha1(key, _int_to_bytes(counter))

    # Dynamic truncation
    code = _dynamic_truncation(hmac_result)

    # Format to N digits with leading zeros
    return str(code % (10 ** digits)).zfill(digits)


def verify_totp(
    secret: str,
    code: str,
    time_step: int = 30,
    digits: int = 6,
    tolerance: int = 1,
    timestamp: Optional[float] = None,
) -> bool:
    """Verify a TOTP code.

    Args:
        secret: Base32-encoded secret
        code: The TOTP code to verify
        time_step: Time step in seconds (default 30)
        digits: Number of digits (default 6)
        tolerance: Number of time steps to check before/after current (default 1)
        timestamp: Unix timestamp for verification (default: now)

    Returns:
        True if the code is valid
    """
    if timestamp is None:
        timestamp = time.time()

    # Check current and adjacent time windows
    for offset in range(-tolerance, tolerance + 1):
        t = timestamp + (offset * time_step)
        expected = generate_totp(secret, time_step, digits, timestamp=t)
        # Constant-time comparison to prevent timing attacks
        if hmac.compare_digest(code, expected):
            return True

    return False


# ── QR Code Generation ─────────────────────────────────────────────────────

def generate_totp_uri(
    secret: str,
    email: str,
    issuer: str = "Quantive",
    digits: int = 6,
    period: int = 30,
) -> str:
    """Generate a TOTP URI for QR code generation.

    Format: otpauth://totp/ISSUER:EMAIL?secret=SECRET&issuer=ISSUER&digits=DIGITS&period=PERIOD
    """
    import urllib.parse
    params = {
        "secret": secret,
        "issuer": issuer,
        "digits": digits,
        "period": period,
    }
    query = urllib.parse.urlencode(params)
    label = f"{urllib.parse.quote(issuer)}:{urllib.parse.quote(email)}"
    return f"otpauth://totp/{label}?{query}"


def generate_qr_code_base64(uri: str, size: int = 200) -> str:
    """Generate a QR code as a base64-encoded PNG image.

    Falls back to a text-based representation if qrcode is not installed.
    """
    try:
        import qrcode
        from io import BytesIO

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")
    except ImportError:
        # Return a placeholder if qrcode is not installed
        return _generate_text_qr(uri)


def _generate_text_qr(uri: str) -> str:
    """Generate a minimal text-based QR code representation (fallback)."""
    import hashlib as hl
    h = hl.md5(uri.encode()).hexdigest()[:16]
    return f"QR_CODE_HASH:{h}"


# ── Backup Codes ────────────────────────────────────────────────────────────

def generate_backup_codes(count: int = 10, length: int = 8) -> list[str]:
    """Generate one-time backup codes for MFA recovery.

    Args:
        count: Number of codes to generate (default 10)
        length: Length of each code (default 8)

    Returns:
        List of backup codes (plaintext, to be shown to user once)
    """
    codes = []
    for _ in range(count):
        code = secrets.token_urlsafe(length)[:length].upper()
        codes.append(code)
    return codes


def hash_backup_code(code: str) -> str:
    """Hash a backup code for storage (SHA-256)."""
    return hashlib.sha256(code.upper().encode()).hexdigest()


def verify_backup_code(code: str, stored_hashes: list[str]) -> Optional[int]:
    """Verify a backup code against stored hashes.

    Args:
        code: The backup code to verify
        stored_hashes: List of hashed backup codes

    Returns:
        Index of the matched hash, or None if no match
    """
    code_hash = hash_backup_code(code)
    for i, stored in enumerate(stored_hashes):
        if hmac.compare_digest(code_hash, stored):
            return i
    return None
