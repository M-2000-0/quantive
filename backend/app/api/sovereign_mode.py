"""Zero Trust Sovereign Mode API endpoints.

Exposes deployment configuration, security checklist, and deployment guide
for government sovereign deployments.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/sovereign-mode", tags=["sovereign-mode"])


# ── Request Models ─────────────────────────────────────────────────

class DeploymentRequest(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=3)
    country_name: str = Field(..., min_length=2, max_length=255)
    security_level: str = Field(default="classified")
    compliance_frameworks: list[str] = Field(default=["iso_27001", "nist_800_53"])
    network_config: dict | None = Field(default=None)
    encryption_config: dict | None = Field(default=None)


# ── API Endpoints ──────────────────────────────────────────────────

@router.get("/default-config")
def get_default_config(
    user: User = Depends(get_current_user),
):
    """Get default Zero Trust Sovereign Mode configuration."""
    from quantive.government.sovereign_mode import SovereignModeEngine

    engine = SovereignModeEngine()
    config = engine.create_default_config()

    return {
        "deployment_mode": config.deployment_mode.value,
        "security_level": config.security_level.value,
        "network": {
            "internal_only": config.network.internal_only,
            "mtls_enabled": config.network.mtls_enabled,
            "vpn_required": config.network.vpn_required,
            "firewall_rules": config.network.firewall_rules,
        },
        "encryption": {
            "at_rest": config.encryption.at_rest,
            "in_transit": config.encryption.in_transit,
            "key_management": config.encryption.key_management,
            "fips_140_2_level": config.encryption.fips_140_2_level,
            "quantum_resistant": config.encryption.quantum_resistant,
        },
        "access_control": {
            "mfa_required": config.access_control.mfa_required,
            "hardware_keys": config.access_control.hardware_keys,
            "separation_of_duties": config.access_control.separation_of_duties,
        },
        "data_residency": {
            "primary_region": config.data_residency.primary_region,
            "cross_border_transfer": config.data_residency.cross_border_transfer,
            "data_classification": config.data_residency.data_classification,
        },
        "features": {
            "air_gap_capable": config.air_gap_capable,
            "offline_mode": config.offline_mode,
            "local_ai_processing": config.local_ai_processing,
            "no_external_dependencies": config.no_external_dependencies,
            "source_code_escrow": config.source_code_escrow,
            "perpetual_license": config.perpetual_license,
        },
    }


@router.post("/docker-compose")
def generate_docker_compose(
    request: DeploymentRequest,
    user: User = Depends(get_current_user),
):
    """Generate Docker Compose configuration for sovereign deployment."""
    from quantive.government.sovereign_mode import (
        ComplianceFramework,
        SecurityLevel,
        SovereignModeEngine,
    )

    engine = SovereignModeEngine()
    config = engine.create_default_config()

    # Apply custom security level
    level_map = {
        "standard": SecurityLevel.STANDARD,
        "elevated": SecurityLevel.ELEVATED,
        "classified": SecurityLevel.CLASSIFIED,
        "top_secret": SecurityLevel.TOP_SECRET,
    }
    config.security_level = level_map.get(request.security_level, SecurityLevel.CLASSIFIED)

    # Apply compliance frameworks
    framework_map = {
        "iso_27001": ComplianceFramework.ISO_27001,
        "soc2_type2": ComplianceFramework.SOC2_TYPE2,
        "nist_800_53": ComplianceFramework.NIST_800_53,
        "fedramp": ComplianceFramework.FedRAMP,
        "bsi_c5": ComplianceFramework.BSI_C5,
        "gdpr": ComplianceFramework.GDPR,
    }
    config.compliance_frameworks = [
        framework_map.get(f, ComplianceFramework.ISO_27001)
        for f in request.compliance_frameworks
    ]

    docker_compose = engine.generate_docker_compose(config)

    return {
        "country_code": request.country_code,
        "country_name": request.country_name,
        "docker_compose": docker_compose,
        "instructions": [
            "1. Review and customize docker-compose.yml",
            "2. Generate TLS certificates for all services",
            "3. Configure HSM integration",
            "4. Set up network segmentation",
            "5. Deploy using: docker stack deploy -c docker-compose.yml quantive",
            "6. Run security validation tests",
            "7. Conduct penetration testing",
        ],
    }


@router.get("/security-checklist")
def get_security_checklist(
    user: User = Depends(get_current_user),
):
    """Get security checklist for sovereign deployment."""
    from quantive.government.sovereign_mode import SovereignModeEngine

    engine = SovereignModeEngine()
    config = engine.create_default_config()
    checklist = engine.generate_security_checklist(config)

    return {
        "checklist": checklist,
        "total_items": sum(len(cat["items"]) for cat in checklist),
        "required_items": sum(
            1 for cat in checklist for item in cat["items"] if item["status"] == "required"
        ),
    }


@router.get("/deployment-guide")
def get_deployment_guide(
    user: User = Depends(get_current_user),
):
    """Get comprehensive deployment guide."""
    from quantive.government.sovereign_mode import SovereignModeEngine

    engine = SovereignModeEngine()
    config = engine.create_default_config()
    guide = engine.generate_deployment_guide(config)

    return guide


@router.post("/register")
def register_deployment(
    request: DeploymentRequest,
    user: User = Depends(get_current_user),
):
    """Register a new sovereign deployment."""
    from quantive.government.sovereign_mode import SovereignModeEngine

    engine = SovereignModeEngine()
    config = engine.create_default_config()

    result = engine.register_deployment(
        country_code=request.country_code,
        config=config,
    )

    return result


@router.get("/status/{country_code}")
def get_deployment_status(
    country_code: str,
    user: User = Depends(get_current_user),
):
    """Get deployment status for a country."""
    from quantive.government.sovereign_mode import SovereignModeEngine

    engine = SovereignModeEngine()
    status = engine.get_deployment_status(country_code.upper())

    if "error" in status:
        raise HTTPException(404, status["error"])

    return status


@router.get("/comparison")
def compare_deployment_modes():
    """Compare different deployment modes."""
    return {
        "modes": [
            {
                "name": "SaaS (Managed)",
                "mode": "saas_managed",
                "data_control": "Full",
                "compliance": "ISO 27001, SOC 2",
                "best_for": "Small to medium deployments",
                "cost": "Lowest upfront",
            },
            {
                "name": "Private Cloud",
                "mode": "private_cloud",
                "data_control": "Full",
                "compliance": "FedRAMP, BSI C5",
                "best_for": "Government agencies with cloud mandate",
                "cost": "Medium",
            },
            {
                "name": "On-Premise",
                "mode": "on_premise",
                "data_control": "Complete",
                "compliance": "Custom",
                "best_for": "Large sovereign deployments",
                "cost": "Higher upfront",
            },
            {
                "name": "Air-Gapped",
                "mode": "air_gapped",
                "data_control": "Complete",
                "compliance": "Air-gapped capable",
                "best_for": "Classified environments",
                "cost": "Highest",
            },
            {
                "name": "Zero Trust Sovereign",
                "mode": "sovereign",
                "data_control": "Complete",
                "compliance": "All frameworks",
                "best_for": "Sovereign debt management",
                "cost": "Premium",
                "features": [
                    "Air-gap capable",
                    "Offline mode",
                    "Local AI processing",
                    "Source code escrow",
                    "Perpetual license",
                    "FIPS 140-2 Level 3",
                    "Quantum-resistant encryption",
                ],
            },
        ],
        "recommendation": "sovereign",
    }
