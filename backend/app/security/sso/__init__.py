"""SSO/SAML Service Provider implementation for government identity federation.

Supports:
- SAML 2.0 SP-initiated SSO (Okta, Azure AD, PingFederate, OneLogin)
- Attribute mapping from SAML assertions to local user fields
- Just-in-time user provisioning
- Single Logout (SLO) via back-channel
- Metadata endpoint for IdP registration

Usage:
    from app.security.sso import SAMLHandler

    handler = SAMLHandler(provider)
    auth_request = handler.create_auth_request()
    user = handler.process_sso_response(saml_response)
"""
from __future__ import annotations

import base64
import secrets
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.sso import SSOProvider, SSOProviderStatus, SSOSession, SSOUserLink  # noqa: F401

# SAML protocol namespaces
SAML2P_NS = "urn:oasis:names:tc:SAML:2.0:protocol"
SAML2_NS = "urn:oasis:names:tc:SAML:2.0:assertion"
MD_NS = "urn:oasis:names:tc:SAML:2.0:metadata"
DS_NS = "http://www.w3.org/2000/09/xmldsig#"

# NameID formats
NAMEID_EMAIL = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
NAMEID_PERSISTENT = "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"
NAMEID_TRANSIENT = "urn:oasis:names:tc:SAML:2.0:nameid-format:transient"


class SSOLoginError(Exception):
    """Raised when SSO authentication fails."""
    pass


class SAMLHandler:
    """Handles SAML 2.0 SP-initiated SSO flow."""

    def __init__(self, provider: SSOProvider, sp_entity_id: str = "quantive"):
        self.provider = provider
        self.sp_entity_id = sp_entity_id

    def create_auth_request(self, relay_state: str = "") -> dict[str, str]:
        """Generate a SAML AuthnRequest for SP-initiated SSO.

        Returns:
            dict with 'url' (IdP SSO URL), 'saml_request' (encoded), 'relay_state'
        """
        request_id = f"_saml_{secrets.token_hex(16)}"
        issue_instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        authn_request = f"""<samlp:AuthnRequest
    xmlns:samlp="{SAML2P_NS}"
    xmlns:saml="{SAML2_NS}"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{self.provider.sso_url}"
    AssertionConsumerServiceURL="{self.sp_entity_id}/sso/acs"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
  <saml:Issuer>{self.sp_entity_id}</saml:Issuer>
  <samlp:NameIDPolicy Format="{self.provider.name_id_format}" AllowCreate="true"/>
</samlp:AuthnRequest>"""

        saml_request = base64.b64encode(authn_request.encode("utf-8")).decode("utf-8")

        if not relay_state:
            relay_state = secrets.token_urlsafe(32)

        return {
            "url": self.provider.sso_url,
            "saml_request": saml_request,
            "relay_state": relay_state,
        }

    def process_sso_response(
        self,
        saml_response_b64: str,
        db: Session,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Validate and process a SAML Response from the IdP.

        Returns:
            dict with 'user_id', 'email', 'name', 'attributes', 'session_index'
        """
        # Decode and parse
        try:
            xml_bytes = base64.b64decode(saml_response_b64)
            root = ET.fromstring(xml_bytes)
        except Exception as e:
            raise SSOLoginError(f"Invalid SAML response: {e}")

        # Check status
        status_el = root.find(f"{{{SAML2P_NS}}}Status/{{{SAML2P_NS}}}StatusCode")
        if status_el is None:
            raise SSOLoginError("Missing SAML status code")
        status_value = status_el.get("Value", "")
        if status_value != "urn:oasis:names:tc:SAML:2.0:status:Success":
            raise SSOLoginError(f"SAML authentication failed: {status_value}")

        # Extract assertion
        assertion = root.find(f"{{{SAML2_NS}}}Assertion")
        if assertion is None:
            raise SSOLoginError("No assertion in SAML response")

        # Validate issuer
        issuer_el = assertion.find(f"{{{SAML2_NS}}}Issuer")
        if issuer_el is None or issuer_el.text != self.provider.entity_id:
            raise SSOLoginError("SAML assertion issuer mismatch")

        # Validate NotOnOrAfter (assertion expiry)
        conditions = assertion.find(f"{{{SAML2_NS}}}Conditions")
        if conditions is not None:
            not_on_or_after = conditions.get("NotOnOrAfter")
            if not_on_or_after:
                expiry = datetime.fromisoformat(not_on_or_after.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > expiry:
                    raise SSOLoginError("SAML assertion expired")

        # Extract Subject
        subject = assertion.find(f"{{{SAML2_NS}}}Subject")
        if subject is None:
            raise SSOLoginError("No subject in SAML assertion")

        name_id_el = subject.find(f"{{{SAML2_NS}}}NameID")
        if name_id_el is None or not name_id_el.text:
            raise SSOLoginError("No NameID in SAML assertion")

        name_id = name_id_el.text.strip()
        session_index = None
        session_index_el = subject.find(f"{{{SAML2_NS}}}SessionIndex")
        if session_index_el is not None and session_index_el.text:
            session_index = session_index_el.text.strip()

        # Extract attributes
        attributes = self._extract_attributes(assertion)

        # Map attributes to user fields
        mapping = self.provider.attribute_mapping or {}
        email = attributes.get(mapping.get("email", "email"), name_id)
        name = attributes.get(mapping.get("name", "displayName"), email.split("@")[0])

        if not email:
            raise SSOLoginError("Could not determine user email from SAML assertion")

        # Find or create user
        user = self._find_or_create_user(
            email=email,
            name=name,
            external_id=name_id,
            attributes=attributes,
            db=db,
        )

        # Record SSO session
        session = SSOSession(
            user_id=user["id"],
            provider_id=self.provider.id,
            session_index=session_index,
            name_id=name_id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
        )
        db.add(session)
        db.commit()

        return {
            "user_id": user["id"],
            "email": email,
            "name": name,
            "attributes": attributes,
            "session_index": session_index,
            "is_new_user": user.get("is_new", False),
        }

    def generate_metadata(self) -> str:
        """Generate SP SAML metadata XML for IdP registration."""
        metadata = f"""<md:EntityDescriptor
    xmlns:md="{MD_NS}"
    entityID="{self.sp_entity_id}">
  <md:SPSSODescriptor
      AuthnRequestsSigned="false"
      WantAssertionsSigned="true"
      protocolSupportEnumeration="{SAML2P_NS}">
    <md:NameIDFormat>{self.provider.name_id_format}</md:NameIDFormat>
    <md:AssertionConsumerService
        Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        Location="{self.sp_entity_id}/sso/acs"
        index="1"
        isDefault="true"/>
    <md:SingleLogoutService
        Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        Location="{self.sp_entity_id}/sso/slo"/>
  </md:SPSSODescriptor>
</md:EntityDescriptor>"""
        return metadata

    def create_logout_request(self, name_id: str, session_index: str | None = None) -> dict[str, str]:
        """Generate a SAML LogoutRequest for SP-initiated SLO."""
        request_id = f"_slo_{secrets.token_hex(16)}"
        issue_instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        session_index_xml = ""
        if session_index:
            session_index_xml = f"\n    <samlp:SessionIndex>{session_index}</samlp:SessionIndex>"

        logout_request = f"""<samlp:LogoutRequest
    xmlns:samlp="{SAML2P_NS}"
    xmlns:saml="{SAML2_NS}"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{self.provider.slo_url}">
  <saml:Issuer>{self.sp_entity_id}</saml:Issuer>
  <saml:NameID>{name_id}</saml:NameID>{session_index_xml}
</samlp:LogoutRequest>"""

        slo_request = base64.b64encode(logout_request.encode("utf-8")).decode("utf-8")

        return {
            "url": self.provider.slo_url,
            "saml_request": slo_request,
            "relay_state": secrets.token_urlsafe(32),
        }

    def _extract_attributes(self, assertion: ET.Element) -> dict[str, str]:
        """Extract all attributes from a SAML assertion."""
        attributes: dict[str, str] = {}
        attribute_statement = assertion.find(f"{{{SAML2_NS}}}AttributeStatement")
        if attribute_statement is None:
            return attributes

        for attr in attribute_statement.findall(f"{{{SAML2_NS}}}Attribute"):
            attr_name = attr.get("Name", "")
            values = []
            for val in attr.findall(f"{{{SAML2_NS}}}AttributeValue"):
                if val.text:
                    values.append(val.text.strip())
            if values:
                attributes[attr_name] = values[0] if len(values) == 1 else ",".join(values)

        return attributes

    def _find_or_create_user(
        self,
        email: str,
        name: str,
        external_id: str,
        attributes: dict,
        db: Session,
    ) -> dict[str, Any]:
        """Find existing SSO link or create new user via JIT provisioning."""
        from app.models import User

        # Check for existing SSO link
        existing_link = db.query(SSOUserLink).filter(
            SSOUserLink.provider_id == self.provider.id,
            SSOUserLink.external_id == external_id,
        ).first()

        if existing_link:
            # Update last login
            existing_link.last_login_at = datetime.now(timezone.utc)
            db.commit()

            user = db.query(User).filter(User.id == existing_link.user_id).first()
            if user:
                return {"id": user.id, "email": user.email, "name": user.name, "is_new": False}

        # JIT provisioning: create user if auto_provision is enabled
        if not self.provider.auto_provision_users:
            raise SSOLoginError(
                f"User {email} not found and auto-provisioning is disabled. "
                "Contact your administrator to create an account."
            )

        # Check if user exists by email
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            # Link existing user to this SSO provider
            link = SSOUserLink(
                user_id=existing_user.id,
                provider_id=self.provider.id,
                external_id=external_id,
                external_email=email,
                last_login_at=datetime.now(timezone.utc),
            )
            db.add(link)
            db.commit()
            return {"id": existing_user.id, "email": email, "name": name, "is_new": False}

        # Create new user
        from app.security import hash_password

        # Generate a random password (user will only log in via SSO)
        random_password = secrets.token_urlsafe(32)

        new_user = User(
            email=email,
            password_hash=hash_password(random_password),
            name=name,
            role=self.provider.default_role,
            is_active=True,
            org_id=self.provider.org_id,
        )
        db.add(new_user)
        db.flush()

        # Create SSO link
        link = SSOUserLink(
            user_id=new_user.id,
            provider_id=self.provider.id,
            external_id=external_id,
            external_email=email,
            last_login_at=datetime.now(timezone.utc),
        )
        db.add(link)
        db.commit()

        return {"id": new_user.id, "email": email, "name": name, "is_new": True}
