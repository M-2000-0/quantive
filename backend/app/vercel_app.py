"""Vercel serverless entrypoint — lightweight FastAPI app for serverless.

Strips out: HTML pages, templates, static files, background threads,
heavy startup tasks. Keeps: all API routes, auth, CORS, middleware.
"""
import logging
import os
import sys
from contextlib import asynccontextmanager

# Ensure backend dir is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError as PydanticValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.database import engine

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("quantive.vercel")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Minimal lifespan — DB check + table creation only, no background threads."""
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connectivity verified")
    except Exception as e:
        logger.warning("Database connection failed at startup: %s", e)

    # Create tables that Vercel's cold start may need
    try:
        from app.database import Base
        # Import all models so Base.metadata knows about them
        import app.models  # noqa: F401
        Base.metadata.create_all(engine, checkfirst=True)
        logger.info("All tables created/verified")
    except Exception as e:
        logger.warning("Table creation partial: %s", e)

    yield

    try:
        engine.dispose()
    except Exception:
        pass


app = FastAPI(
    title="Quantive API",
    description="Quantive — Financial Optimization API (Vercel)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.exception_handler(PydanticValidationError)
async def validation_exception_handler(request, exc: PydanticValidationError):
    errors = []
    for error in exc.errors():
        loc = " -> ".join(str(part) for part in error["loc"])
        errors.append({"field": loc, "message": error["msg"]})
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "code": "validation_error", "errors": errors},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "code": "bad_request"},
    )


# ── API Routes Only ──────────────────────────────────────────────────
from app.api import router  # noqa: E402

app.include_router(router)

# Also include gov routes if they exist
try:
    from app.gov.api import router as gov_router
    app.include_router(gov_router)
except ImportError:
    pass

# ── Health Check ─────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return {"status": "healthy", "version": "1.0.0", "database": db_status, "runtime": "vercel"}


# ── CORS ─────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Total-Count", "Retry-After"],
)
