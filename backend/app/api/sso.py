"""SSO/SAML API routes for government identity provider integration.

Endpoints:
    POST /api/sso/providers          - Create SSO provider
    GET  /api/sso/providers          - List SSO providers for org
    GET  /api/sso/providers/{id}     - Get SSO provider details
    PUT  /api/sso/providers/{id}     - Update SSO provider
    DELETE /api/sso/providers/{id}   - Delete SSO provider
    GET  /api/sso/providers/{id}/metadata - SP SAML metadata XML
    POST /api/sso/login              - Initiate SP-initiated SSO
    POST /api/sso/acs                - Assertion Consumer Service (IdP callback)
    POST /api/sso/slo                - Single Logout
    GET  /api/sso/sessions           - List active SSO sessions
    DELETE /api/sso/sessions/{id}    - Revoke an SSO session
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.sso import SSOProvider, SSOProviderStatus, SSOProviderType, SSOSession
from app.security import get_current_user, log_audit_event
from app.security.sso import SAMLHandler, SSOLoginError

router = APIRouter(prefix="/api/sso", tags=["sso"])


# ── Request/Response Schemas ─────────────────────────────────────

class SSOProviderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    provider_type: SSOProviderType = SSOProviderType.SAML
    entity_id: str = Field(..., description="IdP Entity ID")
    sso_url: str = Field(..., description="IdP SSO URL")
    slo_url: Optional[str] = None
    x509_cert: Optional[str] = None
    metadata_url: Optional[str] = None
    attribute_mapping: Optional[dict] = None
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    enforce_sso: bool = False
    auto_provision_users: bool = True
    default_role: str = "analyst"


class SSOProviderUpdate(BaseModel):
    name: Optional[str] = None
    entity_id: Optional[str] = None
    sso_url: Optional[str] = None
    slo_url: Optional[str] = None
    x509_cert: Optional[str] = None
    metadata_url: Optional[str] = None
    attribute_mapping: Optional[dict] = None
    name_id_format: Optional[str] = None
    enforce_sso: Optional[bool] = None
    auto_provision_users: Optional[bool] = None
    default_role: Optional[str] = None
    status: Optional[SSOProviderStatus] = None


class SSOProviderResponse(BaseModel):
    id: str
    name: str
    provider_type: SSOProviderType
    status: SSOProviderStatus
    entity_id: Optional[str] = None
    sso_url: Optional[str] = None
    enforce_sso: bool
    auto_provision_users: bool
    default_role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SSOLoginRequest(BaseModel):
    provider_id: str
    relay_state: Optional[str] = None


class SSOLoginResponse(BaseModel):
    url: str
    saml_request: str
    relay_state: str


class SSOCallbackResponse(BaseModel):
    user_id: str
    email: str
    name: str
    is_new_user: bool
    access_token: str
    refresh_token: str


class SSOSessionResponse(BaseModel):
    id: str
    user_id: str
    provider_id: str
    session_index: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None


# ── Provider Management ──────────────────────────────────────────

@router.post("/providers", response_model=SSOProviderResponse, status_code=201)
def create_sso_provider(
    body: SSOProviderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new SSO identity provider for this organization."""
    provider = SSOProvider(
        org_id=user.org_id,
        name=body.name,
        provider_type=body.provider_type,
        entity_id=body.entity_id,
        sso_url=body.sso_url,
        slo_url=body.slo_url,
        x509_cert=body.x509_cert,
        metadata_url=body.metadata_url,
        attribute_mapping=body.attribute_mapping,
        name_id_format=body.name_id_format,
        enforce_sso=body.enforce_sso,
        auto_provision_users=body.auto_provision_users,
        default_role=body.default_role,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)

    log_audit_event(db, user, "sso_provider_create", "sso_provider", provider.id, metadata={"name": body.name})

    return provider


@router.get("/providers", response_model=list[SSOProviderResponse])
def list_sso_providers(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all SSO providers configured for this organization."""
    return db.query(SSOProvider).filter(SSOProvider.org_id == user.org_id).all()


@router.get("/providers/{provider_id}", response_model=SSOProviderResponse)
def get_sso_provider(
    provider_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get SSO provider details."""
    provider = db.query(SSOProvider).filter(
        SSOProvider.id == provider_id,
        SSOProvider.org_id == user.org_id,
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found")
    return provider


@router.put("/providers/{provider_id}", response_model=SSOProviderResponse)
def update_sso_provider(
    provider_id: str,
    body: SSOProviderUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update SSO provider configuration."""
    provider = db.query(SSOProvider).filter(
        SSOProvider.id == provider_id,
        SSOProvider.org_id == user.org_id,
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(provider, field, value)

    db.commit()
    db.refresh(provider)

    log_audit_event(db, user, "sso_provider_update", "sso_provider", provider.id, metadata={"fields": list(update_data.keys())})

    return provider


@router.delete("/providers/{provider_id}", status_code=204)
def delete_sso_provider(
    provider_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an SSO provider and all associated links."""
    provider = db.query(SSOProvider).filter(
        SSOProvider.id == provider_id,
        SSOProvider.org_id == user.org_id,
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found")

    db.delete(provider)
    db.commit()

    log_audit_event(db, user, "sso_provider_delete", "sso_provider", provider_id)


@router.get("/providers/{provider_id}/metadata", response_class=None)
def get_sso_metadata(
    provider_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get SP SAML metadata XML for IdP registration."""
    provider = db.query(SSOProvider).filter(
        SSOProvider.id == provider_id,
        SSOProvider.org_id == user.org_id,
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found")

    handler = SAMLHandler(provider)
    metadata_xml = handler.generate_metadata()

    from fastapi.responses import Response
    return Response(content=metadata_xml, media_type="application/xml")


# ── SSO Login Flow ──────────────────────────────────────────────

@router.post("/login", response_model=SSOLoginResponse)
def initiate_sso_login(
    body: SSOLoginRequest,
    db: Session = Depends(get_db),
):
    """Initiate SP-initiated SSO. Returns the IdP URL and encoded AuthnRequest."""
    provider = db.query(SSOProvider).filter(
        SSOProvider.id == body.provider_id,
        SSOProvider.status == SSOProviderStatus.ACTIVE,
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Active SSO provider not found")

    handler = SAMLHandler(provider)
    auth_request = handler.create_auth_request(relay_state=body.relay_state or "")

    return SSOLoginResponse(
        url=auth_request["url"],
        saml_request=auth_request["saml_request"],
        relay_state=auth_request["relay_state"],
    )


@router.post("/acs")
def sso_assertion_consumer(
    request: Request,
    response: Response,
    SAMLResponse: str = Form(...),
    RelayState: str = Form(""),
    db: Session = Depends(get_db),
):
    """Assertion Consumer Service - receives SAML Response from IdP.

    This is the callback URL that the IdP redirects to after authentication.
    Processes the SAML response, creates/finds the user, and sets session cookies.
    """
    # Find provider by looking up which org this is for
    # In production, the RelayState would contain the provider_id or org context
    # For now, find any active provider (single IdP per deployment is common in gov)
    providers = db.query(SSOProvider).filter(
        SSOProvider.status == SSOProviderStatus.ACTIVE,
    ).all()

    if not providers:
        raise HTTPException(status_code=400, detail="No active SSO provider configured")

    # Try each provider (in practice, filter by entity_id from the assertion)
    last_error = None
    for provider in providers:
        try:
            handler = SAMLHandler(provider)
            result = handler.process_sso_response(
                saml_response_b64=SAMLResponse,
                db=db,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

            # Generate JWT tokens for the authenticated user
            from app.security import create_access_token, create_refresh_token

            access_token = create_access_token({
                "sub": result["user_id"],
                "org_id": provider.org_id,
            })
            refresh_token = create_refresh_token({
                "sub": result["user_id"],
                "org_id": provider.org_id,
            })

            # Set httpOnly cookies (matching existing auth pattern)
            from app.config import get_settings
            settings = get_settings()

            response.set_cookie(
                "access_token",
                access_token,
                httponly=True,
                secure=settings.SECURE_COOKIES,
                samesite="strict",
                max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                path="/",
            )
            response.set_cookie(
                "refresh_token",
                refresh_token,
                httponly=True,
                secure=settings.SECURE_COOKIES,
                samesite="strict",
                max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
                path="/",
            )

            log_audit_event(
                db, None, "sso_login_success", "user", result["user_id"],
                org_id=provider.org_id,
                metadata={"email": result["email"], "is_new": result["is_new_user"]},
                ip_address=request.client.host if request.client else None,
            )

            return {
                "user_id": result["user_id"],
                "email": result["email"],
                "name": result["name"],
                "is_new_user": result["is_new_user"],
                "access_token": access_token,
                "refresh_token": refresh_token,
            }

        except SSOLoginError as e:
            last_error = e
            continue

    raise HTTPException(status_code=401, detail=f"SAML authentication failed: {last_error}")


@router.post("/slo")
def sso_single_logout(
    request: Request,
    response: Response,
    SAMLResponse: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Single Logout - invalidate SSO session and redirect to IdP for global logout."""
    # Find active sessions for this user
    sessions = db.query(SSOSession).filter(
        SSOSession.user_id == user.id,
        SSOSession.expires_at > datetime.now(timezone.utc),
    ).all()

    for session in sessions:
        provider = db.query(SSOProvider).filter(SSOProvider.id == session.provider_id).first()
        if provider and provider.slo_url:
            handler = SAMLHandler(provider)
            handler.create_logout_request(
                name_id=session.name_id or user.email,
                session_index=session.session_index,
            )
            # In a real implementation, redirect to IdP SLO URL
            break

    # Delete all SSO sessions for this user
    db.query(SSOSession).filter(SSOSession.user_id == user.id).delete()
    db.commit()

    # Clear cookies
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")

    log_audit_event(db, user, "sso_logout", "user", user.id)

    return {"message": "Logged out successfully"}


# ── Session Management ──────────────────────────────────────────

@router.get("/sessions", response_model=list[SSOSessionResponse])
def list_sso_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List active SSO sessions for the current user."""
    return db.query(SSOSession).filter(
        SSOSession.user_id == user.id,
        SSOSession.expires_at > datetime.now(timezone.utc),
    ).all()


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_sso_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke a specific SSO session."""
    session = db.query(SSOSession).filter(
        SSOSession.id == session_id,
        SSOSession.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()

    log_audit_event(db, user, "sso_session_revoke", "sso_session", session_id)
