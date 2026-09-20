"""Vercel serverless entrypoint — lightweight FastAPI app for serverless.

Strips out: HTML pages, templates, static files, background threads,
heavy startup tasks. Keeps: all API routes, auth, CORS, middleware.
"""
import logging
import os
import sys

# Ensure backend dir is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── Defensive config import ──────────────────────────────────────────
try:
    from app.config import get_settings
    settings = get_settings()
except Exception as e:
    # Fallback so the module at least loads
    import warnings
    warnings.warn(f"Config load failed: {e}. Using safe defaults.")
    settings = None

LOG_LEVEL = getattr(logging, getattr(settings, "LOG_LEVEL", "INFO")) if settings else logging.INFO
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("quantive.vercel")

# ── Defensive database import ────────────────────────────────────────
_engine = None
try:
    from app.database import engine
    _engine = engine
except Exception as e:
    logger.warning("Database engine unavailable: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Minimal lifespan — DB check only, no background threads."""
    if _engine is not None:
        try:
            from sqlalchemy import text
            with _engine.begin() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connectivity verified")
        except Exception as e:
            logger.warning("Database connection failed: %s", e)

        try:
            from app.database import Base
            import app.models  # noqa: F401
            Base.metadata.create_all(_engine, checkfirst=True)
            logger.info("Tables created/verified")
        except Exception as e:
            logger.warning("Table creation partial: %s", e)

        # ── Seed patricio owner if missing (for Vercel SQLite ephemeral) ──
        try:
            from app.database import SessionLocal
            from app.models import User, Organization
            from app.models.billing import SubscriptionRow
            from app.security import hash_password
            import secrets
            from datetime import datetime, timezone, timedelta
            db = SessionLocal()
            try:
                pat = db.query(User).filter(User.email == "patricio@quantive.com").first()
                if not pat:
                    logger.info("Seeding patricio@quantive.com for Vercel")
                    org = Organization(name="Patricio's Organization")
                    db.add(org)
                    db.flush()
                    user = User(
                        email="patricio@quantive.com",
                        password_hash=hash_password("QuantumComp"),
                        name="Patricio",
                        role="admin",
                        is_active=True,
                        email_verified=True,
                        org_id=org.id,
                    )
                    db.add(user)
                    db.flush()
                    now = datetime.now(timezone.utc)
                    sub = SubscriptionRow(
                        id=secrets.token_urlsafe(16),
                        org_id=org.id,
                        user_id=user.id,
                        tier="enterprise",
                        billing_cycle="yearly",
                        stripe_customer_id="",
                        stripe_subscription_id="",
                        status="active",
                        current_period_start=now.isoformat(),
                        current_period_end=(now + timedelta(days=365)).isoformat(),
                        created_at=now.isoformat(),
                        updated_at=now.isoformat(),
                    )
                    db.add(sub)
                    db.commit()
                    logger.info("Seeded patricio owner")
                else:
                    logger.info("Patricio already exists, skip seed")
            finally:
                db.close()
        except Exception as e:
            logger.warning("Patricio seed skipped: %s", e)
    else:
        logger.warning("Skipping DB init — engine unavailable")

    yield

    if _engine is not None:
        try:
            _engine.dispose()
        except Exception:
            pass


app = FastAPI(
    title="Quantive API",
    description="Quantive — Financial Optimization API (Vercel)",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "server_error"},
    )


# ── API Routes ───────────────────────────────────────────────────────
try:
    from app.api import router
    app.include_router(router)
except Exception as e:
    logger.error("Failed to load API router: %s", e)

try:
    from app.gov.api import router as gov_router
    app.include_router(gov_router)
except ImportError:
    pass
except Exception as e:
    logger.warning("Gov routes unavailable: %s", e)


# ── Health Check ─────────────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    db_status = "unknown"
    if _engine is not None:
        try:
            from sqlalchemy import text
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception:
            db_status = "disconnected"
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": db_status,
        "runtime": "vercel",
        "routes": len(app.routes),
    }


# ── CORS (only if settings loaded) ──────────────────────────────────
if settings is not None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Total-Count", "Retry-After"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Total-Count", "Retry-After"],
    )
