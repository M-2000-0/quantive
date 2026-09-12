"""Agent execution API — runs, approvals, audit trail.

Execution is asynchronous: POST returns 202 immediately with a run snapshot
(queued/running/waiting_approval) and a daemon worker thread drives the
plan→execute→verify loop, mirroring app/api/optimizations.py. Clients poll
GET /runs/{id} for terminal state (completed/failed/cancelled).
"""
from __future__ import annotations

import logging
import threading

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import app.database as database_module
from app.agent.models import AgentRun, AgentStep
from app.agent.runner import approve_step, cancel_run, create_run, execute_run
from app.database import get_db
from app.models import User
from app.security import get_current_user

logger = logging.getLogger("quantive.agent_api")

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Tracked for tests/teardown joins (same pattern as optimizations._job_threads).
_agent_threads: set = set()


class PlanStep(BaseModel):
    tool: str
    args: dict = Field(default_factory=dict)


class CreateRunBody(BaseModel):
    goal: str = Field(..., min_length=3, max_length=2000)
    steps: list[PlanStep] = Field(..., min_length=1, max_length=25)


class ApproveBody(BaseModel):
    approved: bool
    comment: str = ""


def _step_dict(s: AgentStep) -> dict:
    return {
        "seq": s.seq,
        "tool": s.tool_name,
        "args": s.args,
        "status": s.status,
        "output": s.output,
        "approval_status": s.approval_status,
        "approved_by": s.approved_by,
        "approved_at": s.approved_at.isoformat() if s.approved_at else None,
        "error": s.error,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "finished_at": s.finished_at.isoformat() if s.finished_at else None,
    }


def _run_dict(run: AgentRun, steps: list[AgentStep]) -> dict:
    return {
        "id": run.id,
        "goal": run.goal,
        "status": run.status,
        "current_step": run.current_step,
        "error": run.error,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "steps": [_step_dict(s) for s in sorted(steps, key=lambda x: x.seq)],
    }


def _load(run_id: str, db: Session) -> tuple[AgentRun, list[AgentStep]]:
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "run not found")
    steps = db.query(AgentStep).filter(AgentStep.run_id == run_id).order_by(AgentStep.seq).all()
    return run, steps


def _spawn(run_id: str) -> None:
    """Drive a run in a daemon thread with its own DB session."""
    _session_factory = database_module.SessionLocal

    def _run():
        db = _session_factory()
        try:
            execute_run(db, run_id)
        except Exception:
            logger.exception("agent run %s failed", run_id)
        finally:
            db.close()
            _agent_threads.discard(threading.current_thread())

    thread = threading.Thread(target=_run, daemon=True)
    _agent_threads.add(thread)
    thread.start()


@router.get("/tools")
def agent_tools(user: User = Depends(get_current_user)):
    from app.agent.tools import registry

    return {"tools": registry.describe()}


@router.post("/runs", status_code=202)
def start_run(body: CreateRunBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Org isolation: runner scopes every tool to user.org_id.
    if user.org_id is None:
        raise HTTPException(400, "user has no organization")
    try:
        run = create_run(db, user, body.goal, [s.model_dump() for s in body.steps])
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))
    run_id = run.id
    _spawn(run_id)
    run, steps = _load(run_id, db)
    return _run_dict(run, steps)


@router.get("/runs")
def list_runs(limit: int = 20, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    runs = (
        db.query(AgentRun)
        .filter(AgentRun.org_id == user.org_id)
        .order_by(AgentRun.created_at.desc())
        .limit(min(max(limit, 1), 100))
        .all()
    )
    return {"runs": [{"id": r.id, "goal": r.goal, "status": r.status} for r in runs]}


@router.get("/runs/{run_id}")
def get_run(run_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run, steps = _load(run_id, db)
    if run.org_id != user.org_id:
        raise HTTPException(404, "run not found")
    return _run_dict(run, steps)


@router.post("/runs/{run_id}/steps/{seq}/approve")
def approve(run_id: str, seq: int, body: ApproveBody,
            user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Approval requires analyst+. Four-eyes (approver != creator) is enforced
    # in approve_step and mapped to 403 here.
    if str(getattr(user.role, "value", user.role)) not in ("analyst", "admin"):
        raise HTTPException(403, "approval requires analyst role")
    run, _ = _load(run_id, db)
    if run.org_id != user.org_id:
        raise HTTPException(404, "run not found")
    try:
        run = approve_step(db, run_id, seq, body.approved, start=False,
                           approver=user, comment=body.comment)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    from app.security import log_audit_event

    try:
        log_audit_event(
            db, user,
            action=f"agent.step.{'approved' if body.approved else 'rejected'}",
            resource_type="agent_run", resource_id=run_id, org_id=user.org_id,
            metadata={"seq": seq, "tool": run.plan[seq].get("tool") if seq < len(run.plan or []) else None},
        )
    except Exception:
        pass
    if body.approved and run.status == "queued":
        _spawn(run_id)
        run, steps = _load(run_id, db)
        return _run_dict(run, steps)
    run, steps = _load(run_id, db)
    return _run_dict(run, steps)


@router.post("/runs/{run_id}/cancel")
def cancel(run_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run, _ = _load(run_id, db)
    if run.org_id != user.org_id:
        raise HTTPException(404, "run not found")
    run = cancel_run(db, run_id)
    run, steps = _load(run_id, db)
    return _run_dict(run, steps)
