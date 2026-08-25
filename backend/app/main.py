import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.api import router
from app.config import get_settings
from app.database import Base, engine
from app.security.middleware import (
    GlobalExceptionHandler,
    RateLimitMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.security.threats import ThreatDetectionMiddleware
from app.jobs import create_job

settings = get_settings()

if settings.DEBUG and settings.SECRET_KEY == "change-me-to-a-random-secret-key-in-production":
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
            conn.execute("SELECT 1")
        print("✅ Database connectivity verified")
    except Exception as e:
        print(f"⚠️ Database connection failed at startup: {e}")
        raise

    yield

    # Shutdown: cleanup
    print("🛑 Quantive shutting down gracefully...")


app = FastAPI(
    title="Quantive",
    description="Government Financial Optimization Infrastructure",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)


@app.get("/api/health", include_in_schema=False)
async def health_check():
    """Health check endpoint for orchestration and load balancers."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": "connected",
        "synthetic_data": True,
        "env": "production" if not settings.DEBUG else "development",
    }


@app.post("/api/v1/optimize/background")
async def optimize_background(background_tasks: BackgroundTasks) -> dict:
    """Start optimization as a background task.

    Returns a job ID that can be polled with GET /api/v1/jobs/{job_id}
    """
    job = create_job(problem_id="demo-problem", portfolio_id="synthetic-demo")

    # Schedule background optimization task
    background_tasks.add_task(_run_optimization_job, job.id)

    return {"job_id": job.id, "status": job.status, "message": "Optimization started in background"}


def _run_optimization_job(job_id: str):
    """Run the full optimization pipeline in background."""
    try:
        from quantive.data.fixtures import demo_portfolio
        from quantive.orchestration import run_full_job
        from quantive.models.optimization import OptimizationObjective
        from quantive.models.enums import StrategyProfile
        from app.audit.logger import AuditLogger

        p = demo_portfolio()
        prob = type(
            "OptimizationProblem",
            (object,),
            {
                "id": "demo-problem",
                "name": "Demo Problem",
                "portfolio_id": "synthetic-demo",
                "financing_requirement": 120_000.0,
                "objectives": OptimizationObjective(),
                "constraints": [],
                "scenarios": [],
                "solver_config": {},
                "reference_currency": "USD",
                "profile": StrategyProfile.BEST_OVERALL,
            },
        )()

        result = run_full_job(p, prob)

        JOBS[job_id].status = "completed"
        JOBS[job_id].result = {
            "id": result["result"].id,
            "strategies": len(result["strategies"]),
            "feasible": all(s.feasible for s in result["strategies"]),
        }

        # Audit log
        AuditLogger.log_optimization_complete(
            result_id=result["result"].id,
            user="background_job",
            feasible=result["result"].strategy.feasible,
            objective_value=result["result"].strategy.objective_value,
            runtime=result["result"].runtime,
        )

    except Exception as e:
        JOBS[job_id].status = "failed"
        JOBS[job_id].error = str(e)


@app.get("/api/v1/jobs/{job_id}")
def get_job_status(job_id: str) -> dict:
    """Poll for optimization job status and results."""
    job = get_job(job_id)
    if not job:
        return {"error": "Job not found"}, 404

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Total-Count", "Retry-After"],
)