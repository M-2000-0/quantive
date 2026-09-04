# Quantive — Service Level Agreement & Data Residency

## Service Level Agreement (SLA)

### Uptime Commitment

| Metric | Target | Measurement |
|--------|--------|-------------|
| Monthly Uptime | ≥ 99.95% | Measured as (Total Minutes - Downtime Minutes) / Total Minutes |
| Planned Maintenance | ≤ 4 hours/month | Sunday 02:00-06:00 UTC only |
| Unplanned Downtime | ≤ 22 minutes/month | Rolling 30-day average |
| Recovery Time Objective (RTO) | ≤ 4 hours | Time to restore service after incident |
| Recovery Point Objective (RPO) | ≤ 15 minutes | Maximum data loss in incident |

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time (P50) | ≤ 200ms | Measured at load balancer |
| API Response Time (P95) | ≤ 500ms | Measured at load balancer |
| API Response Time (P99) | ≤ 1000ms | Measured at load balancer |
| Optimization Job (1000 instruments) | ≤ 120 seconds | End-to-end including solver |
| Market Data Freshness | ≤ 5 minutes | Time since last successful fetch |
| Concurrent Users | ≥ 100 | Without degradation |

### Incident Response

| Severity | Response Time | Update Frequency | Resolution Target |
|----------|--------------|-----------------|-------------------|
| Critical (service down) | 15 minutes | Every 30 minutes | 4 hours |
| High (major feature broken) | 1 hour | Every 2 hours | 8 hours |
| Medium (minor feature broken) | 4 hours | Daily | 48 hours |
| Low (cosmetic/ Enhancement) | 24 hours | Weekly | Next release |

### SLA Breach Penalties

| Uptime Achieved | Service Credit |
|-----------------|----------------|
| 99.95% - 99.99% | 0% (meeting target) |
| 99.90% - 99.94% | 10% monthly credit |
| 99.50% - 99.89% | 25% monthly credit |
| 99.00% - 99.49% | 50% monthly credit |
| Below 99.00% | 100% monthly credit + termination right |

### Exclusions

SLA does not apply to:
- Scheduled maintenance windows (communicated 48h in advance)
- Force majeure events (natural disasters, war, government action)
- Customer-caused outages (misconfiguration, unauthorized changes)
- Third-party service failures (upstream data providers)

---

## Data Residency Controls

### Supported Deployment Regions

| Region | Location | Provider | Encryption | Compliance |
|--------|----------|----------|------------|------------|
| US-East | Virginia, USA | AWS GovCloud | AES-256-GCM | FedRAMP High |
| US-West | Oregon, USA | AWS GovCloud | AES-256-GCM | FedRAMP High |
| EU-West | Frankfurt, Germany | Azure Government | AES-256-GCM | GDPR, BSI C5 |
| EU-Central | Amsterdam, Netherlands | Azure Government | AES-256-GCM | GDPR, BSI C5 |
| AP-Southeast | Singapore | AWS | AES-256-GCM | PDPA |
| AP-Northeast | Tokyo, Japan | AWS | AES-256-GCM | APPI |
| ME-South | Bahrain | AWS | AES-256-GCM | Local regulations |
| AF-South | Cape Town, South Africa | AWS | AES-256-GCM | POPIA |
| SA-East | São Paulo, Brazil | AWS | AES-256-GCM | LGPD |
| Sovereign | Customer datacenter | Self-hosted | Customer-managed | Customer-controlled |

### Encryption Standards

| Layer | Standard | Key Management |
|-------|----------|----------------|
| Data at Rest | AES-256-GCM | AWS KMS / Azure Key Vault / HSM |
| Data in Transit | TLS 1.3 | Certificate management |
| Database | Transparent Data Encryption (TDE) | Customer-managed keys |
| Backups | AES-256 | Separate key from database |
| Audit Logs | SHA-256 hash chain | Immutable storage |

### Data Sovereignty Guarantees

1. **No Cross-Border Transfer**: Data never leaves the selected region unless explicitly configured
2. **In-Country Processing**: All computation occurs within the deployment region
3. **Local Encryption Keys**: Customers can manage their own encryption keys (BYOK)
4. **Audit Trail**: All data access logged with user, timestamp, and IP address
5. **Export Controls**: Configurable restrictions on data export (size, format, destination)

### Deployment Options

| Option | Description | Data Control | Compliance |
|--------|-------------|-------------|------------|
| SaaS (Managed) | Quantive-hosted in selected region | Full | ISO 27001, SOC 2 |
| Private Cloud | Dedicated infrastructure in customer cloud | Full | FedRAMP, BSI C5 |
| On-Premise | Customer datacenter deployment | Complete | Air-gapped capable |
| Hybrid | Split deployment (sensitive data on-prem) | Complete | Flexible |

### Data Retention

| Data Type | Default Retention | Configurable | Archival |
|-----------|------------------|-------------|----------|
| Portfolio Data | Until deleted by customer | Yes | After 1 year |
| Optimization Results | 5 years | Yes | Compressed archive |
| Audit Logs | 25 years | Yes (minimum 7) | Immutable archive |
| User Activity | 2 years | Yes | Anonymized after 90 days |
| Market Data Cache | 30 days | Yes | Purged |

### Backup and Recovery

| Metric | Target | Frequency |
|--------|--------|-----------|
| Full Backup | Daily | 02:00 UTC |
| Incremental Backup | Every 15 minutes | Continuous |
| Backup Retention | 90 days | Rolling |
| Geographic Redundancy | 3 regions | Automatic |
| Backup Encryption | AES-256 | Customer-managed keys |
| Recovery Testing | Monthly | Documented |

### Compliance Certifications

| Standard | Status | Scope |
|----------|--------|-------|
| ISO 27001 | In Progress | Information Security Management |
| SOC 2 Type II | Planned Q1 2027 | Security, Availability, Confidentiality |
| FedRAMP Moderate | Planned Q2 2027 | US Government Cloud |
| BSI C5 | Planned Q3 2027 | German Cloud Security |
| GDPR | Compliant | EU Data Protection |
| NIST 800-53 | Control mapping documented | US Government Security |

### Incident Data Handling

During a security incident:
1. Affected data scope identified within 1 hour
2. Customer notification within 24 hours (per GDPR)
3. Forensic evidence preserved in immutable storage
4. Remediation plan provided within 72 hours
5. Post-incident report within 30 days
