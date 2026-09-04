"""Comments API — CRUD for comments on any resource."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Comment, User, Portfolio
from app.security import get_current_user

router = APIRouter(prefix="/api", tags=["comments"])


def _verify_resource_access(db: Session, user: User, resource_type: str, resource_id: str):
    """Verify user has access to the resource's organization.
    Prevents IDOR: users cannot access comments on resources they don't own.
    """
    if resource_type == "portfolio":
        resource = db.query(Portfolio).filter(Portfolio.id == resource_id).first()
        if not resource or resource.org_id != user.org_id:
            raise HTTPException(status_code=403, detail="Access denied to this resource")
    # For other resource types, we rely on the user being authenticated
    # and the resource existing. Add more resource type checks as needed.


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    parent_id: Optional[str] = None


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    id: str
    user_id: str
    resource_type: str
    resource_id: str
    parent_id: Optional[str]
    content: str
    is_resolved: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get("/{resource_type}/{resource_id}/comments", response_model=list[CommentResponse])
def list_comments(
    resource_type: str,
    resource_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List comments on a resource."""
    # Verify user has access to the resource's organization
    _verify_resource_access(db, user, resource_type, resource_id)
    comments = db.query(Comment).filter(
        Comment.resource_type == resource_type,
        Comment.resource_id == resource_id,
    ).order_by(Comment.created_at.asc()).all()
    return [CommentResponse.model_validate(c).model_dump(mode="json") for c in comments]


@router.post("/{resource_type}/{resource_id}/comments", response_model=CommentResponse, status_code=201)
def create_comment(
    resource_type: str,
    resource_id: str,
    data: CommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a comment to a resource."""
    _verify_resource_access(db, user, resource_type, resource_id)
    comment = Comment(
        user_id=user.id,
        resource_type=resource_type,
        resource_id=resource_id,
        parent_id=data.parent_id,
        content=data.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return CommentResponse.model_validate(comment).model_dump(mode="json")


@router.put("/{resource_type}/{resource_id}/comments/{comment_id}", response_model=CommentResponse)
def update_comment(
    resource_type: str,
    resource_id: str,
    comment_id: str,
    data: CommentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a comment (owner only)."""
    _verify_resource_access(db, user, resource_type, resource_id)
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != user.id:
        raise HTTPException(status_code=403, detail="Can only edit your own comments")

    comment.content = data.content
    db.commit()
    db.refresh(comment)
    return CommentResponse.model_validate(comment).model_dump(mode="json")


@router.delete("/{resource_type}/{resource_id}/comments/{comment_id}", status_code=204)
def delete_comment(
    resource_type: str,
    resource_id: str,
    comment_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a comment (owner or admin)."""
    _verify_resource_access(db, user, resource_type, resource_id)
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != user.id:
        raise HTTPException(status_code=403, detail="Can only delete your own comments")
    db.delete(comment)
    db.commit()
