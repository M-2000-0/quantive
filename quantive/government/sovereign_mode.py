"""Zero Trust Sovereign Mode deployment configuration.

Build a deployment option that runs entirely within a government's
existing infrastructure — no data leaves their network, no cloud dependency.
Marketed as "Zero Trust Sovereign Mode" and made the default, not premium.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DeploymentMode(str, Enum):
    """Available deployment modes."""
    SAAS_MANAGED = "saas_managed"           # Quantive-hosted
    PRIVATE_CLOUD = "private_cloud"         # Dedicated in customer cloud
    ON_PREMISE = "on_premise"               # Customer datacenter
    AIR_GAPPED = "air_gapped"              # Fully isolated
    SOVEREIGN = "sovereign"                 # Zero Trust Sovereign Mode


class SecurityLevel(str, Enum):
    """Security clearance levels."""
    STANDARD = "standard"
    ELEVATED = "elevated"
    CLASSIFIED = "classified"
    TOP_SECRET = "top_secret"


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""
    ISO_27001 = "iso_27001"
    SOC2_TYPE2 = "soc2_type2"
    NIST_800_53 = "nist_800_53"
    FedRAMP = "fedramp"
    BSI_C5 = "bsi_c5"
    GDPR = "gdpr"
    LOCAL_REGULATIONS = "local_regulations"


@dataclass
class NetworkConfig:
    """Network isolation configuration."""
    vlan_id: int | None = None
    subnet_cidr: str | None = None
    firewall_rules: list[dict] = field(default_factory=list)
    dns_servers: list[str] = field(default_factory=list)
    proxy_config: dict | None = None
    mtls_enabled: bool = True
    certificate_authority: str | None = None
    internal_only: bool = True


@dataclass
class EncryptionConfig:
    """Encryption configuration for sovereign mode."""
    at_rest: str = "AES-256-GCM"
    in_transit: str = "TLS 1.3"
    key_management: str = "customer_managed_hsm"
    fips_140_2_level: int = 3
    quantum_resistant: bool = True
    key_rotation_days: int = 90
    backup_encryption: bool = True


@dataclass
class AccessControl:
    """Zero trust access control configuration."""
    mfa_required: bool = True
    hardware_keys: bool = True
    ip_whitelist: list[str] = field(default_factory=list)
    vpn_required: bool = True
    session_timeout_minutes: int = 30
    max_concurrent_sessions: int = 3
    role_based_access: bool = True
    separation_of_duties: bool = True
    audit_all_access: bool = True


@dataclass
class DataResidency:
    """Data residency and sovereignty configuration."""
    primary_region: str = "customer_datacenter"
    backup_regions: list[str] = field(default_factory=list)
    cross_border_transfer: bool = False
    data_classification: str = "sovereign"
    retention_years: int = 25
    immutable_storage: bool = True
    geographic_redundancy: bool = True


@dataclass
class AuditConfig:
    """Immutable audit configuration."""
    immutable_logs: bool = True
    hash_chain_verification: bool = True
    external_audit_integration: bool = True
    tamper_evidence: bool = True
    retention_years: int = 25
    real_time_monitoring: bool = True
    anomaly_detection: bool = True


@dataclass
class SovereignModeConfig:
    """Complete Zero Trust Sovereign Mode configuration."""
    deployment_mode: DeploymentMode = DeploymentMode.SOVEREIGN
    security_level: SecurityLevel = SecurityLevel.CLASSIFIED
    network: NetworkConfig = field(default_factory=NetworkConfig)
    encryption: EncryptionConfig = field(default_factory=EncryptionConfig)
    access_control: AccessControl = field(default_factory=AccessControl)
    data_residency: DataResidency = field(default_factory=DataResidency)
    audit: AuditConfig = field(default_factory=AuditConfig)
    compliance_frameworks: list[ComplianceFramework] = field(default_factory=list)

    # Additional sovereign features
    air_gap_capable: bool = True
    offline_mode: bool = True
    local_ai_processing: bool = True
    no_external_dependencies: bool = True
    source_code_escrow: bool = True
    perpetual_license: bool = True


class SovereignModeEngine:
    """Manages Zero Trust Sovereign Mode deployments."""

    def __init__(self):
        self._deployments: dict[str, SovereignModeConfig] = {}

    def create_default_config(self) -> SovereignModeConfig:
        """Create default Zero Trust Sovereign Mode configuration."""
        return SovereignModeConfig(
            deployment_mode=DeploymentMode.SOVEREIGN,
            security_level=SecurityLevel.CLASSIFIED,
            network=NetworkConfig(
                internal_only=True,
                mtls_enabled=True,
                vpn_required=True,
                firewall_rules=[
                    {"port": 443, "protocol": "tcp", "source": "internal", "action": "allow"},
                    {"port": 5432, "protocol": "tcp", "source": "internal", "action": "allow"},
                    {"port": 6379, "protocol": "tcp", "source": "internal", "action": "allow"},
                    {"port": "*", "protocol": "*", "source": "external", "action": "deny"},
                ],
            ),
            encryption=EncryptionConfig(
                at_rest="AES-256-GCM",
                in_transit="TLS 1.3",
                key_management="customer_managed_hsm",
                fips_140_2_level=3,
                quantum_resistant=True,
                key_rotation_days=90,
            ),
            access_control=AccessControl(
                mfa_required=True,
                hardware_keys=True,
                vpn_required=True,
                session_timeout_minutes=30,
                separation_of_duties=True,
                audit_all_access=True,
            ),
            data_residency=DataResidency(
                primary_region="customer_datacenter",
                cross_border_transfer=False,
                data_classification="sovereign",
                retention_years=25,
                immutable_storage=True,
            ),
            audit=AuditConfig(
                immutable_logs=True,
                hash_chain_verification=True,
                tamper_evidence=True,
                retention_years=25,
                real_time_monitoring=True,
                anomaly_detection=True,
            ),
            compliance_frameworks=[
                ComplianceFramework.ISO_27001,
                ComplianceFramework.NIST_800_53,
                ComplianceFramework.BSI_C5,
            ],
            air_gap_capable=True,
            offline_mode=True,
            local_ai_processing=True,
            no_external_dependencies=True,
            source_code_escrow=True,
            perpetual_license=True,
        )

    def generate_docker_compose(self, config: SovereignModeConfig) -> dict:
        """Generate Docker Compose configuration for sovereign deployment."""
        services = {
            "quantive-api": {
                "image": "quantive/api:latest",
                "environment": {
                    "DEPLOYMENT_MODE": "sovereign",
                    "SECURITY_LEVEL": config.security_level.value,
                    "FIPS_140_2": "true",
                    "QUANTUM_RESISTANT": str(config.encryption.quantum_resistant).lower(),
                },
                "volumes": [
                    "quantive_data:/app/data",
                    "audit_logs:/app/audit",
                    "hsm_socket:/app/hsm",
                ],
                "networks": ["internal"],
                "deploy": {
                    "replicas": 3,
                    "restart_policy": {"condition": "on-failure"},
                },
            },
            "quantive-worker": {
                "image": "quantive/worker:latest",
                "environment": {
                    "DEPLOYMENT_MODE": "sovereign",
                    "LOCAL_AI_PROCESSING": "true",
                },
                "volumes": [
                    "quantive_data:/app/data",
                    "models_data:/app/models",
                ],
                "networks": ["internal"],
            },
            "postgres": {
                "image": "postgres:16-alpine",
                "environment": {
                    "POSTGRES_PASSWORD_FILE": "/run/secrets/db_password",
                    "POSTGRES_INITDB_ARGS": "--data-checksums",
                },
                "volumes": [
                    "pg_data:/var/lib/postgresql/data",
                    "./init.sql:/docker-entrypoint-initdb.d/init.sql",
                ],
                "networks": ["internal"],
                "command": [
                    "postgres",
                    "-c", "ssl=on",
                    "-c", "ssl_cert_file=/certs/server.crt",
                    "-c", "ssl_key_file=/certs/server.key",
                    "-c", "ssl_ca_file=/certs/ca.crt",
                    "-c", "log_statement=all",
                    "-c", "log_connections=on",
                    "-c", "log_disconnections=on",
                ],
            },
            "redis": {
                "image": "redis:7-alpine",
                "command": [
                    "redis-server",
                    "--requirepass", "${REDIS_PASSWORD}",
                    "--tls-port", "6380",
                    "--port", "0",
                    "--tls-cert-file", "/certs/redis.crt",
                    "--tls-key-file", "/certs/redis.key",
                    "--tls-ca-cert-file", "/certs/ca.crt",
                ],
                "networks": ["internal"],
            },
            "nginx": {
                "image": "nginx:alpine",
                "ports": ["443:443"],
                "volumes": [
                    "./nginx.conf:/etc/nginx/nginx.conf",
                    "/certs:/certs:ro",
                ],
                "networks": ["internal"],
            },
        }

        return {
            "version": "3.8",
            "services": services,
            "networks": {
                "internal": {
                    "driver": "bridge",
                    "internal": True,
                },
            },
            "volumes": {
                "quantive_data": {"driver": "local"},
                "audit_logs": {"driver": "local"},
                "hsm_socket": {"driver": "local"},
                "pg_data": {"driver": "local"},
                "models_data": {"driver": "local"},
            },
        }

    def generate_security_checklist(self, config: SovereignModeConfig) -> list[dict]:
        """Generate security checklist for sovereign deployment."""
        checklist = [
            {
                "category": "Network Security",
                "items": [
                    {"item": "Network segmentation configured", "status": "required"},
                    {"item": "Firewall rules implemented", "status": "required"},
                    {"item": "mTLS enabled for all services", "status": "required"},
                    {"item": "VPN access configured", "status": "required"},
                    {"item": "External access blocked", "status": "required"},
                ],
            },
            {
                "category": "Encryption",
                "items": [
                    {"item": "AES-256 encryption at rest", "status": "required"},
                    {"item": "TLS 1.3 in transit", "status": "required"},
                    {"item": "HSM integration verified", "status": "required"},
                    {"item": "FIPS 140-2 Level 3 certified", "status": "required"},
                    {"item": "Quantum-resistant algorithms enabled", "status": "recommended"},
                ],
            },
            {
                "category": "Access Control",
                "items": [
                    {"item": "MFA with hardware keys", "status": "required"},
                    {"item": "Role-based access control", "status": "required"},
                    {"item": "Separation of duties enforced", "status": "required"},
                    {"item": "Session timeout configured", "status": "required"},
                    {"item": "IP whitelist implemented", "status": "recommended"},
                ],
            },
            {
                "category": "Data Residency",
                "items": [
                    {"item": "Data within sovereign borders", "status": "required"},
                    {"item": "No cross-border transfer", "status": "required"},
                    {"item": "Immutable storage enabled", "status": "required"},
                    {"item": "Geographic redundancy", "status": "required"},
                    {"item": "Backup encryption verified", "status": "required"},
                ],
            },
            {
                "category": "Audit & Compliance",
                "items": [
                    {"item": "Immutable audit logs", "status": "required"},
                    {"item": "Hash chain verification", "status": "required"},
                    {"item": "Tamper evidence enabled", "status": "required"},
                    {"item": "Real-time monitoring", "status": "required"},
                    {"item": "Anomaly detection active", "status": "recommended"},
                ],
            },
        ]
        return checklist

    def generate_deployment_guide(self, config: SovereignModeConfig) -> dict:
        """Generate comprehensive deployment guide."""
        return {
            "title": "Quantive Zero Trust Sovereign Mode Deployment Guide",
            "version": "1.0",
            "classification": "CONFIDENTIAL",
            "sections": [
                {
                    "title": "Prerequisites",
                    "items": [
                        "Kubernetes cluster (v1.28+) or Docker Swarm",
                        "PostgreSQL 16+ with SSL configured",
                        "Redis 7+ with TLS",
                        "HSM (FIPS 140-2 Level 3)",
                        "Internal Certificate Authority",
                        "VPN infrastructure",
                        "Monitoring stack (Prometheus/Grafana)",
                    ],
                },
                {
                    "title": "Installation",
                    "steps": [
                        "1. Provision infrastructure in sovereign datacenter",
                        "2. Configure network segmentation and firewall rules",
                        "3. Deploy Certificate Authority and issue certificates",
                        "4. Initialize HSM and generate encryption keys",
                        "5. Deploy database cluster with replication",
                        "6. Deploy Quantive API and worker services",
                        "7. Configure monitoring and alerting",
                        "8. Run security validation tests",
                        "9. Conduct penetration testing",
                        "10. Obtain compliance certification",
                    ],
                },
                {
                    "title": "Security Validation",
                    "tests": [
                        "Network isolation verification",
                        "Encryption at rest validation",
                        "mTLS certificate verification",
                        "Access control testing",
                        "Audit log integrity check",
                        "Data residency verification",
                        "Penetration testing",
                        "Compliance audit",
                    ],
                },
                {
                    "title": "Operational Procedures",
                    "procedures": [
                        "Key rotation (quarterly)",
                        "Certificate renewal (annual)",
                        "Security patching (within 7 days)",
                        "Backup verification (monthly)",
                        "DR testing (quarterly)",
                        "Compliance audit (annual)",
                        "Penetration testing (annual)",
                    ],
                },
            ],
            "support": {
                "escalation_path": "Critical → 15 min response",
                "dedicated_support": "24/7 for sovereign deployments",
                "on_site_support": "Available for critical incidents",
            },
        }

    def register_deployment(
        self,
        country_code: str,
        config: SovereignModeConfig,
    ) -> dict:
        """Register a sovereign deployment."""
        self._deployments[country_code] = config
        return {
            "country_code": country_code,
            "deployment_mode": config.deployment_mode.value,
            "security_level": config.security_level.value,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending_deployment",
        }

    def get_deployment_status(self, country_code: str) -> dict:
        """Get deployment status for a country."""
        config = self._deployments.get(country_code)
        if not config:
            return {"error": "Deployment not found"}

        return {
            "country_code": country_code,
            "deployment_mode": config.deployment_mode.value,
            "security_level": config.security_level.value,
            "compliance_frameworks": [f.value for f in config.compliance_frameworks],
            "features": {
                "air_gap_capable": config.air_gap_capable,
                "offline_mode": config.offline_mode,
                "local_ai_processing": config.local_ai_processing,
                "source_code_escrow": config.source_code_escrow,
                "perpetual_license": config.perpetual_license,
            },
            "security_checklist": self.generate_security_checklist(config),
        }
