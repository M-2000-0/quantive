"""Watchlists API — CRUD for monitoring watchlists."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Watchlist, WatchlistItem
from app.security import get_current_user

router = APIRouter(prefix="/api/watchlists", tags=["watchlists"])


class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class WatchlistUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class WatchlistItemCreate(BaseModel):
    resource_type: str = Field(..., description="portfolio or instrument")
    resource_id: str
    alert_threshold: Optional[dict] = None
    notes: str = ""


class WatchlistResponse(BaseModel):
    id: str
    name: str
    description: str
    is_default: bool
    item_count: int = 0
    created_at: str

    class Config:
        from_attributes = True


class WatchlistItemResponse(BaseModel):
    id: str
    resource_type: str
    resource_id: str
    alert_threshold: Optional[dict]
    notes: str
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[WatchlistResponse])
def list_watchlists(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all watchlists for the current user."""
    watchlists = db.query(Watchlist).filter(Watchlist.user_id == user.id).order_by(Watchlist.name).all()
    result = []
    for wl in watchlists:
        count = db.query(WatchlistItem).filter(WatchlistItem.watchlist_id == wl.id).count()
        resp = WatchlistResponse.model_validate(wl).model_dump(mode="json")
        resp["item_count"] = count
        result.append(resp)
    return result


@router.post("", response_model=WatchlistResponse, status_code=201)
def create_watchlist(data: WatchlistCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new watchlist."""
    wl = Watchlist(user_id=user.id, name=data.name, description=data.description)
    db.add(wl)
    db.commit()
    db.refresh(wl)
    resp = WatchlistResponse.model_validate(wl).model_dump(mode="json")
    resp["item_count"] = 0
    return resp


@router.get("/{watchlist_id}", response_model=WatchlistResponse)
def get_watchlist(watchlist_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a watchlist with its items."""
    wl = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == user.id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    count = db.query(WatchlistItem).filter(WatchlistItem.watchlist_id == wl.id).count()
    resp = WatchlistResponse.model_validate(wl).model_dump(mode="json")
    resp["item_count"] = count
    return resp


@router.put("/{watchlist_id}", response_model=WatchlistResponse)
def update_watchlist(watchlist_id: str, data: WatchlistUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a watchlist."""
    wl = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == user.id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    if data.name is not None:
        wl.name = data.name
    if data.description is not None:
        wl.description = data.description
    db.commit()
    db.refresh(wl)
    return WatchlistResponse.model_validate(wl).model_dump(mode="json")


@router.delete("/{watchlist_id}", status_code=204)
def delete_watchlist(watchlist_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a watchlist."""
    wl = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == user.id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    db.delete(wl)
    db.commit()


@router.get("/{watchlist_id}/items", response_model=list[WatchlistItemResponse])
def list_watchlist_items(watchlist_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List items in a watchlist."""
    wl = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == user.id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    items = db.query(WatchlistItem).filter(WatchlistItem.watchlist_id == watchlist_id).all()
    return [WatchlistItemResponse.model_validate(i).model_dump(mode="json") for i in items]


@router.post("/{watchlist_id}/items", response_model=WatchlistItemResponse, status_code=201)
def add_watchlist_item(watchlist_id: str, data: WatchlistItemCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add an item to a watchlist."""
    wl = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == user.id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    item = WatchlistItem(
        watchlist_id=watchlist_id,
        resource_type=data.resource_type,
        resource_id=data.resource_id,
        alert_threshold=data.alert_threshold,
        notes=data.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return WatchlistItemResponse.model_validate(item).model_dump(mode="json")


@router.delete("/{watchlist_id}/items/{item_id}", status_code=204)
def remove_watchlist_item(watchlist_id: str, item_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove an item from a watchlist."""
    wl = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == user.id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    item = db.query(WatchlistItem).filter(WatchlistItem.id == item_id, WatchlistItem.watchlist_id == watchlist_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    db.delete(item)
    db.commit()
