"""Project workspaces — persistent continuity + business documents."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.models import AgentRun
from app.agent.runner import create_run, spawn_run
from app.api.agent_api import _run_dict as _agent_run_dict
from app.api.agent_api import _load as _load_agent_run
from app.database import get_db
from app.models import User
from app.models.project import DOC_FOLDERS, Project, ProjectDocument
from app.security import get_current_user

router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateProjectBody(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str = Field(default="", max_length=5000)


class PatchProjectBody(BaseModel):
    status: str = Field(..., pattern="^(active|archived)$")


class CreateDocBody(BaseModel):
    folder: str
    title: str = Field(..., min_length=2, max_length=255)
    body_text: str = Field(default="", max_length=100000)


class ProjectRunBody(BaseModel):
    goal: str = Field(..., min_length=3, max_length=2000)
    steps: list[dict] = Field(..., min_length=1, max_length=25)


def _get_project(project_id: str, user: User, db: Session) -> Project:
    p = db.query(Project).filter(Project.id == project_id, Project.org_id == user.org_id).first()
    if not p:
        raise HTTPException(404, "project not found")
    return p


def _project_dict(p: Project, db: Session) -> dict:
    runs = (
        db.query(AgentRun).filter(AgentRun.project_id == p.id)
        .order_by(AgentRun.created_at.desc()).limit(20).all()
    )
    docs = db.query(ProjectDocument).filter(ProjectDocument.project_id == p.id).all()
    by_folder: dict[str, int] = {}
    for d in docs:
        by_folder[d.folder] = by_folder.get(d.folder, 0) + 1
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "status": p.status,
        "runs": [{"id": r.id, "goal": r.goal, "status": r.status} for r in runs],
        "documents": len(docs),
        "documents_by_folder": by_folder,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.post("", status_code=201)
def create_project(body: CreateProjectBody, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    p = Project(org_id=user.org_id, name=body.name.strip(),
                description=body.description, created_by=user.id)
    db.add(p)
    db.commit()
    db.refresh(p)
    return _project_dict(p, db)


@router.get("")
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Project).filter(Project.org_id == user.org_id)
        .order_by(Project.updated_at.desc()).limit(100).all()
    )
    return {"projects": [{"id": p.id, "name": p.name, "status": p.status} for p in rows]}


@router.get("/{project_id}")
def get_project(project_id: str, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return _project_dict(_get_project(project_id, user, db), db)


@router.patch("/{project_id}")
def patch_project(project_id: str, body: PatchProjectBody, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    p = _get_project(project_id, user, db)
    p.status = body.status
    db.commit()
    db.refresh(p)
    return _project_dict(p, db)


@router.post("/{project_id}/documents", status_code=201)
def add_document(project_id: str, body: CreateDocBody, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    p = _get_project(project_id, user, db)
    if body.folder not in DOC_FOLDERS:
        raise HTTPException(400, f"folder must be one of {list(DOC_FOLDERS)}")
    d = ProjectDocument(project_id=p.id, org_id=user.org_id, folder=body.folder,
                        title=body.title.strip(), body_text=body.body_text, uploaded_by=user.id)
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"id": d.id, "folder": d.folder, "title": d.title}


@router.get("/{project_id}/documents")
def list_documents(project_id: str, folder: str | None = None,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _get_project(project_id, user, db)
    q = db.query(ProjectDocument).filter(ProjectDocument.project_id == p.id)
    if folder:
        q = q.filter(ProjectDocument.folder == folder)
    docs = q.order_by(ProjectDocument.created_at.desc()).limit(100).all()
    return {"documents": [
        {"id": d.id, "folder": d.folder, "title": d.title,
         "body_text": d.body_text, "created_at": d.created_at.isoformat() if d.created_at else None}
        for d in docs
    ]}


@router.post("/{project_id}/runs", status_code=202)
def start_project_run(project_id: str, body: ProjectRunBody,
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Start an agent run inside this project ("continue the Acme project")."""
    p = _get_project(project_id, user, db)
    for s in body.steps:
        if "tool" not in s:
            raise HTTPException(400, "each step needs a 'tool' key")
    try:
        run = create_run(db, user, body.goal, body.steps, project_id=p.id)
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))
    run_id = run.id
    spawn_run(run_id)
    run, steps = _load_agent_run(run_id, db)
    return _agent_run_dict(run, steps)
