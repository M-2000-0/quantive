"""Tasks API — CRUD, assignment, and status management."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.tasks import Task, TaskComment
from app.security import get_current_user

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    priority: str = "medium"
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None


class TaskCommentCreate(BaseModel):
    content: str = Field(..., min_length=1)


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    status: str
    priority: str
    created_by: str
    assigned_to: Optional[str]
    due_date: Optional[str]
    comment_count: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TaskCommentResponse(BaseModel):
    id: str
    task_id: str
    user_id: str
    content: str
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List tasks for the organization."""
    q = db.query(Task).filter(Task.org_id == user.org_id)
    if status:
        q = q.filter(Task.status == status)
    if priority:
        q = q.filter(Task.priority == priority)
    if assigned_to:
        q = q.filter(Task.assigned_to == assigned_to)
    tasks = q.order_by(desc(Task.created_at)).offset(offset).limit(limit).all()
    result = []
    for t in tasks:
        count = db.query(TaskComment).filter(TaskComment.task_id == t.id).count()
        resp = TaskResponse.model_validate(t).model_dump(mode="json")
        resp["comment_count"] = count
        result.append(resp)
    return result


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(data: TaskCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new task."""
    task = Task(
        org_id=user.org_id,
        title=data.title,
        description=data.description,
        priority=data.priority,
        created_by=user.id,
        assigned_to=data.assigned_to,
        due_date=data.due_date,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    resp = TaskResponse.model_validate(task).model_dump(mode="json")
    resp["comment_count"] = 0
    return resp


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a single task."""
    task = db.query(Task).filter(Task.id == task_id, Task.org_id == user.org_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    count = db.query(TaskComment).filter(TaskComment.task_id == task.id).count()
    resp = TaskResponse.model_validate(task).model_dump(mode="json")
    resp["comment_count"] = count
    return resp


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: str, data: TaskUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a task."""
    task = db.query(Task).filter(Task.id == task_id, Task.org_id == user.org_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return TaskResponse.model_validate(task).model_dump(mode="json")


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a task."""
    task = db.query(Task).filter(Task.id == task_id, Task.org_id == user.org_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()


@router.get("/{task_id}/comments", response_model=list[TaskCommentResponse])
def list_comments(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List comments on a task."""
    task = db.query(Task).filter(Task.id == task_id, Task.org_id == user.org_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    comments = db.query(TaskComment).filter(TaskComment.task_id == task_id).order_by(TaskComment.created_at).all()
    return [TaskCommentResponse.model_validate(c).model_dump(mode="json") for c in comments]


@router.post("/{task_id}/comments", response_model=TaskCommentResponse, status_code=201)
def add_comment(task_id: str, data: TaskCommentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add a comment to a task."""
    task = db.query(Task).filter(Task.id == task_id, Task.org_id == user.org_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    comment = TaskComment(task_id=task_id, user_id=user.id, content=data.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return TaskCommentResponse.model_validate(comment).model_dump(mode="json")
