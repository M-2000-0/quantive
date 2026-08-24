from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./quantive.db"
    SECRET_KEY: str = "change-me-to-a-random-secret-key-in-production"
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

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
