import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import text

from app.api import router
from app.config import get_settings
from app.database import engine
from app.jobs import JOBS, create_job, get_job
from app.security.middleware import (
    GlobalExceptionHandler,
    RateLimitMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.security.threats import ThreatDetectionMiddleware

settings = get_settings()

if settings.ENVIRONMENT == "production" and settings.SECRET_KEY == "change-me-to-a-random-secret-key-in-production":
    raise RuntimeError("SECRET_KEY must be set in production. Refusing to start with default value.")

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify DB connectivity (engine is synchronous)
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        print("[OK] Database connectivity verified")
    except Exception as e:
        logging.getLogger("uvicorn.error").exception("Database connection failed at startup: %s", e)
        raise

    yield

    # Shutdown: cleanup
    print("[OK] Quantive shutting down gracefully")


app = FastAPI(
    title="Quantive",
    description="Government Financial Optimization Infrastructure",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
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


@app.post("/api/v1/optimize/background")
async def optimize_background(background_tasks: BackgroundTasks) -> dict:
    """Start optimization as a background task.

    Returns a job ID that can be polled with GET /api/v1/jobs/{job_id}
    """
    job = create_job(problem_id="demo-problem", portfolio_id="synthetic-demo")

    # Schedule background optimization task with job reference
    background_tasks.add_task(_run_optimization_job, job.id)

    return {"job_id": job.id, "status": job.status, "message": "Optimization started in background"}


def _run_optimization_job(job_id: str):
    """Run the full optimization pipeline in background."""
    try:
        # The engine lives outside backend/; make it importable at runtime.
        import sys
        from pathlib import Path

        repo_root = str(Path(__file__).resolve().parents[2])
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)

        from quantive.data.fixtures import demo_portfolio, build_default_problem
        from quantive.orchestration import run_full_job

        p = demo_portfolio()
        prob = build_default_problem()
        # Override problem ID so it's unique per job
        prob.id = f"job-problem-{job_id}"

        result = run_full_job(p, prob)

        JOBS[job_id].status = "completed"
        JOBS[job_id].result = {
            "id": result["result"].id,
            "strategies": len(result["strategies"]),
            "feasible": all(s.feasible for s in result["strategies"]),
        }

        # Audit log
        try:
            from app.audit.logger import AuditLogger

            AuditLogger.log_optimization_complete(
                result_id=result["result"].id,
                user="background_job",
                feasible=result["result"].strategy.feasible,
                objective_value=result["result"].strategy.objective_value,
                runtime=result["result"].runtime,
            )
        except ImportError:
            pass

    except Exception as e:
        JOBS[job_id].status = "failed"
        JOBS[job_id].error = str(e)


@app.get("/api/v1/jobs/{job_id}")
def get_job_status(job_id: str) -> dict:
    """Poll for optimization job status and results."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job.to_dict()


# Keep backward compatibility: register router at root AND under /api/v1
api_v1_prefix = "/api/v1"
app.include_router(router, prefix=api_v1_prefix)
app.include_router(router)  # Root-level routes also work

app.add_middleware(GlobalExceptionHandler)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=settings.RATE_LIMIT_PER_MINUTE)
app.add_middleware(ThreatDetectionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Total-Count", "Retry-After"],
)
