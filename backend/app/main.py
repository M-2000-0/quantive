import logging
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import text

from app.api import router
from app.config import get_settings
from app.database import engine
from app.jobs import JOBS, create_job, get_job
from app.security.middleware import (
    BearerPromotionMiddleware,
    BodySizeLimitMiddleware,
    GlobalExceptionHandler,
    RateLimitMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.security.rbac_middleware import RBACMiddleware
from app.security.compression import CompressionMiddleware
from app.security.threats import ThreatDetectionMiddleware
from app.security.csrf import CSRFMiddleware
from app.security.idempotency import IdempotencyMiddleware

# ── Page Route Auth Middleware ───────────────────────────────────────
from starlette.middleware.base import BaseHTTPMiddleware

PUBLIC_PATHS = {
    "/", "/login", "/register", "/forgot-password", "/reset-password",
    "/landing", "/pricing", "/demo", "/logout",
    "/qubo", "/terms", "/government", "/business",
}
PUBLIC_PREFIXES = ("/static", "/api/", "/docs", "/redoc")


class PageAuthMiddleware(BaseHTTPMiddleware):
    """Require valid session cookie for all page routes except public ones."""

    async def dispatch(self, request, call_next):
        path = request.url.path
        # Skip auth for API routes, static files, and public pages
        if any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)
        if path in PUBLIC_PATHS:
            return await call_next(request)
        # Check for access_token cookie
        token = request.cookies.get("access_token", "")
        if not token:
            return RedirectResponse("/login", status_code=303)
        # Validate the token
        try:
            from app.security import decode_token
            payload = decode_token(token)
            if not payload or payload.get("type") != "access":
                return RedirectResponse("/login", status_code=303)
        except Exception:
            return RedirectResponse("/login", status_code=303)
        return await call_next(request)


settings = get_settings()

if settings.ENVIRONMENT == "production" and settings.SECRET_KEY == "change-me-to-a-random-secret-key-in-production":
    raise RuntimeError("SECRET_KEY must be set in production. Refusing to start with default value.")

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# Structured JSON logging for production
if settings.ENVIRONMENT == "production":
    try:
        import structlog
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    except ImportError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        print("[OK] Database connectivity verified")
    except Exception as e:
        logging.getLogger("uvicorn.error").exception("Database connection failed at startup: %s", e)
        raise

    # Ensure signal-outcome tracking table exists (additive, non-destructive)
    try:
        from app.models.signal_outcome import SignalOutcome
        SignalOutcome.__table__.create(engine, checkfirst=True)
        print("[OK] Signal outcome table ready")
    except Exception as e:
        logging.getLogger("uvicorn.error").warning("Could not create signal_outcomes table: %s", e)

    # Ensure market-monitor tables exist (alerts, history, assets, signals)
    try:
        from app.database import Base
        from app.models import market_monitor as _mm
        for _t in (_mm.MarketAsset, _mm.PriceHistory, _mm.MarketSignal,
                   _mm.InsightRecord, _mm.UserAlert, _mm.AlertHistory):
            _t.__table__.create(engine, checkfirst=True)
        print("[OK] Market monitor tables ready")
    except Exception as e:
        logging.getLogger("uvicorn.error").warning("Could not create market monitor tables: %s", e)

    # Ensure user_profiles has the columns added by later model revisions
    # (checkfirst only creates missing tables, not missing columns).
    try:
        with engine.connect() as conn:
            # Reflect current columns on user_profiles
            cols = {r[1] for r in conn.execute(
                text("PRAGMA table_info(user_profiles)"
            )).fetchall()}
            if "exclusions" not in cols:
                conn.execute(text(
                    "ALTER TABLE user_profiles ADD COLUMN exclusions JSON NULL"
                ))
                conn.commit()
                print("[OK] user_profiles.exclusions column added")
            else:
                print("[OK] user_profiles.exclusions column present")
    except Exception as e:
        logging.getLogger("uvicorn.error").warning(
            "Could not ensure user_profiles columns: %s", e
        )

    # Start background alert checker
    try:
        from app.api.price_alerts import start_alert_checker
        start_alert_checker()
        print("[OK] Background alert checker started")
    except Exception as e:
        logging.getLogger("uvicorn.error").warning("Could not start alert checker: %s", e)

    # Start market-monitor alert checker (email/SMS dispatch)
    try:
        from app.api.market_monitor_api import start_mm_alert_checker
        start_mm_alert_checker()
        print("[OK] Market-monitor alert checker started")
    except Exception as e:
        logging.getLogger("uvicorn.error").warning("Could not start MM alert checker: %s", e)

    # Start live market price WebSocket stream
    try:
        from app.services.market_price_stream import start_market_stream
        await start_market_stream()
        print("[OK] Market price WebSocket stream started")
    except Exception as e:
        logging.getLogger("uvicorn.error").warning("Could not start market stream: %s", e)

    # Start weekly digest email scheduler (Mondays 08:00 UTC)
    try:
        from app.services.weekly_digest_scheduler import start_weekly_digest_scheduler
        await start_weekly_digest_scheduler()
        print("[OK] Weekly digest scheduler started")
    except Exception as e:
        logging.getLogger("uvicorn.error").warning("Could not start weekly digest scheduler: %s", e)

    # Start hourly news ingestion scheduler (keeps sentiment fresh)
    try:
        from app.services.news_scheduler import start_news_ingestion_scheduler
        await start_news_ingestion_scheduler()
        print("[OK] Hourly news ingestion scheduler started")
    except Exception as e:
        logging.getLogger("uvicorn.error").warning("Could not start news scheduler: %s", e)

    # Ensure billing tables exist (subscriptions + usage metering — persisted
    # so plans and daily quotas survive restarts)
    try:
        from app.models.billing import SubscriptionRow, UsageRow
        SubscriptionRow.__table__.create(engine, checkfirst=True)
        UsageRow.__table__.create(engine, checkfirst=True)
        print("[OK] Billing tables ready")
    except Exception as e:
        logging.getLogger("uvicorn.error").warning("Could not create billing tables: %s", e)

    # Ensure discovery tables exist (personalized opportunity engine) and
    # seed the reference universe so cold-start returns useful suggestions.
    try:
        from app.models.discovery import DiscoveryAsset, DiscoveryFeedback, DiscoveryPreference
        for _t in (DiscoveryAsset, DiscoveryPreference, DiscoveryFeedback):
            _t.__table__.create(engine, checkfirst=True)
        from app.database import SessionLocal as _SeedSession
        _seed = _SeedSession()
        try:
            from app.services.discovery_engine import DiscoveryEngine
            DiscoveryEngine(_seed).seed_universe()
        finally:
            _seed.close()
        print("[OK] Discovery tables ready + universe seeded")
    except Exception as e:
        logging.getLogger("uvicorn.error").warning("Could not create discovery tables: %s", e)

    # Ensure automation tables exist + start automation scheduler (native workflow engine)
    try:
        from app.database import Base
        from app.models.automation import (
            Automation, AutomationRun, DunningCase, Lead, MrrEvent, OnboardingSequence,
        )
        for _t in (Automation, AutomationRun, Lead, OnboardingSequence, DunningCase, MrrEvent):
            _t.__table__.create(engine, checkfirst=True)
        from app.services.automation_scheduler import start_automation_scheduler
        await start_automation_scheduler()
        print("[OK] Automation engine started (6 native workflow automations)")
    except Exception as e:
        logging.getLogger("uvicorn.error").warning("Could not start automation engine: %s", e)

    # Ensure Quantive Personal tables exist in SEPARATE database (never in sovereign DB)
    try:
        from app.personal.database import PersonalBase, personal_engine
        from app.personal import models as _pm  # noqa: F401
        PersonalBase.metadata.create_all(bind=personal_engine, checkfirst=True)
        print("[OK] Quantive Personal tables ready (separate DB)")
    except Exception as e:
        logging.getLogger("uvicorn.error").warning("Could not create Personal tables: %s", e)

    yield

    # ── Graceful Shutdown ──────────────────────────────────────────────
    logger = logging.getLogger("quantive.shutdown")
    logger.info("Starting graceful shutdown — cancelling background tasks...")

    # Cancel any running background threads
    shutdown_event = threading.Event()
    shutdown_event.set()

    # Dispose database engine to release connections
    try:
        engine.dispose()
        logger.info("Database connections released")
    except Exception as e:
        logger.warning("Error disposing database engine: %s", e)

    logger.info("Quantive shut down gracefully")


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


# ── API Routes ───────────────────────────────────────────────────────

@app.post("/api/v1/optimize/background")
async def optimize_background(background_tasks: BackgroundTasks) -> dict:
    job = create_job(problem_id="demo-problem", portfolio_id="synthetic-demo")
    background_tasks.add_task(_run_optimization_job, job.id)
    return {"job_id": job.id, "status": job.status, "message": "Optimization started in background"}


_jobs_lock = threading.Lock()

def _run_optimization_job(job_id: str):
    try:
        import sys
        from pathlib import Path

        repo_root = str(Path(__file__).resolve().parents[2])
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)

        from quantive.data.fixtures import demo_portfolio, build_default_problem
        from quantive.orchestration import run_full_job

        p = demo_portfolio()
        prob = build_default_problem()
        prob.id = f"job-problem-{job_id}"

        result = run_full_job(p, prob)

        with _jobs_lock:
            JOBS[job_id].status = "completed"
            JOBS[job_id].result = {
                "id": result["result"].id,
                "strategies": len(result["strategies"]),
                "feasible": all(s.feasible for s in result["strategies"]),
            }

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
        with _jobs_lock:
            JOBS[job_id].status = "failed"
            JOBS[job_id].error = str(e)


@app.get("/api/v1/jobs/{job_id}")
def get_job_status(job_id: str) -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


api_v1_prefix = "/api/v1"
app.include_router(router, prefix=api_v1_prefix)
app.include_router(router)

app.add_middleware(GlobalExceptionHandler)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=settings.RATE_LIMIT_PER_MINUTE)
app.add_middleware(ThreatDetectionMiddleware)
app.add_middleware(RBACMiddleware)
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(CompressionMiddleware)
app.add_middleware(PageAuthMiddleware)
# Cookie→Bearer promotion for same-origin API calls (see class docstring).
# Added LAST so it runs FIRST in the chain, before CSRF/rate-limit see headers.
app.add_middleware(BearerPromotionMiddleware)

# ── Static Files (cached) ───────────────────────────────────
import os as _os
_STATIC_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "static")
if _os.path.isdir(_STATIC_DIR):
    from fastapi.staticfiles import StaticFiles as _StaticFiles
    app.mount("/static", _StaticFiles(directory=_STATIC_DIR), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Total-Count", "Retry-After"],
)


# ── Jinja2 Templates ─────────────────────────────────────────────────

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

TODAY = datetime.now().strftime("%B %d, %Y")

# Default context for all page routes
def page_ctx(**kwargs):
    return {"today": TODAY, **kwargs}


# ── Auth Pages ───────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse("/dashboard", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("pages/login.html", {"request": request, **page_ctx()})


@app.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, response: Response, email: str = Form(...), password: str = Form(...)):
    from app.security import verify_password, create_access_token, create_refresh_token, log_audit_event
    from app.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower().strip()).first()
        if not user or not verify_password(password, user.password_hash):
            log_audit_event(db, None, "user.login_failed", "user",
                            metadata={"email": email.lower().strip()},
                            ip_address=request.client.host if request.client else None)
            return templates.TemplateResponse("pages/login.html", {
                "request": request, "error": "Invalid email or password", **page_ctx()
            })
        if not user.is_active:
            return templates.TemplateResponse("pages/login.html", {
                "request": request, "error": "Account is deactivated", **page_ctx()
            })
        # Check if MFA is enabled for this user
        try:
            from app.models.mfa_config import MFAConfig
            mfa_config = db.query(MFAConfig).filter(
                MFAConfig.user_id == user.id,
                MFAConfig.enabled == True
            ).first()
            if mfa_config:
                # Store user ID in session for MFA verification
                resp = RedirectResponse("/mfa/verify", status_code=303)
                import hmac as _hmac, hashlib as _hashlib, time as _time
                _mfa_sig = _hmac.new(settings.SECRET_KEY.encode(), f"{user.id}:{int(_time.time())}".encode(), _hashlib.sha256).hexdigest()[:16]
                resp.set_cookie("mfa_pending_user", f"{user.id}:{int(_time.time())}:{_mfa_sig}", httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax", max_age=300)
                return resp
        except Exception:
            pass  # MFA table may not exist yet
        access = create_access_token({"sub": user.id, "org_id": user.org_id, "role": user.role})
        refresh = create_refresh_token({"sub": user.id})
        log_audit_event(db, user, "user.login", "user", user.id,
                        ip_address=request.client.host if request.client else None)
        resp = RedirectResponse("/dashboard", status_code=303)
        resp.set_cookie("access_token", access, httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax", max_age=1800)
        resp.set_cookie("refresh_token", refresh, httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax", max_age=604800)
        resp.set_cookie("user_name", user.name, httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax", max_age=604800)
        resp.set_cookie("user_role", str(user.role.value if hasattr(user.role, 'value') else user.role), httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax", max_age=604800)
        return resp
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("pages/register.html", {"request": request, **page_ctx()})


@app.post("/register", response_class=HTMLResponse)
async def register_post(request: Request, first_name: str = Form(""), last_name: str = Form(""), email: str = Form(...), password: str = Form(...), organization: str = Form("")):
    name = f"{first_name.strip()} {last_name.strip()}".strip()
    org_name = organization.strip()
    if not name:
        return templates.TemplateResponse("pages/register.html", {
            "request": request, "error": "Please enter your name.", **page_ctx()
        })
    from app.security import hash_password, create_access_token, create_refresh_token, log_audit_event
    from app.database import SessionLocal
    from app.models import User, Organization

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email.lower().strip()).first()
        if existing:
            return templates.TemplateResponse("pages/register.html", {
                "request": request, "error": "Email already registered", **page_ctx()
            })
        org = Organization(name=org_name or f"{name.strip()}'s Organization")
        db.add(org)
        db.flush()
        user = User(
            email=email.lower().strip(),
            password_hash=hash_password(password),
            name=name.strip(),
            role="admin",
            org_id=org.id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        log_audit_event(db, user, "user.registered", "user", user.id,
                        ip_address=request.client.host if request.client else None)
        access = create_access_token({"sub": user.id, "org_id": user.org_id, "role": user.role})
        refresh = create_refresh_token({"sub": user.id})
        resp = RedirectResponse("/dashboard", status_code=303)
        resp.set_cookie("access_token", access, httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax", max_age=1800)
        resp.set_cookie("refresh_token", refresh, httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax", max_age=604800)
        resp.set_cookie("user_name", user.name, httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax", max_age=604800)
        resp.set_cookie("user_role", "admin", httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax", max_age=604800)
        return resp
    finally:
        db.close()


@app.get("/mfa/verify", response_class=HTMLResponse)
async def mfa_verify_page(request: Request):
    mfa_cookie = request.cookies.get("mfa_pending_user")
    if not mfa_cookie:
        return RedirectResponse("/login", status_code=303)
    parts = mfa_cookie.split(":")
    if len(parts) != 3:
        return RedirectResponse("/login", status_code=303)
    mfa_user_id, ts_str, sig = parts
    import hmac as _hmac, hashlib as _hashlib
    expected_sig = _hmac.new(settings.SECRET_KEY.encode(), f"{mfa_user_id}:{ts_str}".encode(), _hashlib.sha256).hexdigest()[:16]
    if not _hmac.compare_digest(sig, expected_sig):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("pages/mfa-verify.html", {
        "request": request, "user_id": mfa_user_id, **page_ctx()
    })


@app.post("/mfa/verify", response_class=HTMLResponse)
async def mfa_verify_post(request: Request, response: Response, user_id: str = Form(...), code: str = Form(...)):
    from app.database import SessionLocal
    from app.models import User
    from app.security.mfa import verify_totp
    from app.security import create_access_token, create_refresh_token, log_audit_event

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return RedirectResponse("/login", status_code=303)

        from app.models.mfa_config import MFAConfig
        mfa_config = db.query(MFAConfig).filter(
            MFAConfig.user_id == user.id,
            MFAConfig.enabled == True
        ).first()

        if not mfa_config:
            # MFA not enabled, skip verification
            pass
        elif not verify_totp(mfa_config.totp_secret, code):
            return templates.TemplateResponse("pages/mfa-verify.html", {
                "request": request, "user_id": user_id,
                "error": "Invalid verification code", **page_ctx()
            })

        # MFA passed, issue tokens
        access = create_access_token({"sub": user.id, "org_id": user.org_id, "role": user.role})
        refresh = create_refresh_token({"sub": user.id})
        log_audit_event(db, user, "user.login_mfa", "user", user.id,
                        ip_address=request.client.host if request.client else None)
        resp = RedirectResponse("/dashboard", status_code=303)
        resp.set_cookie("access_token", access, httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax", max_age=1800)
        resp.set_cookie("refresh_token", refresh, httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax", max_age=604800)
        resp.set_cookie("user_name", user.name, httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax", max_age=604800)
        resp.set_cookie("user_role", str(user.role.value if hasattr(user.role, 'value') else user.role), httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax", max_age=604800)
        resp.delete_cookie("mfa_pending_user")
        return resp
    finally:
        db.close()


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("pages/forgot-password.html", {"request": request, **page_ctx()})


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    return templates.TemplateResponse("pages/reset-password.html", {"request": request, **page_ctx()})


@app.get("/demo", response_class=HTMLResponse)
async def demo_mode(request: Request):
    return RedirectResponse("/dashboard", status_code=303)


@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("access_token")
    resp.delete_cookie("refresh_token")
    resp.delete_cookie("user_name")
    resp.delete_cookie("user_role")
    return resp


# ── Dashboard ────────────────────────────────────────────────────────

@app.get("/simulation", response_class=HTMLResponse)
async def simulation_page(request: Request):
    return templates.TemplateResponse("pages/simulation.html", {
        "request": request,
        "active_page": "simulation",
        **page_ctx(),
    })


@app.get("/advanced-debt", response_class=HTMLResponse)
async def advanced_debt_page(request: Request):
    return templates.TemplateResponse("pages/advanced-debt.html", {
        "request": request,
        "active_page": "advanced-debt",
        **page_ctx(),
    })


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("pages/dashboard.html", {
        "request": request,
        "active_page": "dashboard",
        **page_ctx(
            total_debt="",
            instrument_count=0,
            currency_count=0,
            avg_maturity="",
            refinancing_risk=0,
            currency_risk=0,
            rate_risk=0,
            portfolios=[],
            optimizations=[],
        ),
    })


# ── Portfolio Pages ──────────────────────────────────────────────────

@app.get("/portfolios", response_class=HTMLResponse)
async def portfolios_page(request: Request):
    return templates.TemplateResponse("pages/portfolios.html", {"request": request, "active_page": "portfolios", **page_ctx()})


@app.get("/portfolios/new", response_class=HTMLResponse)
async def portfolio_new_page(request: Request):
    return templates.TemplateResponse("pages/portfolio-new.html", {"request": request, "active_page": "portfolios", **page_ctx()})


@app.get("/portfolios/{portfolio_id}", response_class=HTMLResponse)
async def portfolio_detail_page(request: Request, portfolio_id: str):
    return templates.TemplateResponse("pages/portfolio-detail.html", {"request": request, "active_page": "portfolios", "portfolio_id": portfolio_id, **page_ctx()})


# ── Optimization Pages ───────────────────────────────────────────────

@app.get("/optimizations/new", response_class=HTMLResponse)
async def optimization_new_page(request: Request):
    return templates.TemplateResponse("pages/optimizations-new.html", {"request": request, "active_page": "optimize", **page_ctx()})


@app.get("/optimizations", response_class=HTMLResponse)
async def optimizations_page(request: Request):
    return templates.TemplateResponse("pages/optimizations.html", {"request": request, "active_page": "optimize", **page_ctx()})


@app.get("/optimizations/{optimization_id}", response_class=HTMLResponse)
async def optimization_detail_page(request: Request, optimization_id: str):
    return templates.TemplateResponse("pages/optimization-detail.html", {"request": request, "active_page": "optimize", "optimization_id": optimization_id, **page_ctx()})


@app.get("/recommendations", response_class=HTMLResponse)
async def recommendations_page(request: Request):
    return templates.TemplateResponse("pages/recommendations.html", {
        "request": request,
        "active_page": "recommendations",
        **page_ctx(),
    })


# ── Market Pages ─────────────────────────────────────────────────────

@app.get("/market", response_class=HTMLResponse)
async def market_page(request: Request):
    return templates.TemplateResponse("pages/market.html", {"request": request, "active_page": "market", **page_ctx()})




# ── Risk Pages ───────────────────────────────────────────────────────

@app.get("/risk", response_class=HTMLResponse)
async def risk_page(request: Request):
    return templates.TemplateResponse("pages/risk.html", {"request": request, "active_page": "risk", **page_ctx()})


@app.get("/risk-dashboard", response_class=HTMLResponse)
async def risk_dashboard_page(request: Request):
    return templates.TemplateResponse("pages/risk-dashboard.html", {"request": request, "active_page": "risk", **page_ctx()})


@app.get("/early-warning", response_class=HTMLResponse)
async def early_warning_page(request: Request):
    return templates.TemplateResponse("pages/early-warning.html", {"request": request, "active_page": "risk", **page_ctx()})


@app.get("/risk-radar", response_class=HTMLResponse)
async def risk_radar_page(request: Request):
    return templates.TemplateResponse("pages/risk-radar.html", {"request": request, "active_page": "risk", **page_ctx()})


@app.get("/risk-intel", response_class=HTMLResponse)
async def risk_intel_page(request: Request):
    return templates.TemplateResponse("pages/risk-intel.html", {"request": request, "active_page": "risk", **page_ctx()})


@app.get("/sovereign-health", response_class=HTMLResponse)
async def sovereign_health_page(request: Request):
    return templates.TemplateResponse("pages/sovereign-health.html", {"request": request, "active_page": "risk", **page_ctx()})


@app.get("/consolidated", response_class=HTMLResponse)
async def consolidated_debt_page(request: Request):
    return templates.TemplateResponse("pages/consolidated-debt.html", {"request": request, "active_page": "risk", **page_ctx()})


@app.get("/vendor-risk", response_class=HTMLResponse)
async def vendor_risk_page(request: Request):
    return templates.TemplateResponse("pages/vendor-risk.html", {"request": request, "active_page": "risk", **page_ctx()})


# ── Simulation Pages ─────────────────────────────────────────────────

@app.get("/whatif", response_class=HTMLResponse)
async def whatif_page(request: Request):
    return templates.TemplateResponse("pages/whatif.html", {"request": request, "active_page": "whatif", **page_ctx()})


@app.get("/black-swan", response_class=HTMLResponse)
async def black_swan_page(request: Request):
    return templates.TemplateResponse("pages/black-swan.html", {"request": request, "active_page": "whatif", **page_ctx()})


@app.get("/digital-twin", response_class=HTMLResponse)
async def digital_twin_page(request: Request):
    return templates.TemplateResponse("pages/digital-twin.html", {"request": request, "active_page": "whatif", **page_ctx()})


@app.get("/pareto", response_class=HTMLResponse)
async def pareto_page(request: Request):
    return templates.TemplateResponse("pages/pareto.html", {"request": request, "active_page": "whatif", **page_ctx()})


@app.get("/scenario-compare", response_class=HTMLResponse)
async def scenario_compare_page(request: Request):
    return templates.TemplateResponse("pages/scenario-compare.html", {"request": request, "active_page": "whatif", **page_ctx()})


@app.get("/crisis", response_class=HTMLResponse)
async def crisis_page(request: Request):
    return templates.TemplateResponse("pages/crisis.html", {"request": request, "active_page": "whatif", **page_ctx()})


@app.get("/policy-impact", response_class=HTMLResponse)
async def policy_impact_page(request: Request):
    return templates.TemplateResponse("pages/policy-impact.html", {"request": request, "active_page": "whatif", **page_ctx()})


@app.get("/stock-monitor", response_class=HTMLResponse)
async def stock_monitor_page(request: Request):
    return templates.TemplateResponse("pages/stock-monitor.html", {"request": request, "active_page": "whatif", **page_ctx()})


# ── Decision Pages ───────────────────────────────────────────────────

@app.get("/copilot", response_class=HTMLResponse)
async def copilot_page(request: Request):
    return templates.TemplateResponse("pages/copilot.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/explain-engine", response_class=HTMLResponse)
async def explain_engine_page(request: Request):
    return templates.TemplateResponse("pages/explain-engine.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/roi-engine", response_class=HTMLResponse)
async def roi_engine_page(request: Request):
    return templates.TemplateResponse("pages/roi-engine.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/rating-agency", response_class=HTMLResponse)
async def rating_agency_page(request: Request):
    return templates.TemplateResponse("pages/rating-agency.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/issuance-planner", response_class=HTMLResponse)
async def issuance_planner_page(request: Request):
    return templates.TemplateResponse("pages/issuance-planner.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/constraint-builder", response_class=HTMLResponse)
async def constraint_builder_page(request: Request):
    return templates.TemplateResponse("pages/constraint-builder.html", {"request": request, "active_page": "copilot", **page_ctx()})


# ── Approve Pages ────────────────────────────────────────────────────

@app.get("/approvals", response_class=HTMLResponse)
async def approvals_page(request: Request):
    return templates.TemplateResponse("pages/approvals.html", {"request": request, "active_page": "approvals", **page_ctx()})


@app.get("/case-studies", response_class=HTMLResponse)
async def case_studies_page(request: Request):
    return templates.TemplateResponse("pages/case-studies.html", {"request": request, "active_page": "case-studies", **page_ctx()})


@app.get("/soc2-readiness", response_class=HTMLResponse)
async def soc2_readiness_page(request: Request):
    return templates.TemplateResponse("pages/soc2-readiness.html", {"request": request, "active_page": "compliance", **page_ctx()})


@app.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request):
    return templates.TemplateResponse("pages/notifications.html", {"request": request, "active_page": "notifications", **page_ctx()})


@app.get("/data-import", response_class=HTMLResponse)
async def data_import_page(request: Request):
    return templates.TemplateResponse("pages/data-import.html", {"request": request, "active_page": "data-import", **page_ctx()})


@app.get("/decision-vault", response_class=HTMLResponse)
async def decision_vault_page(request: Request):
    return templates.TemplateResponse("pages/decision-vault.html", {"request": request, "active_page": "approvals", **page_ctx()})


@app.get("/minister", response_class=HTMLResponse)
async def minister_page(request: Request):
    return templates.TemplateResponse("pages/minister.html", {"request": request, "active_page": "approvals", **page_ctx()})


@app.get("/compliance", response_class=HTMLResponse)
async def compliance_page(request: Request):
    return templates.TemplateResponse("pages/compliance.html", {"request": request, "active_page": "compliance", **page_ctx()})


@app.get("/fiscal-rules", response_class=HTMLResponse)
async def fiscal_rules_page(request: Request):
    return templates.TemplateResponse("pages/fiscal-rules.html", {"request": request, "active_page": "compliance", **page_ctx()})


@app.get("/immutable-audit", response_class=HTMLResponse)
async def immutable_audit_page(request: Request):
    return templates.TemplateResponse("pages/immutable-audit.html", {"request": request, "active_page": "audit", **page_ctx()})


@app.get("/audit", response_class=HTMLResponse)
async def audit_page(request: Request):
    return templates.TemplateResponse("pages/immutable-audit.html", {"request": request, "active_page": "audit", **page_ctx()})


@app.get("/audit-trail", response_class=HTMLResponse)
async def audit_trail_page(request: Request):
    return templates.TemplateResponse("pages/audit-trail.html", {"request": request, "active_page": "audit", **page_ctx()})


@app.get("/circuit-designer", response_class=HTMLResponse)
async def circuit_designer_page(request: Request):
    return templates.TemplateResponse("pages/circuit-designer.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/error-correction", response_class=HTMLResponse)
async def error_correction_page(request: Request):
    return templates.TemplateResponse("pages/error-correction.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/quantum-simulator", response_class=HTMLResponse)
async def quantum_simulator_page(request: Request):
    return templates.TemplateResponse("pages/quantum-simulator.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/decision-history", response_class=HTMLResponse)
async def decision_history_page(request: Request):
    return templates.TemplateResponse("pages/decision-history.html", {"request": request, "active_page": "approvals", **page_ctx()})


@app.get("/decision-archive", response_class=HTMLResponse)
async def decision_archive_page(request: Request):
    return templates.TemplateResponse("pages/decision-archive.html", {"request": request, "active_page": "approvals", **page_ctx()})


# ── Monitor Pages ────────────────────────────────────────────────────

@app.get("/executions", response_class=HTMLResponse)
async def executions_page(request: Request):
    return templates.TemplateResponse("pages/executions.html", {"request": request, "active_page": "executions", **page_ctx()})


@app.get("/fraud-detection", response_class=HTMLResponse)
async def fraud_detection_page(request: Request):
    return templates.TemplateResponse("pages/fraud-detection.html", {"request": request, "active_page": "fraud", **page_ctx()})


@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    return templates.TemplateResponse("pages/reports.html", {"request": request, "active_page": "reports", **page_ctx()})


@app.get("/security", response_class=HTMLResponse)
async def security_page(request: Request):
    return templates.TemplateResponse("pages/security.html", {"request": request, "active_page": "security", **page_ctx()})



@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("pages/settings.html", {"request": request, "active_page": "settings", **page_ctx()})


@app.get("/automation", response_class=HTMLResponse)
async def automation_page(request: Request):
    return templates.TemplateResponse("pages/automation.html", {"request": request, "active_page": "automation", **page_ctx()})


@app.get("/user-settings", response_class=HTMLResponse)
async def user_settings_page(request: Request):
    return templates.TemplateResponse("pages/user-settings.html", {"request": request, "active_page": "settings", **page_ctx()})


@app.get("/system-status", response_class=HTMLResponse)
async def system_status_page(request: Request):
    return templates.TemplateResponse("pages/system-status.html", {"request": request, "active_page": "settings", **page_ctx()})


# ── Special Pages ────────────────────────────────────────────────────

@app.get("/landing", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse("pages/landing.html", {"request": request, **page_ctx()})


@app.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request):
    return templates.TemplateResponse("pages/pricing.html", {"request": request, **page_ctx()})


@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(request: Request):
    return templates.TemplateResponse("pages/onboarding.html", {"request": request, **page_ctx()})


@app.get("/onboarding-wizard", response_class=HTMLResponse)
async def onboarding_wizard_page(request: Request):
    return templates.TemplateResponse("pages/onboarding-wizard.html", {"request": request, **page_ctx()})


@app.get("/changelog", response_class=HTMLResponse)
async def changelog_page(request: Request):
    return templates.TemplateResponse("pages/changelog.html", {"request": request, "active_page": "changelog", **page_ctx()})


@app.get("/savings", response_class=HTMLResponse)
async def savings_page(request: Request):
    return templates.TemplateResponse("pages/dashboard.html", {
        "request": request,
        "active_page": "savings",
        **page_ctx(),
    })


@app.get("/market-pulse", response_class=HTMLResponse)
async def market_pulse_page(request: Request):
    return templates.TemplateResponse("pages/market.html", {
        "request": request,
        "active_page": "market",
        **page_ctx(),
    })


@app.get("/briefing", response_class=HTMLResponse)
async def briefing_page(request: Request):
    return templates.TemplateResponse("pages/dashboard.html", {
        "request": request,
        "active_page": "briefing",
        **page_ctx(),
    })


@app.get("/assets", response_class=HTMLResponse)
async def assets_page(request: Request):
    return templates.TemplateResponse("pages/dashboard.html", {
        "request": request,
        "active_page": "assets",
        **page_ctx(),
    })


@app.get("/commodities", response_class=HTMLResponse)
async def commodities_page(request: Request):
    return templates.TemplateResponse("pages/dashboard.html", {
        "request": request,
        "active_page": "assets",
        **page_ctx(),
    })


@app.get("/legal/{page_name}", response_class=HTMLResponse)
async def legal_page(request: Request, page_name: str):
    return templates.TemplateResponse("pages/legal.html", {"request": request, "page_name": page_name, **page_ctx()})


@app.get("/billing", response_class=HTMLResponse)
async def billing_page(request: Request):
    return templates.TemplateResponse("pages/billing.html", {"request": request, "active_page": "billing", **page_ctx()})


# ── Advanced Pages ───────────────────────────────────────────────────

@app.get("/peer-comparison", response_class=HTMLResponse)
async def peer_comparison_page(request: Request):
    return templates.TemplateResponse("pages/peer-comparison.html", {"request": request, "active_page": "risk", **page_ctx()})


@app.get("/benchmark", response_class=HTMLResponse)
async def benchmark_page(request: Request):
    return templates.TemplateResponse("pages/benchmark.html", {"request": request, "active_page": "risk", **page_ctx()})


@app.get("/maturity-assessment", response_class=HTMLResponse)
async def maturity_assessment_page(request: Request):
    return templates.TemplateResponse("pages/maturity-assessment.html", {"request": request, "active_page": "risk", **page_ctx()})


@app.get("/maturity-ladder", response_class=HTMLResponse)
async def maturity_ladder_page(request: Request):
    return templates.TemplateResponse("pages/maturity-ladder.html", {"request": request, "active_page": "risk", **page_ctx()})


@app.get("/savings-trace", response_class=HTMLResponse)
async def savings_trace_page(request: Request):
    return templates.TemplateResponse("pages/savings-trace.html", {"request": request, "active_page": "risk", **page_ctx()})


@app.get("/knowledge-graph", response_class=HTMLResponse)
async def knowledge_graph_page(request: Request):
    return templates.TemplateResponse("pages/knowledge-graph.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/knowledge-network", response_class=HTMLResponse)
async def knowledge_network_page(request: Request):
    return templates.TemplateResponse("pages/knowledge-network.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/institutional-iq", response_class=HTMLResponse)
async def institutional_iq_page(request: Request):
    return templates.TemplateResponse("pages/institutional-iq.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/institutional-memory", response_class=HTMLResponse)
async def institutional_memory_page(request: Request):
    return templates.TemplateResponse("pages/institutional-memory.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/solver-tournament", response_class=HTMLResponse)
async def solver_tournament_page(request: Request):
    return templates.TemplateResponse("pages/solver-tournament.html", {"request": request, "active_page": "optimize", **page_ctx()})


@app.get("/sovereign-advisor", response_class=HTMLResponse)
async def sovereign_advisor_page(request: Request):
    return templates.TemplateResponse("pages/sovereign-advisor.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/sovereign-dsa", response_class=HTMLResponse)
async def sovereign_dsa_page(request: Request):
    return templates.TemplateResponse("pages/sovereign-dsa.html", {"request": request, "active_page": "risk", **page_ctx()})


@app.get("/explainability", response_class=HTMLResponse)
async def explainability_page(request: Request):
    return templates.TemplateResponse("pages/explainability-page.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/zkp-policy", response_class=HTMLResponse)
async def zkp_policy_page(request: Request):
    return templates.TemplateResponse("pages/zkp-policy.html", {"request": request, "active_page": "security", **page_ctx()})


@app.get("/quantum-readiness", response_class=HTMLResponse)
async def quantum_readiness_page(request: Request):
    return templates.TemplateResponse("pages/quantum-readiness.html", {"request": request, "active_page": "security", **page_ctx()})


@app.get("/air-gapped", response_class=HTMLResponse)
async def air_gapped_page(request: Request):
    return templates.TemplateResponse("pages/air-gapped.html", {"request": request, "active_page": "security", **page_ctx()})


@app.get("/red-team", response_class=HTMLResponse)
async def red_team_page(request: Request):
    return templates.TemplateResponse("pages/red-team.html", {"request": request, "active_page": "security", **page_ctx()})


@app.get("/multi-eyes", response_class=HTMLResponse)
async def multi_eyes_page(request: Request):
    return templates.TemplateResponse("pages/multi-eyes.html", {"request": request, "active_page": "security", **page_ctx()})


@app.get("/insider-risk", response_class=HTMLResponse)
async def insider_risk_page(request: Request):
    return templates.TemplateResponse("pages/insider-risk.html", {"request": request, "active_page": "security", **page_ctx()})


@app.get("/dlp", response_class=HTMLResponse)
async def dlp_page(request: Request):
    return templates.TemplateResponse("pages/dlp.html", {"request": request, "active_page": "security", **page_ctx()})


@app.get("/data-residency", response_class=HTMLResponse)
async def data_residency_page(request: Request):
    return templates.TemplateResponse("pages/data-residency.html", {"request": request, "active_page": "security", **page_ctx()})


@app.get("/source-inspection", response_class=HTMLResponse)
async def source_inspection_page(request: Request):
    return templates.TemplateResponse("pages/source-inspection.html", {"request": request, "active_page": "security", **page_ctx()})


@app.get("/training-academy", response_class=HTMLResponse)
async def training_academy_page(request: Request):
    return templates.TemplateResponse("pages/training-academy.html", {"request": request, "active_page": "settings", **page_ctx()})


@app.get("/national-resilience", response_class=HTMLResponse)
async def national_resilience_page(request: Request):
    return templates.TemplateResponse("pages/national-resilience.html", {"request": request, "active_page": "risk", **page_ctx()})




@app.get("/disaster-recovery", response_class=HTMLResponse)
async def disaster_recovery_page(request: Request):
    return templates.TemplateResponse("pages/disaster-recovery.html", {"request": request, "active_page": "security", **page_ctx()})


@app.get("/geopolitical", response_class=HTMLResponse)
async def geopolitical_page(request: Request):
    return templates.TemplateResponse("pages/geopolitical.html", {"request": request, "active_page": "risk", **page_ctx()})


@app.get("/anti-corruption", response_class=HTMLResponse)
async def anti_corruption_page(request: Request):
    return templates.TemplateResponse("pages/anti-corruption.html", {"request": request, "active_page": "compliance", **page_ctx()})


@app.get("/corruption-opportunity", response_class=HTMLResponse)
async def corruption_opportunity_page(request: Request):
    return templates.TemplateResponse("pages/corruption-opportunity.html", {"request": request, "active_page": "compliance", **page_ctx()})


@app.get("/political-feasibility", response_class=HTMLResponse)
async def political_feasibility_page(request: Request):
    return templates.TemplateResponse("pages/political-feasibility.html", {"request": request, "active_page": "risk", **page_ctx()})




@app.get("/fiscal-impact", response_class=HTMLResponse)
async def fiscal_impact_page(request: Request):
    return templates.TemplateResponse("pages/fiscal-impact.html", {"request": request, "active_page": "risk", **page_ctx()})


@app.get("/excel-import", response_class=HTMLResponse)
async def excel_import_page(request: Request):
    return templates.TemplateResponse("pages/excel-import.html", {"request": request, "active_page": "portfolios", **page_ctx()})


@app.get("/purchase-tracker", response_class=HTMLResponse)
async def purchase_tracker_page(request: Request):
    return templates.TemplateResponse("pages/purchase-tracker.html", {"request": request, "active_page": "executions", **page_ctx()})


@app.get("/workflow", response_class=HTMLResponse)
async def workflow_page(request: Request):
    return templates.TemplateResponse("pages/workflow.html", {"request": request, "active_page": "approvals", **page_ctx()})


@app.get("/qae", response_class=HTMLResponse)
async def qae_page(request: Request):
    return templates.TemplateResponse("pages/qae.html", {"request": request, "active_page": "copilot", **page_ctx()})






@app.get("/ai-challenger", response_class=HTMLResponse)
async def ai_challenger_page(request: Request):
    return templates.TemplateResponse("pages/ai-challenger.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/ai-governance", response_class=HTMLResponse)
async def ai_governance_page(request: Request):
    return templates.TemplateResponse("pages/ai-governance.html", {"request": request, "active_page": "compliance", **page_ctx()})


@app.get("/openqasm3", response_class=HTMLResponse)
async def openqasm3_page(request: Request):
    return templates.TemplateResponse("pages/openqasm3.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/event-impact", response_class=HTMLResponse)
async def event_impact_page(request: Request):
    return templates.TemplateResponse("pages/event-impact.html", {"request": request, "active_page": "risk", **page_ctx()})









@app.get("/assumption-tracker", response_class=HTMLResponse)
async def assumption_tracker_page(request: Request):
    return templates.TemplateResponse("pages/assumption-tracker.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/model-validation", response_class=HTMLResponse)
async def model_validation_page(request: Request):
    return templates.TemplateResponse("pages/model-validation.html", {"request": request, "active_page": "copilot", **page_ctx()})


@app.get("/offline-mode", response_class=HTMLResponse)
async def offline_mode_page(request: Request):
    return templates.TemplateResponse("pages/offline-mode.html", {"request": request, "active_page": "settings", **page_ctx()})


@app.get("/data-source-trust", response_class=HTMLResponse)
async def data_source_trust_page(request: Request):
    return templates.TemplateResponse("pages/data-source-trust.html", {"request": request, "active_page": "market", **page_ctx()})


@app.get("/war-room", response_class=HTMLResponse)
async def war_room_page(request: Request):
    return templates.TemplateResponse("pages/war-room.html", {"request": request, "active_page": "risk", **page_ctx()})



@app.get("/crypto", response_class=HTMLResponse)
async def crypto_page(request: Request):
    return templates.TemplateResponse("pages/crypto.html", {
        "request": request,
        "active_page": "crypto",
        **page_ctx(),
    })


@app.get("/fintech-tracker", response_class=HTMLResponse)
async def fintech_tracker_page(request: Request):
    return templates.TemplateResponse("pages/fintech-tracker.html", {
        "request": request,
        "active_page": "fintech-tracker",
        **page_ctx(),
    })


@app.get("/market-intelligence", response_class=HTMLResponse)
async def market_intelligence_page(request: Request):
    return templates.TemplateResponse("pages/market-intelligence.html", {
        "request": request,
        "active_page": "market-intelligence",
        **page_ctx(),
    })


@app.get("/external-factors", response_class=HTMLResponse)
async def external_factors_page(request: Request):
    return templates.TemplateResponse("pages/external-factors.html", {
        "request": request,
        "active_page": "risk",
        **page_ctx(),
    })


@app.get("/trading-tools", response_class=HTMLResponse)
async def trading_tools_page(request: Request):
    return templates.TemplateResponse("pages/alerts-backtest.html", {
        "request": request,
        "active_page": "market",
        **page_ctx(),
    })


@app.get("/backtesting", response_class=HTMLResponse)
async def backtesting_page(request: Request):
    return templates.TemplateResponse("pages/backtesting.html", {
        "request": request,
        "active_page": "backtesting",
        **page_ctx(),
    })


@app.get("/compliance-check", response_class=HTMLResponse)
async def compliance_check_page(request: Request):
    return templates.TemplateResponse("pages/compliance-check.html", {
        "request": request,
        "active_page": "compliance",
        **page_ctx(),
    })


@app.get("/fx-hedging", response_class=HTMLResponse)
async def fx_hedging_page(request: Request):
    return templates.TemplateResponse("pages/fx-hedging.html", {
        "request": request,
        "active_page": "fx-hedging",
        **page_ctx(),
    })


@app.get("/trading-hub", response_class=HTMLResponse)
async def trading_hub_page(request: Request):
    return templates.TemplateResponse("pages/trading-hub.html", {
        "request": request,
        "active_page": "market",
        **page_ctx(),
    })



@app.get("/advanced-analytics", response_class=HTMLResponse)
async def advanced_analytics_page(request: Request):
    return templates.TemplateResponse("pages/advanced-analytics.html", {
        "request": request,
        "active_page": "advanced-analytics",
        **page_ctx(),
    })
@app.get("/rebalancing", response_class=HTMLResponse)
async def rebalancing_page(request: Request):
    return templates.TemplateResponse("pages/rebalancing.html", {
        "request": request,
        "active_page": "rebalancing",
        **page_ctx(),
    })

@app.get("/debt-optimizer", response_class=HTMLResponse)
async def debt_optimizer_page(request: Request):
    return templates.TemplateResponse("pages/debt-optimizer.html", {
        "request": request,
        "active_page": "debt-optimizer",
        **page_ctx(),
    })


@app.get("/market-monitor", response_class=HTMLResponse)
async def market_monitor_page(request: Request):
    return templates.TemplateResponse("pages/market-monitor.html", {
        "request": request,
        "active_page": "market-monitor",
        **page_ctx(),
    })


@app.get("/bubble-detector", response_class=HTMLResponse)
async def bubble_detector_page(request: Request):
    return templates.TemplateResponse("pages/bubble-detector.html", {
        "request": request,
        "active_page": "bubble-detector",
        **page_ctx(),
    })


@app.get("/portfolio-optimizer", response_class=HTMLResponse)
async def portfolio_optimizer_page(request: Request):
    return templates.TemplateResponse("pages/portfolio-optimizer.html", {
        "request": request,
        "active_page": "portfolio-optimizer",
        **page_ctx(),
    })


@app.get("/trading", response_class=HTMLResponse)
async def trading_redirect(request: Request):
    return RedirectResponse("/trading-hub", status_code=303)


@app.get("/stocks", response_class=HTMLResponse)
async def stocks_redirect(request: Request):
    return RedirectResponse("/trading-hub", status_code=303)


@app.get("/options", response_class=HTMLResponse)
async def options_redirect(request: Request):
    return RedirectResponse("/trading-hub", status_code=303)


@app.get("/sectors", response_class=HTMLResponse)
async def sectors_redirect(request: Request):
    return RedirectResponse("/trading-hub", status_code=303)


# ── Fallback ─────────────────────────────────────────────────────────

@app.get("/{path:path}", response_class=HTMLResponse)
async def fallback(request: Request, path: str):
    if path.startswith("api/") or path.startswith("docs") or path.startswith("redoc"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    return RedirectResponse("/login", status_code=303)


print("[OK] Python frontend loaded — Jinja2 templates active")

# Keep a reference to the unwrapped FastAPI instance so tests can register
# dependency_overrides and inspect the middleware stack even though the
# served `app` below is wrapped by the CSRF ASGI middleware.
fastapi_app = app

# Wrap the fully-built FastAPI app with the CSRF ASGI middleware as the
# outermost non-CORS layer. add_middleware does not reliably invoke this
# Starlette version's raw-ASGI middlewares, so we compose the app directly.
# This must happen AFTER all @app.get/@app.post decorators and route mounts.
app = CSRFMiddleware(app)
print("[OK] CSRF ASGI middleware wrapped around app")
