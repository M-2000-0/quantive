"""Plan → execute → verify loop (synchronous MVP, DB-persisted).

GOAL → PLAN (validated tool list) → EXECUTE (RBAC + approval + timeout)
     → OBSERVE (output stored) → VERIFY (ok flag) → NEXT / COMPLETED.

Approval: tools with risk == needs_approval stop the run in
`waiting_approval` until a human approves that exact step.
Timeouts: each step runs in a worker thread with ToolSpec.timeout_seconds.
Audit: every step completion/failure writes an AuditEvent.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.agent import builtin_tools  # noqa: F401  (register built-ins)
from app.agent.models import AgentRun, AgentStep
from app.agent.tools import NEEDS_APPROVAL, ToolContext, registry


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _audit(db: Session, user: Any, run_id: str, step: AgentStep, decision: str) -> None:
    try:
        from app.security import log_audit_event

        log_audit_event(
            db,
            user,
            action=f"agent.step.{step.status}",
            resource_type="agent_run",
            resource_id=run_id,
            org_id=getattr(user, "org_id", None),
            metadata={
                "tool": step.tool_name,
                "seq": step.seq,
                "decision": decision,
                "approval_status": step.approval_status,
            },
        )
    except Exception:
        pass  # audit must never break execution


def create_run(db: Session, user: Any, goal: str, steps: list[dict]) -> AgentRun:
    if not goal or not goal.strip():
        raise ValueError("goal is required")
    if not steps or len(steps) > 25:
        raise ValueError("steps must contain 1..25 items")
    for s in steps:
        if "tool" not in s:
            raise ValueError("each step needs a 'tool' key")
        registry.get(s["tool"])  # validates name now

    run = AgentRun(org_id=user.org_id, actor_id=user.id, goal=goal.strip(), status="queued", plan=steps)
    db.add(run)
    db.flush()
    for i, s in enumerate(steps):
        db.add(
            AgentStep(
                run_id=run.id, seq=i, tool_name=s["tool"], args=s.get("args", {}) or {},
            )
        )
    db.commit()
    db.refresh(run)
    return run


def _run_tool(spec, ctx: ToolContext, args: dict) -> dict:
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(spec.func, ctx, **args)
        return fut.result(timeout=spec.timeout_seconds)


def execute_run(db: Session, run_id: str, max_cost: int = 50) -> AgentRun:
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise KeyError(f"Unknown run: {run_id}")
    if run.status in ("completed", "failed", "cancelled"):
        return run

    from app.models import User as UserModel

    user = db.query(UserModel).filter(UserModel.id == run.actor_id).first()
    role = getattr(user, "role", "viewer")
    role = getattr(role, "value", role)  # UserRole enum -> str
    spent = 0

    run.status = "running"
    db.commit()

    steps = db.query(AgentStep).filter(AgentStep.run_id == run.id).order_by(AgentStep.seq).all()
    for step in steps:
        if step.status in ("completed", "skipped"):
            continue
        if step.status == "rejected":
            run.status = "failed"
            run.error = f"step {step.seq} rejected"
            break
        spec = registry.get(step.tool_name)
        spent += spec.cost
        if spent > max_cost:
            step.status = "failed"
            step.error = f"cost budget exceeded (>{max_cost})"
            run.status = "failed"
            run.error = step.error
            db.commit()
            break
        if not spec.allows(str(role)):
            step.status = "failed"
            step.error = f"role '{role}' may not run '{spec.name}' (min: {spec.min_role})"
            run.status = "failed"
            run.error = step.error
            _audit(db, user, run.id, step, "deny-rbac")
            db.commit()
            break
        if spec.risk == NEEDS_APPROVAL and step.approval_status != "approved":
            step.status = "waiting_approval"
            step.approval_status = "pending"
            run.status = "waiting_approval"
            run.current_step = step.seq
            _audit(db, user, run.id, step, "wait-approval")
            db.commit()
            break

        step.status = "running"
        step.started_at = _now()
        db.commit()
        t0 = time.perf_counter()
        try:
            ctx = ToolContext(db=db, user=user, org_id=run.org_id, run_id=run.id, step_seq=step.seq)
            out = _run_tool(spec, ctx, step.args or {})
            if not isinstance(out, dict):
                out = {"ok": True, "result": out}
            step.output = out
            step.finished_at = _now()
            if out.get("ok") is False:
                step.status = "failed"
                step.error = str(out.get("error", "tool returned ok=false"))[:2000]
                run.status = "failed"
                run.error = f"step {step.seq} ({step.tool_name}) failed"
                _audit(db, user, run.id, step, "verify-fail")
                db.commit()
                break
            step.status = "completed"
            run.current_step = step.seq + 1
            _audit(
                db, user, run.id, step,
                f"ok in {time.perf_counter() - t0:.2f}s",
            )
            db.commit()
        except FuturesTimeout:
            step.status = "failed"
            step.error = f"timeout after {spec.timeout_seconds}s"
            step.finished_at = _now()
            run.status = "failed"
            run.error = step.error
            _audit(db, user, run.id, step, "timeout")
            db.commit()
            break
        except TypeError as e:  # bad args
            step.status = "failed"
            step.error = f"bad args: {e}"[:2000]
            step.finished_at = _now()
            run.status = "failed"
            run.error = step.error
            _audit(db, user, run.id, step, "verify-fail")
            db.commit()
            break
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
            step = db.query(AgentStep).filter(
                AgentStep.run_id == run_id, AgentStep.seq == step.seq
            ).first()
            step.status = "failed"
            step.error = f"{type(e).__name__}: {e}"[:2000]
            step.finished_at = _now()
            run.status = "failed"
            run.error = step.error
            _audit(db, user, run.id, step, "error")
            db.commit()
            break
    else:
        run.status = "completed"
        run.completed_at = _now()
        db.commit()

    if run.status in ("completed", "failed"):
        run.completed_at = run.completed_at or _now()
        db.commit()
    db.refresh(run)
    return run


def approve_step(
    db: Session,
    run_id: str,
    seq: int,
    approved: bool,
    start: bool = True,
    approver: Any | None = None,
    comment: str = "",
) -> AgentRun:
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise KeyError(f"Unknown run: {run_id}")
    step = (
        db.query(AgentStep)
        .filter(AgentStep.run_id == run_id, AgentStep.seq == seq)
        .first()
    )
    if not step:
        raise KeyError(f"Unknown step {seq}")
    if step.status != "waiting_approval":
        raise ValueError("step is not awaiting approval")
    # Four-eyes: the run creator may never approve their own step.
    if approver is not None and getattr(approver, "id", None) == run.actor_id:
        raise PermissionError("four-eyes: approver must differ from run creator")
    step.approved_by = getattr(approver, "id", None)
    step.approved_at = _now()
    step.approve_comment = (comment or "")[:2000]
    if approved:
        step.approval_status = "approved"
        step.status = "pending"
        run.status = "queued"
        db.commit()
        if start:
            return execute_run(db, run_id)
        db.refresh(run)
        return run
    step.approval_status = "rejected"
    step.status = "rejected"
    step.finished_at = _now()
    run.status = "failed"
    run.error = f"step {seq} rejected by approver"
    run.completed_at = _now()
    db.commit()
    db.refresh(run)
    return run


def cancel_run(db: Session, run_id: str) -> AgentRun:
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise KeyError(f"Unknown run: {run_id}")
    if run.status not in ("completed", "failed", "cancelled"):
        run.status = "cancelled"
        run.completed_at = _now()
        db.query(AgentStep).filter(
            AgentStep.run_id == run_id, AgentStep.status.in_(["pending", "waiting_approval"])
        ).update({"status": "skipped"}, synchronize_session=False)
        db.commit()
    db.refresh(run)
    return run
