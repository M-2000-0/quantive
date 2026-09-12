"""Built-in Quantive domain tools (safe defaults).

Tiers:
  read            — viewer+, auto-allowed (research, analyze, summarize)
  write_internal  — analyst+, auto-allowed (drafts, internal records)
  needs_approval  — analyst+, human must approve before execution
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.agent.tools import ToolContext, quantive_tool


@quantive_tool("list_tools", "List available agent tools with risk tiers", risk="read")
def list_tools(ctx: ToolContext) -> dict:
    from app.agent.tools import registry

    return {"ok": True, "tools": registry.describe()}


@quantive_tool("portfolio_summary", "Summarize a portfolio: totals, counts, avg coupon", risk="read")
def portfolio_summary(ctx: ToolContext, portfolio_id: str) -> dict:
    from app.models import DebtInstrument, Portfolio

    p = (
        ctx.db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.org_id == ctx.org_id)
        .first()
    )
    if not p:
        return {"ok": False, "error": "portfolio not found"}
    insts = ctx.db.query(DebtInstrument).filter(DebtInstrument.portfolio_id == p.id).all()
    total = sum(float(i.principal_outstanding) for i in insts)
    avg_coupon = (
        sum(float(i.principal_outstanding) * float(i.coupon_rate) for i in insts) / total
        if total
        else 0.0
    )
    currencies: dict[str, float] = {}
    for i in insts:
        currencies[i.currency] = currencies.get(i.currency, 0.0) + float(i.principal_outstanding)
    return {
        "ok": True,
        "portfolio_id": p.id,
        "name": p.name,
        "instruments": len(insts),
        "total_principal": total,
        "avg_coupon": avg_coupon,
        "currencies": currencies,
    }


@quantive_tool("maturity_ladder", "Bucket principal by maturity year", risk="read")
def maturity_ladder(ctx: ToolContext, portfolio_id: str) -> dict:
    from app.models import DebtInstrument, Portfolio

    p = (
        ctx.db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.org_id == ctx.org_id)
        .first()
    )
    if not p:
        return {"ok": False, "error": "portfolio not found"}
    insts = ctx.db.query(DebtInstrument).filter(DebtInstrument.portfolio_id == p.id).all()
    ladder: dict[str, float] = {}
    for i in insts:
        year = (i.maturity_date or "????-??-??")[:4]
        ladder[year] = ladder.get(year, 0.0) + float(i.principal_outstanding)
    return {"ok": True, "portfolio_id": p.id, "ladder": dict(sorted(ladder.items()))}


@quantive_tool("risk_summary", "Simple refinancing-concentration risk scan", risk="read")
def risk_summary(ctx: ToolContext, portfolio_id: str) -> dict:
    ladder = maturity_ladder(ctx, portfolio_id=portfolio_id)
    if not ladder.get("ok"):
        return ladder
    buckets = ladder["ladder"]
    total = sum(buckets.values()) or 1.0
    top_year, top_val = max(buckets.items(), key=lambda kv: kv[1]) if buckets else ("-", 0.0)
    concentration = top_val / total
    level = "high" if concentration > 0.4 else "medium" if concentration > 0.25 else "low"
    return {
        "ok": True,
        "portfolio_id": portfolio_id,
        "top_year": top_year,
        "concentration": round(concentration, 4),
        "level": level,
        "buckets": len(buckets),
    }


@quantive_tool("data_freshness", "Counts + automation health for ops overview", risk="read")
def data_freshness(ctx: ToolContext) -> dict:
    from app.models import DebtInstrument, OptimizationJob, Portfolio

    return {
        "ok": True,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "portfolios": ctx.db.query(Portfolio).filter(Portfolio.org_id == ctx.org_id).count(),
        "instruments": (
            ctx.db.query(DebtInstrument)
            .join(Portfolio, DebtInstrument.portfolio_id == Portfolio.id)
            .filter(Portfolio.org_id == ctx.org_id)
            .count()
        ),
        "jobs": ctx.db.query(OptimizationJob).filter(OptimizationJob.org_id == ctx.org_id).count(),
    }


@quantive_tool(
    "create_optimization_draft",
    "Create a QUEUED optimization draft (no solver run)",
    risk="write_internal",
    min_role="analyst",
)
def create_optimization_draft(ctx: ToolContext, portfolio_id: str, name: str = "Agent draft") -> dict:
    from app.models import OptimizationJob, Portfolio

    p = (
        ctx.db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.org_id == ctx.org_id)
        .first()
    )
    if not p:
        return {"ok": False, "error": "portfolio not found"}
    job = OptimizationJob(
        portfolio_id=p.id,
        org_id=ctx.org_id,
        created_by=ctx.user.id,
        name=name[:255],
        status="queued",
        objectives={},
        constraints={},
        solver_config={},
        scenario_config={},
    )
    # SQLAlchemy enum column accepts the raw string on SQLite; normalize on read.
    ctx.db.add(job)
    ctx.db.commit()
    ctx.db.refresh(job)
    return {"ok": True, "job_id": job.id, "status": str(job.status)}


@quantive_tool(
    "request_external_action",
    "Record intent for an external/financial action. Never executes directly.",
    risk="needs_approval",
    min_role="analyst",
    cost=5,
)
def request_external_action(ctx: ToolContext, action_type: str, payload: dict | None = None) -> dict:
    allowed = {"send_email", "execute_trade", "make_payment", "delete_data", "publish_report"}
    if action_type not in allowed:
        return {"ok": False, "error": f"unsupported action_type: {action_type}"}
    return {
        "ok": True,
        "recorded": True,
        "action_type": action_type,
        "payload": payload or {},
        "note": "Requires human approval before any real-world effect.",
    }


@quantive_tool("project_summary", "Summarize a project workspace: runs + documents", risk="read")
def project_summary(ctx: ToolContext, project_id: str) -> dict:
    from app.agent.models import AgentRun
    from app.models.project import Project, ProjectDocument

    p = (
        ctx.db.query(Project)
        .filter(Project.id == project_id, Project.org_id == ctx.org_id)
        .first()
    )
    if not p:
        return {"ok": False, "error": "project not found"}
    runs = ctx.db.query(AgentRun).filter(AgentRun.project_id == p.id).all()
    docs = ctx.db.query(ProjectDocument).filter(ProjectDocument.project_id == p.id).all()
    by_status: dict[str, int] = {}
    for r in runs:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    return {
        "ok": True,
        "project_id": p.id,
        "name": p.name,
        "status": p.status,
        "runs": len(runs),
        "runs_by_status": by_status,
        "documents": len(docs),
    }


@quantive_tool(
    "save_note",
    "Save a note into a project folder (default: meeting_notes)",
    risk="write_internal",
    min_role="analyst",
)
def save_note(ctx: ToolContext, project_id: str, title: str, body_text: str = "",
              folder: str = "meeting_notes") -> dict:
    from app.models.project import DOC_FOLDERS, Project, ProjectDocument

    if folder not in DOC_FOLDERS:
        return {"ok": False, "error": f"folder must be one of {list(DOC_FOLDERS)}"}
    p = (
        ctx.db.query(Project)
        .filter(Project.id == project_id, Project.org_id == ctx.org_id)
        .first()
    )
    if not p:
        return {"ok": False, "error": "project not found"}
    d = ProjectDocument(project_id=p.id, org_id=ctx.org_id, folder=folder,
                        title=title[:255], body_text=body_text, uploaded_by=ctx.user.id)
    ctx.db.add(d)
    ctx.db.commit()
    ctx.db.refresh(d)
    return {"ok": True, "document_id": d.id, "folder": folder}


@quantive_tool("list_automations", "List registered automations with last-run status", risk="read")
def list_automations(ctx: ToolContext) -> dict:
    from app.models.automation import Automation
    from app.services import automation_engine

    automation_engine.ensure_automations(ctx.db)
    autos = ctx.db.query(Automation).order_by(Automation.category, Automation.key).all()
    return {
        "ok": True,
        "automations": [
            {"key": a.key, "name": a.name, "category": a.category,
             "enabled": a.enabled, "last_status": a.last_status} for a in autos
        ],
    }


@quantive_tool(
    "run_automation",
    "Run a registered automation (lead scoring, onboarding, dunning, ...). Side effects possible.",
    risk="needs_approval",
    min_role="analyst",
    timeout_seconds=120,
    cost=5,
)
def run_automation(ctx: ToolContext, key: str) -> dict:
    from app.services import automation_engine

    try:
        result = automation_engine.run_automation(key, ctx.db, trigger="agent")
    except KeyError:
        return {"ok": False, "error": f"unknown automation: {key}"}
    return {"ok": result.get("status") != "failed", **result}


@quantive_tool("optimization_status", "Job progress + result counts for verification", risk="read")
def optimization_status(ctx: ToolContext, job_id: str) -> dict:
    from app.models import BenchmarkResult, OptimizationJob, OptimizationResult, Strategy

    job = (
        ctx.db.query(OptimizationJob)
        .filter(OptimizationJob.id == job_id, OptimizationJob.org_id == ctx.org_id)
        .first()
    )
    if not job:
        return {"ok": False, "error": "job not found"}
    return {
        "ok": True,
        "job_id": job.id,
        "status": str(job.status),
        "progress": job.progress,
        "strategies": ctx.db.query(Strategy).filter(Strategy.job_id == job.id).count(),
        "results": ctx.db.query(OptimizationResult).filter(OptimizationResult.job_id == job.id).count(),
        "benchmarks": ctx.db.query(BenchmarkResult).filter(BenchmarkResult.job_id == job.id).count(),
        "error": job.error_message,
    }


@quantive_tool(
    "notify_owner",
    "Create an in-app notification for the run creator (no external send)",
    risk="write_internal",
    min_role="analyst",
)
def notify_owner(ctx: ToolContext, title: str, message: str = "") -> dict:
    from app.models.extended import Notification

    n = Notification(user_id=ctx.user.id, type="system", title=title[:255],
                     message=message[:5000], resource_type="agent_run", resource_id=ctx.run_id)
    ctx.db.add(n)
    ctx.db.commit()
    return {"ok": True, "notification_id": n.id}


@quantive_tool("market_snapshot", "Latest persisted market snapshot for a source", risk="read")
def market_snapshot(ctx: ToolContext, source: str = "treasury_yields") -> dict:
    from app.models.market import SOURCES, MarketSnapshot

    if source not in SOURCES:
        return {"ok": False, "error": f"source must be one of {list(SOURCES)}"}
    snap = (
        ctx.db.query(MarketSnapshot).filter(MarketSnapshot.source == source)
        .order_by(MarketSnapshot.fetched_at.desc()).first()
    )
    if not snap:
        return {"ok": False, "error": "no snapshot yet; market_refresh has not run"}
    return {
        "ok": True,
        "source": source,
        "status": snap.status,
        "records": snap.record_count,
        "fetched_at": snap.fetched_at.isoformat() if snap.fetched_at else None,
        "payload": snap.payload,
    }
