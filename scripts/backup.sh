#!/usr/bin/env bash
# Quantive Automated Backup Script
# Designed for air-gapped or on-premise deployments
#
# Usage:
#   chmod +x scripts/backup.sh
#   scripts/backup.sh                          # Run backup
#   scripts/backup.sh --retention 30           # Keep 30 days
#   scripts/backup.sh --output /mnt/usb/backups
#
# Cron example (daily at 2 AM):
#   0 2 * * * /path/to/quantive/scripts/backup.sh --output /mnt/backups >> /var/log/quantive-backup.log 2>&1

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_OUTPUT:-/var/backups/quantive}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DB_NAME="${POSTGRES_DB:-quantive}"
DB_USER="${POSTGRES_USER:-quantive}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="quantive_backup_${TIMESTAMP}.sql.gz"
CHECKSUM_FILE="quantive_backup_${TIMESTAMP}.sha256"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output) BACKUP_DIR="$2"; shift 2 ;;
        --retention) RETENTION_DAYS="$2"; shift 2 ;;
        --help)
            echo "Usage: $0 [--output DIR] [--retention DAYS]"
            echo ""
            echo "Options:"
            echo "  --output DIR      Backup output directory (default: /var/backups/quantive)"
            echo "  --retention DAYS  Days to keep backups (default: 30)"
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "[$(date -Iseconds)] Starting Quantive backup..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Database backup
echo "[$(date -Iseconds)] Backing up database..."
if command -v pg_dump &> /dev/null; then
    PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-owner \
        --no-acl \
        | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"
    echo "[$(date -Iseconds)] Database backup complete: ${BACKUP_FILE}"
else
    echo "[$(date -Iseconds)] WARNING: pg_dump not found, skipping database backup"
    echo "[$(date -Iseconds)] On air-gapped systems, ensure PostgreSQL tools are installed"
fi

# Backup market data if exported
if [ -d "${BACKUP_DIR}/../market-data" ]; then
    echo "[$(date -Iseconds)] Backing up market data..."
    tar czf "${BACKUP_DIR}/quantive_market_data_${TIMESTAMP}.tar.gz" \
        -C "${BACKUP_DIR}/.." market-data/ 2>/dev/null || true
fi

# Backup configuration files
echo "[$(date -Iseconds)] Backing up configuration..."
tar czf "${BACKUP_DIR}/quantive_config_${TIMESTAMP}.tar.gz" \
    -C "$(dirname "$0")/.." \
    docker-compose.airgapped.yml \
    deployment/nginx.prod.conf \
    .env.production.example \
    2>/dev/null || true

# Generate checksums
echo "[$(date -Iseconds)] Generating checksums..."
cd "$BACKUP_DIR"
for file in *_${TIMESTAMP}.*; do
    if [ -f "$file" ]; then
        sha256sum "$file" >> "$CHECKSUM_FILE"
    fi
done

# Clean up old backups
echo "[$(date -Iseconds)] Cleaning up backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "quantive_backup_*" -type f -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "quantive_market_data_*" -type f -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "quantive_config_*" -type f -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "*.sha256" -type f -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true

# Summary
echo ""
echo "[$(date -Iseconds)] Backup complete:"
echo "  Location: ${BACKUP_DIR}"
echo "  Database: ${BACKUP_FILE}"
echo "  Checksums: ${CHECKSUM_FILE}"
echo "  Retention: ${RETENTION_DAYS} days"
echo ""

# List current backups
echo "Current backups:"
ls -lh "$BACKUP_DIR"/quantive_backup_* 2>/dev/null | tail -5 || echo "  (none)"
