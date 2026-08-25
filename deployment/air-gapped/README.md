# Quantive — Air-Gapped Deployment Guide

## Overview

Many government debt management offices, central banks, and sovereign
wealth funds **cannot connect to the internet**. This guide covers
how to deploy Quantive in a fully isolated (air-gapped) environment.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   AIR-GAPPED NETWORK                     │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Frontend │  │ Backend  │  │ Database │              │
│  │ (React)  │──│ (FastAPI)│──│(Postgres)│              │
│  └──────────┘  └────┬─────┘  └──────────┘              │
│                     │                                    │
│              ┌──────┴──────┐                             │
│              │  Market Data │                            │
│              │  (Local Cache)│                           │
│              └─────────────┘                             │
│                                                          │
│  ┌──────────────────────────────────────────┐           │
│  │  USB/Data Diode Import Station            │           │
│  │  (External → Air-Gapped one-way transfer) │           │
│  └──────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘

External Network (Market Data)
        │
        ▼ (USB / Data Diode — ONE WAY)
┌───────────────────────┐
│  Import Station        │
│  - Market data updates │
│  - Sanctions list sync │
│  - Software updates    │
└───────────────────────┘
```

## Requirements

### Hardware
- 2 servers (primary + backup): 16 CPU, 64GB RAM, 1TB SSD
- 1 import station (laptop/desktop with USB ports)
- Network switch (isolated, no uplink)
- UPS / battery backup

### Software
- Ubuntu 22.04 LTS (or RHEL 8/9)
- Docker + Docker Compose
- PostgreSQL 15+
- Python 3.11+
- Node.js 18+

## Deployment Steps

### 1. Build on Connected Machine

```bash
# On a machine with internet access
git clone https://github.com/quantive/quantive-platform.git
cd quantive-platform

# Build backend Docker image
docker build -t quantive-backend:latest -f deployment/Dockerfile.backend .

# Build frontend Docker image
cd frontend && npm run build && cd ..
docker build -t quantive-frontend:latest -f deployment/Dockerfile.frontend .

# Export images
docker save quantive-backend:latest quantive-frontend:latest -o quantive-images.tar

# Copy entire deployment directory to USB
cp -r deployment/ /media/usb/quantive/
cp quantive-images.tar /media/usb/quantive/
```

### 2. Import to Air-Gapped Network

```bash
# On import station (has USB access)
# Copy USB contents to air-gapped server
scp -r /media/usb/quantive/ user@airgap-server:/opt/quantive/
```

### 3. Deploy on Air-Gapped Server

```bash
# Load Docker images
docker load -i /opt/quantive/quantive-images.tar

# Start services
cd /opt/quantive
docker-compose -f docker-compose.airgapped.yml up -d

# Initialize database
docker exec quantive-backend alembic upgrade head

# Create admin user
docker exec quantive-backend python -c "
from app.database import SessionLocal
from app.models import User
from app.security import hash_password
db = SessionLocal()
user = User(
    email='admin@quantive.local',
    hashed_password=hash_password('ChangeMeImmediately!'),
    name='Admin',
    role='admin',
    is_active=True,
    org_id='default',
)
db.add(user)
db.commit()
print('Admin user created')
"
```

### 4. Configure Market Data

Since there's no internet, market data must be imported via USB:

```bash
# On connected machine: export latest market data
python scripts/export_market_data.py --output /media/usb/market_data/

# On air-gapped server: import market data
python scripts/import_market_data.py --input /opt/quantive/market_data/
```

Market data files:
- `yield_curves.json` — Treasury yields, SOFR, ECB rates
- `fx_rates.json` — Major currency pairs
- `economic_indicators.json` — GDP, CPI, fiscal data
- `sanctions_lists.json` — OFAC SDN, EU, UN lists

### 5. Sanctions List Updates

Sanctions lists must be updated regularly (at least monthly):

```bash
# On connected machine
python scripts/update_sanctions.py --output /media/usb/sanctions/

# On air-gapped server
python scripts/import_sanctions.py --input /opt/quantive/sanctions/
```

## Disaster Recovery

### Backup Strategy

```bash
# Daily automated backup (runs via cron)
#!/bin/bash
# /opt/quantive/scripts/backup.sh

BACKUP_DIR="/opt/quantive/backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Database backup
docker exec quantive-postgres pg_dump -U quantive quantive > "$BACKUP_DIR/database.sql"

# Audit trail backup (hash chain)
docker exec quantive-backend python scripts/export_audit_trail.py > "$BACKUP_DIR/audit_trail.json"

# Configuration backup
cp /opt/quantive/docker-compose.airgapped.yml "$BACKUP_DIR/"
cp /opt/quantive/.env "$BACKUP_DIR/"

# Retain last 30 days
find /opt/quantive/backups/ -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR"
```

### Recovery Procedures

#### Database Corruption
```bash
# Stop services
docker-compose -f docker-compose.airgapped.yml down

# Restore database
docker exec -i quantive-postgres psql -U quantive quantive < /opt/quantive/backups/LATEST/database.sql

# Verify audit trail integrity
docker exec quantive-backend python scripts/verify_audit_chain.py

# Restart services
docker-compose -f docker-compose.airgapped.yml up -d
```

#### Complete Server Failure
```bash
# 1. Install Ubuntu on new server
# 2. Install Docker + Docker Compose
# 3. Copy backup USB to new server
# 4. Load Docker images
docker load -i /opt/quantive/quantive-images.tar

# 5. Restore database
docker-compose -f docker-compose.airgapped.yml up -d postgres
docker exec -i quantive-postgres psql -U quantive quantive < /opt/quantive/backups/LATEST/database.sql

# 6. Start all services
docker-compose -f docker-compose.airgapped.yml up -d

# 7. Verify audit trail
docker exec quantive-backend python scripts/verify_audit_chain.py
```

## Security Considerations

### Network Isolation
- No network interfaces connected to external networks
- No WiFi, Bluetooth, or cellular modems
- USB ports restricted to import station only
- Network monitoring for unauthorized connections

### Data Diode (Recommended)
For highest security, use a hardware data diode instead of USB:
- One-way transfer only (external → air-gapped)
- No return path for data exfiltration
- Hardware-enforced, not software-controlled

### Audit Trail Verification
The immutable audit trail uses SHA-256 hash chains:
```bash
# Verify chain integrity
docker exec quantive-backend python -c "
from app.immutable_audit import get_audit_trail
trail = get_audit_trail()
is_valid, broken_at = trail.verify()
print(f'Chain valid: {is_valid}, broken at: {broken_at}')
"
```

### Encryption at Rest
```bash
# Enable LUKS disk encryption during Ubuntu installation
# All data on the encrypted volume is automatically protected
```

## Software Updates

Updates must follow the same USB import process:

1. Build new Docker images on connected machine
2. Export to USB: `docker save quantive-backend:latest -o quantive-update.tar`
3. Import to air-gapped server
4. Load and restart: `docker load -i quantive-update.tar && docker-compose up -d`

### Update Verification
```bash
# Verify image checksum before loading
sha256sum quantive-update.tar
# Compare with published checksum on quantive.com/updates
```

## Compliance Documentation

### SOC 2 Type II
- Immutable audit trail with hash chain verification
- Access controls via RBAC and MFA
- Encryption at rest and in transit (within air-gapped network)
- Regular backup and disaster recovery testing

### ISO 27001
- Information security management system (ISMS) documentation
- Risk assessment and treatment records
- Incident response procedures
- Business continuity plan

### IMF/World Bank
- Debt Sustainability Analysis (DSA) report generation
- Medium-Term Debt Strategy (MTDS) reporting
- Government Finance Statistics (GFS) data export
- Data sovereignty compliance (all data stays on-premise)

## Support

For air-gapped deployment support:
- Email: support@quantive.com
- Encrypted communication: PGP key available on website
- Emergency: +1-800-QUANTIVE (encrypted line available)
