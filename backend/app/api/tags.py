"""Tags API — CRUD for tags and tagging resources."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tag, TaggedItem, User
from app.security import get_current_user

router = APIRouter(prefix="/api/tags", tags=["tags"])


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#6366f1", max_length=7)


class TagResponse(BaseModel):
    id: str
    name: str
    color: str
    created_at: str

    class Config:
        from_attributes = True


class TagResourceRequest(BaseModel):
    resource_type: str
    resource_id: str


@router.get("", response_model=list[TagResponse])
def list_tags(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all tags for the user's organization."""
    tags = db.query(Tag).filter(Tag.org_id == user.org_id).order_by(Tag.name).all()
    return [TagResponse.model_validate(t).model_dump(mode="json") for t in tags]


@router.post("", response_model=TagResponse, status_code=201)
def create_tag(data: TagCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new tag."""
    existing = db.query(Tag).filter(
        Tag.org_id == user.org_id, Tag.name == data.name
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Tag already exists")

    tag = Tag(org_id=user.org_id, name=data.name, color=data.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagResponse.model_validate(tag).model_dump(mode="json")


@router.delete("/{tag_id}", status_code=204)
def delete_tag(tag_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a tag."""
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.org_id == user.org_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.delete(tag)
    db.commit()


@router.post("/{tag_id}/resources", status_code=201)
def tag_resource(tag_id: str, data: TagResourceRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Associate a tag with a resource."""
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.org_id == user.org_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    existing = db.query(TaggedItem).filter(
        TaggedItem.tag_id == tag_id,
        TaggedItem.resource_type == data.resource_type,
        TaggedItem.resource_id == data.resource_id,
    ).first()
    if existing:
        return {"detail": "Already tagged"}

    item = TaggedItem(tag_id=tag_id, resource_type=data.resource_type, resource_id=data.resource_id)
    db.add(item)
    db.commit()
    return {"detail": "Tagged"}


@router.delete("/{tag_id}/resources/{resource_type}/{resource_id}", status_code=204)
def untag_resource(tag_id: str, resource_type: str, resource_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove a tag from a resource."""
    item = db.query(TaggedItem).filter(
        TaggedItem.tag_id == tag_id,
        TaggedItem.resource_type == resource_type,
        TaggedItem.resource_id == resource_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Tag association not found")
    db.delete(item)
    db.commit()
