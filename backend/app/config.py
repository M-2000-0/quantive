import os
import secrets
import warnings
from functools import lru_cache

from pathlib import Path

from pydantic_settings import BaseSettings
from dotenv import load_dotenv

_BASE_DIR = Path(__file__).resolve().parents[2]  # repo root
_BACKEND_DIR = Path(__file__).resolve().parents[1]  # backend/

# Load .env into os.environ so BOTH consumers see the same values:
# - Settings (pydantic-settings) below, and
# - modules reading os.environ directly at import time (billing, market
#   data providers, notification providers, ...).
# backend/.env (local overrides) loads first; load_dotenv never overwrites
# keys already in os.environ, so it wins over the repo-root .env, and real
# environment variables win over both.
load_dotenv(_BACKEND_DIR / ".env")
load_dotenv(_BASE_DIR / ".env")

# ── Production secret requirements ─────────────────────────────────
DEFAULT_SECRET_KEY = "change-me-to-a-random-secret-key-in-production"
MIN_SECRET_KEY_LENGTH = 32  # NIST SP 800-132 minimum


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./quantive.db"
    PERSONAL_DATABASE_URL: str = "sqlite:///./quantive_personal.db"
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    CORS_ORIGINS: str = "http://localhost:5173"
    RATE_LIMIT_PER_MINUTE: int = 2000
    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_SCENARIO: int = 10000     # Gov-facing cap (was 50000)
    DEFAULT_SCENARIO: int = 1000  # Default for agency use
    OPTIMIZATION_TIMEOUT_SECONDS: int = 120   # Gov SLA
    SOLVER_TIMEOUT_SECONDS: int = 60        # Per-solver timeout
    LOG_LEVEL: str = "INFO"
    ENABLE_PROVENANCE: bool = True      # Track model origins
    ENVIRONMENT: str = "development"    # "production" enforces real SECRET_KEY
    SECURE_COOKIES: bool = False         # set True in production (requires HTTPS)

    # ── Data residency controls ─────────────────────────────────────
    DATA_RESIDENCY_REGION: str = "us-east-1"       # AWS/GCP region
    DATA_RESIDENCY_COUNTRY: str = "US"             # ISO 3166-1 alpha-2
    DATA_RESIDENCY_ENCRYPTION: str = "aes-256-gcm" # Encryption at rest
    DATA_RESIDENCY_KEY_MANAGEMENT: str = "aws-kms"  # aws-kms | azure-keyvault | hsm | local
    DATA_RESIDENCY_AUDIT_LOGGING: bool = True       # Log all data access
    DATA_RESIDENCY_MAX_EXPORT_SIZE_MB: int = 100    # Max export size
    DATA_RESIDENCY_RESTRICT_CROSS_BORDER: bool = True  # Block cross-border transfers

    # ── Approval workflow configuration ──────────────────────────────
    APPROVAL_FOUR_EYES_THRESHOLD: float = 1_000_000    # $1M requires 2 approvers
    APPROVAL_SIX_EYES_THRESHOLD: float = 50_000_000    # $50M requires 3 approvers
    APPROVAL_EIGHT_EYES_THRESHOLD: float = 500_000_000 # $500M requires 4 approvers
    APPROVAL_MAX_AUTO_APPROVE: float = 100_000         # $100K auto-approved
    APPROVAL_TIMEOUT_HOURS: int = 48                    # Escalation after 48h

    # ── SLA configuration ───────────────────────────────────────────
    SLA_UPTIME_TARGET: float = 99.95     # 99.95% uptime target
    SLA_RTO_HOURS: int = 4               # Recovery Time Objective
    SLA_RPO_MINUTES: int = 15            # Recovery Point Objective
    SLA_MAX_LATENCY_MS: int = 500        # P95 latency target
    SLA_MONTHLY_MAINTENANCE_WINDOW: str = "02:00-06:00 UTC Sunday"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    def validate_production_config(self):
        """Validate configuration for production deployments.
        
        Called at startup to prevent insecure deployments.
        """
        errors = []

        # SECRET_KEY validation
        if self.SECRET_KEY == DEFAULT_SECRET_KEY:
            if self.ENVIRONMENT == "production":
                errors.append(
                    "CRITICAL: SECRET_KEY is the default value. "
                    "Set a cryptographically random SECRET_KEY (≥32 bytes) in production. "
                    "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )
            else:
                warnings.warn(
                    "SECRET_KEY is the default value. "
                    "This is INSECURE and must be changed for production.",
                    stacklevel=2,
                )
        elif len(self.SECRET_KEY) < MIN_SECRET_KEY_LENGTH:
            errors.append(
                f"SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} bytes. "
                f"Current length: {len(self.SECRET_KEY)} bytes."
            )

        # Database validation
        if self.ENVIRONMENT == "production" and "sqlite" in self.DATABASE_URL:
            errors.append(
                "CRITICAL: SQLite is not supported in production. "
                "Use PostgreSQL with RLS enabled. "
                "DATABASE_URL must start with postgresql:// or postgres://"
            )

        # CORS validation
        if self.ENVIRONMENT == "production" and "localhost" in self.CORS_ORIGINS:
            errors.append(
                "CRITICAL: CORS_ORIGINS contains localhost in production. "
                "Set to your actual domain(s)."
            )

        if errors:
            raise ValueError(
                "Production configuration validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        return True

    class Config:
        env_file = [
            str(_BACKEND_DIR / ".env"),
            str(_BASE_DIR / ".env"),
        ]
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Validate on first load
    if settings.ENVIRONMENT == "production":
        settings.validate_production_config()
    return settings
