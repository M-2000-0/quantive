"""User Preferences, Organization Settings, and Saved Views/Filters APIs."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Organization, User, UserPreferences, UserRole
from app.security import get_current_user, require_role

# ── User Preferences ────────────────────────────────────────────────────────

pref_router = APIRouter(prefix="/api/preferences", tags=["preferences"])


class PreferencesUpdate(BaseModel):
    theme: Optional[str] = Field(None, description="light, dark, system")
    language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    date_format: Optional[str] = None
    number_format: Optional[str] = None
    currency_display: Optional[str] = None
    notifications_email: Optional[bool] = None
    notifications_in_app: Optional[bool] = None
    dashboard_config: Optional[dict] = None


class PreferencesResponse(BaseModel):
    theme: str
    language: str
    timezone: str
    date_format: str
    number_format: str
    currency_display: str
    notifications_email: bool
    notifications_in_app: bool
    dashboard_config: Optional[dict]

    class Config:
        from_attributes = True


@pref_router.get("", response_model=PreferencesResponse)
def get_preferences(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user preferences."""
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user.id).first()
    if not prefs:
        return PreferencesResponse(
            theme="light", language="en", timezone="UTC",
            date_format="YYYY-MM-DD", number_format="en-US", currency_display="USD",
            notifications_email=True, notifications_in_app=True, dashboard_config=None,
        )
    return prefs


@pref_router.put("", response_model=PreferencesResponse)
def update_preferences(data: PreferencesUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update user preferences."""
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user.id).first()
    if not prefs:
        from app.models.extended import UserPreferences as UP
        prefs = UP(user_id=user.id)
        db.add(prefs)
        db.flush()

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    for key, value in updates.items():
        setattr(prefs, key, value)

    db.commit()
    db.refresh(prefs)
    return prefs


# ── Organization Settings ───────────────────────────────────────────────────

org_router = APIRouter(prefix="/api/organization", tags=["organization"])


class OrgSettingsUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class OrgSettingsResponse(BaseModel):
    id: str
    name: str
    created_at: str
    member_count: int = 0
    portfolio_count: int = 0
    optimization_count: int = 0

    class Config:
        from_attributes = True


@org_router.get("/settings", response_model=OrgSettingsResponse)
def get_org_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get organization settings and stats."""
    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    from app.models import Portfolio, OptimizationJob
    member_count = db.query(User).filter(User.org_id == user.org_id).count()
    portfolio_count = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).count()
    optimization_count = db.query(OptimizationJob).filter(OptimizationJob.org_id == user.org_id).count()

    return OrgSettingsResponse(
        id=org.id,
        name=org.name,
        created_at=org.created_at.isoformat(),
        member_count=member_count,
        portfolio_count=portfolio_count,
        optimization_count=optimization_count,
    )


@org_router.put("/settings", response_model=OrgSettingsResponse)
def update_org_settings(
    data: OrgSettingsUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Update organization settings (admin only)."""
    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if data.name:
        org.name = data.name
    db.commit()
    db.refresh(org)
    return get_org_settings(user, db)


# ── Saved Views ─────────────────────────────────────────────────────────────

views_router = APIRouter(prefix="/api/views", tags=["views"])


class SavedViewCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    view_type: str = Field(..., description="portfolio, optimization, analytics")
    config: dict = Field(default_factory=dict)
    is_shared: bool = False


class SavedViewUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[dict] = None
    is_shared: Optional[bool] = None


class SavedViewResponse(BaseModel):
    id: str
    name: str
    view_type: str
    config: dict
    is_default: bool
    is_shared: bool
    created_at: str

    class Config:
        from_attributes = True


@views_router.get("", response_model=list[SavedViewResponse])
def list_views(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List saved views for the current user."""
    from app.models import SavedView
    views = db.query(SavedView).filter(SavedView.user_id == user.id).order_by(SavedView.name).all()
    return [SavedViewResponse.model_validate(v).model_dump(mode="json") for v in views]


@views_router.post("", response_model=SavedViewResponse, status_code=201)
def create_view(data: SavedViewCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new saved view."""
    from app.models import SavedView
    view = SavedView(
        user_id=user.id,
        name=data.name,
        view_type=data.view_type,
        config=data.config,
        is_shared=data.is_shared,
    )
    db.add(view)
    db.commit()
    db.refresh(view)
    return SavedViewResponse.model_validate(view).model_dump(mode="json")


@views_router.put("/{view_id}", response_model=SavedViewResponse)
def update_view(view_id: str, data: SavedViewUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a saved view."""
    from app.models import SavedView
    view = db.query(SavedView).filter(SavedView.id == view_id, SavedView.user_id == user.id).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    if data.name is not None:
        view.name = data.name
    if data.config is not None:
        view.config = data.config
    if data.is_shared is not None:
        view.is_shared = data.is_shared
    db.commit()
    db.refresh(view)
    return SavedViewResponse.model_validate(view).model_dump(mode="json")


@views_router.delete("/{view_id}", status_code=204)
def delete_view(view_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a saved view."""
    from app.models import SavedView
    view = db.query(SavedView).filter(SavedView.id == view_id, SavedView.user_id == user.id).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    db.delete(view)
    db.commit()


# ── Saved Filters ───────────────────────────────────────────────────────────

filters_router = APIRouter(prefix="/api/filters", tags=["filters"])


class SavedFilterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    filter_type: str
    filters: dict = Field(default_factory=dict)
    is_default: bool = False


class SavedFilterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    filters: Optional[dict] = None
    is_default: Optional[bool] = None


class SavedFilterResponse(BaseModel):
    id: str
    name: str
    filter_type: str
    filters: dict
    is_default: bool
    created_at: str

    class Config:
        from_attributes = True


@filters_router.get("", response_model=list[SavedFilterResponse])
def list_filters(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List saved filters for the current user."""
    from app.models import SavedFilter
    filters = db.query(SavedFilter).filter(SavedFilter.user_id == user.id).order_by(SavedFilter.name).all()
    return [SavedFilterResponse.model_validate(f).model_dump(mode="json") for f in filters]


@filters_router.post("", response_model=SavedFilterResponse, status_code=201)
def create_filter(data: SavedFilterCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new saved filter."""
    from app.models import SavedFilter
    filt = SavedFilter(
        user_id=user.id,
        name=data.name,
        filter_type=data.filter_type,
        filters=data.filters,
        is_default=data.is_default,
    )
    db.add(filt)
    db.commit()
    db.refresh(filt)
    return SavedFilterResponse.model_validate(filt).model_dump(mode="json")


@filters_router.put("/{filter_id}", response_model=SavedFilterResponse)
def update_filter(filter_id: str, data: SavedFilterUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a saved filter."""
    from app.models import SavedFilter
    filt = db.query(SavedFilter).filter(SavedFilter.id == filter_id, SavedFilter.user_id == user.id).first()
    if not filt:
        raise HTTPException(status_code=404, detail="Filter not found")
    if data.name is not None:
        filt.name = data.name
    if data.filters is not None:
        filt.filters = data.filters
    if data.is_default is not None:
        filt.is_default = data.is_default
    db.commit()
    db.refresh(filt)
    return SavedFilterResponse.model_validate(filt).model_dump(mode="json")


@filters_router.delete("/{filter_id}", status_code=204)
def delete_filter(filter_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a saved filter."""
    from app.models import SavedFilter
    filt = db.query(SavedFilter).filter(SavedFilter.id == filter_id, SavedFilter.user_id == user.id).first()
    if not filt:
        raise HTTPException(status_code=404, detail="Filter not found")
    db.delete(filt)
    db.commit()
