# Quantive — Production Implementation Roadmap

> 30-day implementation plan for government-grade production deployment.
> Priority: P0 = Critical (Day 1-7) | P1 = Important (Day 8-21) | P2 = Nice-to-have (Day 22-30)

---

## Table of Contents

1. [Docker Compose Improvements](#1-docker-compose-improvements)
2. [Environment Variables](#2-environment-variables)
3. [Secrets Management](#3-secrets-management)
4. [Backup Strategy](#4-backup-strategy)
5. [Disaster Recovery](#5-disaster-recovery)
6. [Horizontal Scaling Plan](#6-horizontal-scaling-plan)
7. [Load Balancing](#7-load-balancing)
8. [Production Deployment Checklist](#8-production-deployment-checklist)
9. [30-Day Implementation Plan](#9-30-day-implementation-plan)

---

## 1. Docker Compose Improvements

### 1.1 Current State Analysis

**Existing files:**
- `docker-compose.yml` — Dev (SQLite, single container)
- `docker-compose.prod.yml` — Prod (PostgreSQL, Redis, 4 services)
- `backend/Dockerfile` — Python 3.11-slim, non-root user
- `frontend/Dockerfile` — Multi-stage Node 20 + Nginx 1.27

**Gaps identified:**
- No resource limits on dev compose
- No read-only filesystem enforcement on all services
- No seccomp/AppArmor profiles
- No network isolation between frontend↔backend
- No graceful shutdown handling (SIGTERM)
- No log rotation on dev compose
- No health check for frontend in dev
- Missing `depends_on` conditions in dev
- No image pinning (uses `latest` implicitly)
- No multi-stage build optimization for backend
- No `.dockerignore` files

### 1.2 Improved Production Docker Compose

```yaml
# docker-compose.prod.yml — Quantive Production Deployment
# Usage: docker compose -f docker-compose.prod.yml --env-file .env.production up -d

services:
  # ── PostgreSQL 16 ──────────────────────────────────────────────────
  postgres:
    image: postgres:16.4-alpine
    container_name: quantive-postgres
    restart: unless-stopped
    env_file: .env.production
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-quantive}
      POSTGRES_USER: ${POSTGRES_USER:-quantive}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --lc-collate=C --lc-ctype=C"
      POSTGRES_INITDB_WALDIR: /var/lib/postgresql/data/pg_wal
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
      - ./scripts/init-extensions.sql:/docker-entrypoint-initdb.d/02-extensions.sql:ro
      - ./scripts/init-partitions.sql:/docker-entrypoint-initdb.d/03-partitions.sql:ro
      - ./deployment/postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro
      - ./deployment/postgres/pg_hba.conf:/etc/postgresql/pg_hba.conf:ro
    command: >
      postgres
      -c config_file=/etc/postgresql/postgresql.conf
      -c hba_file=/etc/postgresql/pg_hba.conf
      -c shared_buffers=1GB
      -c effective_cache_size=3GB
      -c work_mem=16MB
      -c maintenance_work_mem=256MB
      -c max_connections=200
      -c wal_buffers=16MB
      -c checkpoint_completion_target=0.9
      -c random_page_cost=1.1
      -c effective_io_concurrency=200
      -c min_wal_size=1GB
      -c max_wal_size=4GB
      -c max_worker_processes=4
      -c max_parallel_workers_per_gather=2
      -c max_parallel_workers=4
      -c log_min_duration_statement=1000
      -c log_checkpoints=on
      -c log_connections=on
      -c log_disconnections=on
      -c log_lock_waits=on
      -c log_temp_files=0
      -c log_autovacuum_min_duration=0
      -c archive_mode=on
      -c archive_command='/bin/true'
      -c wal_level=replica
      -c max_wal_senders=3
      -c max_replication_slots=3
      -c hot_standby=on
    ports:
      - "127.0.0.1:5432:5432"
    networks:
      - quantive-backend
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-quantive} -d ${POSTGRES_DB:-quantive}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '4'
        reservations:
          memory: 2G
          cpus: '2'
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - DAC_OVERRIDE
      - FOWNER
      - SETGID
      - SETUID
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "10"
    shm_size: '256mb'
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

  # ── Redis 7 ────────────────────────────────────────────────────────
  redis:
    image: redis:7.4-alpine
    container_name: quantive-redis
    restart: unless-stopped
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --appendfsync everysec
      --auto-aof-rewrite-percentage 100
      --auto-aof-rewrite-min-size 64mb
      --save 900 1
      --save 300 10
      --save 60 10000
      --slowlog-log-slower-than 10000
      --slowlog-max-len 128
      --rename-command FLUSHDB ""
      --rename-command FLUSHALL ""
      --rename-command DEBUG ""
      --tcp-backlog 511
      --timeout 300
    volumes:
      - redis-data:/data
    ports:
      - "127.0.0.1:6379:6379"
    networks:
      - quantive-backend
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '2'
        reservations:
          memory: 512M
          cpus: '0.5'
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - SETGID
      - SETUID
      - DAC_OVERRIDE
    logging:
      driver: json-file
      options:
        max-size: "25m"
        max-file: "5"

  # ── Backend API (FastAPI + Uvicorn) ────────────────────────────────
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      args:
        - PYTHON_VERSION=3.11
    container_name: quantive-backend
    restart: unless-stopped
    env_file: .env.production
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-quantive}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-quantive}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - ENVIRONMENT=production
      - DEBUG=false
      - LOG_LEVEL=WARNING
      - WORKERS=${BACKEND_WORKERS:-4}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - backend-uploads:/app/uploads
      - backend-logs:/app/logs
    networks:
      - quantive-backend
      - quantive-frontend
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '4'
        reservations:
          memory: 2G
          cpus: '2'
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - SETGID
      - SETUID
    read_only: true
    tmpfs:
      - /tmp:size=100M
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "10"
    stop_grace_period: 30s

  # ── Frontend (Nginx) ──────────────────────────────────────────────
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - VITE_API_URL=${VITE_API_URL:-https://yourdomain.gov}
    container_name: quantive-frontend
    restart: unless-stopped
    networks:
      - quantive-frontend
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:80/"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1'
        reservations:
          memory: 128M
          cpus: '0.25'
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - SETGID
      - SETUID
      - DAC_OVERRIDE
    read_only: true
    tmpfs:
      - /var/cache/nginx:size=50M
      - /var/run:size=1M
      - /tmp:size=50M
    logging:
      driver: json-file
      options:
        max-size: "25m"
        max-file: "5"

  # ── Nginx Reverse Proxy ────────────────────────────────────────────
  nginx:
    image: nginx:1.27-alpine
    container_name: quantive-nginx
    restart: unless-stopped
    depends_on:
      backend:
        condition: service_healthy
      frontend:
        condition: service_healthy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deployment/nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - ./deployment/ssl:/etc/nginx/ssl:ro
      - nginx-logs:/var/log/nginx
    networks:
      - quantive-frontend
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:80/"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '1'
        reservations:
          memory: 64M
          cpus: '0.25'
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - SETGID
      - SETUID
      - DAC_OVERRIDE
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /var/cache/nginx:size=50M
      - /var/run:size=1M
      - /tmp:size=50M
    logging:
      driver: json-file
      options:
        max-size: "25m"
        max-file: "5"

  # ── Prometheus Monitoring ──────────────────────────────────────────
  prometheus:
    image: prom/prometheus:v2.53.0
    container_name: quantive-prometheus
    restart: unless-stopped
    volumes:
      - ./deployment/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./deployment/prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro
      - prometheus-data:/prometheus
    ports:
      - "127.0.0.1:9090:9090"
    networks:
      - quantive-backend
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=90d'
      - '--storage.tsdb.retention.size=10GB'
      - '--web.enable-lifecycle'
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '2'
        reservations:
          memory: 512M
          cpus: '0.5'

  # ── Grafana Dashboards ─────────────────────────────────────────────
  grafana:
    image: grafana/grafana:11.1.0
    container_name: quantive-grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=https://yourdomain.gov/grafana
      - GF_AUTH_ANONYMOUS_ENABLED=false
    volumes:
      - grafana-data:/var/lib/grafana
      - ./deployment/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./deployment/grafana/dashboards:/var/lib/grafana/dashboards:ro
    ports:
      - "127.0.0.1:3000:3000"
    networks:
      - quantive-backend
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1'
        reservations:
          memory: 256M
          cpus: '0.25'

  # ── Loki Log Aggregation ──────────────────────────────────────────
  loki:
    image: grafana/loki:3.1.0
    container_name: quantive-loki
    restart: unless-stopped
    volumes:
      - ./deployment/loki/loki.yml:/etc/loki/local-config.yaml:ro
      - loki-data:/loki
    ports:
      - "127.0.0.1:3100:3100"
    networks:
      - quantive-backend
    command: -config.file=/etc/loki/local-config.yaml
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '2'
        reservations:
          memory: 512M
          cpus: '0.5'

# ── Networks ──────────────────────────────────────────────────────────
networks:
  quantive-backend:
    driver: bridge
    internal: true
  quantive-frontend:
    driver: bridge

# ── Volumes ───────────────────────────────────────────────────────────
volumes:
  postgres-data:
    driver: local
  redis-data:
    driver: local
  backend-uploads:
    driver: local
  backend-logs:
    driver: local
  nginx-logs:
    driver: local
  prometheus-data:
    driver: local
  grafana-data:
    driver: local
  loki-data:
    driver: local
```

### 1.3 Backend Dockerfile Improvements

```dockerfile
# backend/Dockerfile — Multi-stage build for smaller image
# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in virtual env
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual env from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy application code
COPY . .

# Create non-root user with specific UID
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/false -m appuser && \
    chown -R appuser:appgroup /app && \
    mkdir -p /app/uploads /app/logs /app/tmp && \
    chown -R appuser:appgroup /app/uploads /app/logs /app/tmp

USER 1001:1001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD curl -f http://127.0.0.1:8000/api/health || exit 1

EXPOSE 8000

# Graceful shutdown
STOPSIGNAL SIGTERM

# Run with uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--limit-concurrency", "1000", \
     "--timeout-keep-alive", "65", \
     "--graceful-timeout", "30", \
     "--access-log", \
     "--log-level", "warning"]
```

### 1.4 Frontend Dockerfile Improvements

```dockerfile
# frontend/Dockerfile — Multi-stage with security hardening
# Stage 1: Build
FROM node:20-alpine AS build

WORKDIR /app

# Copy dependency files first (layer caching)
COPY package.json package-lock.json* ./

# Install dependencies with frozen lockfile
RUN npm ci --prefer-offline --no-audit --no-fund

# Copy source code
COPY . .

# Build argument for API URL
ARG VITE_API_URL=http://127.0.0.1:8000
ENV VITE_API_URL=$VITE_API_URL

# Build the application
RUN npm run build

# Stage 2: Production Nginx
FROM nginx:1.27-alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=build --chown=nginx:nginx /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create nginx cache directories
RUN mkdir -p /var/cache/nginx/client_temp /var/cache/nginx/proxy_temp \
    /var/cache/nginx/fastcgi_temp /var/cache/nginx/uwsgi_temp /var/cache/nginx/scgi_temp && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# Switch to non-root user
USER nginx

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 1.5 Required .dockerignore Files

```dockerignore
# backend/.dockerignore
__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.egg-info
.git
.github
.pytest_cache
.ruff_cache
*.db
*.db-shm
*.db-wal
*.log
.env*
!.env.example
tests/
docs/
scripts/
deployment/
*.md
Dockerfile
docker-compose*
.vscode
.idea
*.swp
*.swo
*~
```

```dockerignore
# frontend/.dockerignore
node_modules
dist
.git
.github
*.log
.env*
!.env.example
.vscode
.idea
*.swp
*.swo
*~
e2e/
playwright.config.ts
```

### 1.6 PostgreSQL Configuration

```ini
# deployment/postgres/postgresql.conf
# Quantive Production PostgreSQL Configuration

# ── Connection Settings ──────────────────────────────────────────────
listen_addresses = '*'
port = 5432
max_connections = 200
superuser_reserved_connections = 3

# ── Memory Settings ──────────────────────────────────────────────────
shared_buffers = 1GB
effective_cache_size = 3GB
work_mem = 16MB
maintenance_work_mem = 256MB
huge_pages = try

# ── WAL Settings ─────────────────────────────────────────────────────
wal_level = replica
wal_buffers = 16MB
max_wal_size = 4GB
min_wal_size = 1GB
checkpoint_completion_target = 0.9
wal_compression = lz4

# ── Parallel Query Settings ──────────────────────────────────────────
max_worker_processes = 4
max_parallel_workers_per_gather = 2
max_parallel_workers = 4
max_parallel_maintenance_workers = 2

# ── Query Planning ───────────────────────────────────────────────────
random_page_cost = 1.1
effective_io_concurrency = 200
default_statistics_target = 100

# ── Logging ──────────────────────────────────────────────────────────
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_min_duration_statement = 1000
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_temp_files = 0
log_autovacuum_min_duration = 0
log_line_prefix = '%m [%p] %q%u@%d '

# ── Autovacuum ───────────────────────────────────────────────────────
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 1min
autovacuum_vacuum_threshold = 50
autovacuum_vacuum_scale_factor = 0.1
autovacuum_analyze_threshold = 50
autovacuum_analyze_scale_factor = 0.05

# ── Replication (for WAL archiving) ──────────────────────────────────
archive_mode = on
archive_command = '/bin/true'
max_wal_senders = 3
max_replication_slots = 3
hot_standby = on

# ── Security ─────────────────────────────────────────────────────────
password_encryption = scram-sha-256
```

```ini
# deployment/postgres/pg_hba.conf
# Quantive PostgreSQL Client Authentication
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Local connections
local   all             all                                     scram-sha-256

# IPv4 local connections
host    all             all             127.0.0.1/32            scram-sha-256

# IPv4 Docker network connections
host    all             all             172.16.0.0/12           scram-sha-256

# IPv6 connections
host    all             all             ::1/128                 scram-sha-256

# Replication connections
local   replication     all                                     scram-sha-256
host    replication     all             127.0.0.1/32            scram-sha-256
host    replication     all             172.16.0.0/12           scram-sha-256

# Deny all other connections
host    all             all             0.0.0.0/0               reject
host    all             all             ::/0                    reject
```

### 1.7 Nginx Production Configuration (Improved)

```nginx
# deployment/nginx.prod.conf — Quantive Production Nginx
worker_processes auto;
worker_rlimit_nofile 65535;

# Error log
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 4096;
    multi_accept on;
    use epoll;
}

http {
    # ── Basic Settings ────────────────────────────────────────────────
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 1000;
    types_hash_max_size 2048;
    client_max_body_size 50M;
    server_tokens off;

    # ── MIME Types ────────────────────────────────────────────────────
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # ── Logging ───────────────────────────────────────────────────────
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time ct=$upstream_connect_time '
                    'ur=$upstream_response_time';

    access_log /var/log/nginx/access.log main buffer=16k flush=5s;

    # ── Gzip Compression ─────────────────────────────────────────────
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 256;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml
        font/woff2;

    # ── Rate Limiting Zones ───────────────────────────────────────────
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=1r/s;
    limit_req_zone $binary_remote_addr zone=optimization:10m rate=5r/m;
    limit_conn_zone $binary_remote_addr zone=conn:10m;

    # ── Upstream Backends (for horizontal scaling) ────────────────────
    upstream backend {
        least_conn;
        server backend-1:8000 max_fails=3 fail_timeout=30s weight=5;
        server backend-2:8000 max_fails=3 fail_timeout=30s weight=5;
        server backend-3:8000 max_fails=3 fail_timeout=30s weight=5 backup;
        keepalive 64;
    }

    upstream frontend {
        server frontend-1:80;
        server frontend-2:80;
        keepalive 32;
    }

    # ── HTTP → HTTPS Redirect ────────────────────────────────────────
    server {
        listen 80;
        listen [::]:80;
        server_name yourdomain.gov;

        # ACME challenge for Let's Encrypt
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$host$request_uri;
        }
    }

    # ── Main HTTPS Server ────────────────────────────────────────────
    server {
        listen 443 ssl http2;
        listen [::]:443 ssl http2;
        server_name yourdomain.gov;

        # ── SSL Configuration ─────────────────────────────────────────
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 1d;
        ssl_session_tickets off;

        # OCSP Stapling
        ssl_stapling on;
        ssl_stapling_verify on;
        resolver 8.8.8.8 8.8.4.4 valid=300s;
        resolver_timeout 5s;

        # ── HSTS ──────────────────────────────────────────────────────
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

        # ── Security Headers ──────────────────────────────────────────
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "DENY" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self' wss://yourdomain.gov" always;
        add_header X-Permitted-Cross-Domain-Policies "none" always;
        add_header Cross-Origin-Embedder-Policy "require-corp" always;
        add_header Cross-Origin-Opener-Policy "same-origin" always;
        add_header Cross-Origin-Resource-Policy "same-origin" always;

        # ── Connection Limits ─────────────────────────────────────────
        limit_conn conn 50;

        # ── API Routes ────────────────────────────────────────────────
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            limit_req_status 429;

            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Request-ID $request_id;
            proxy_set_header X-Forwarded-Host $host;

            proxy_connect_timeout 10s;
            proxy_send_timeout 30s;
            proxy_read_timeout 60s;

            proxy_http_version 1.1;
            proxy_set_header Connection "";
        }

        # ── Auth Routes (Stricter Rate Limiting) ──────────────────────
        location ~ ^/api/(auth|login|register|mfa) {
            limit_req zone=auth burst=3 nodelay;
            limit_req_status 429;

            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Request-ID $request_id;
        }

        # ── Optimization Routes (Special Rate Limiting) ────────────────
        location ~ ^/api/v1/(optimize|simulate) {
            limit_req zone=optimization burst=2 nodelay;
            limit_req_status 429;

            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Request-ID $request_id;

            proxy_read_timeout 180s;
        }

        # ── WebSocket Routes ──────────────────────────────────────────
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_read_timeout 86400;
            proxy_send_timeout 86400;
        }

        # ── Health Check (No Rate Limit) ──────────────────────────────
        location = /api/health {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            access_log off;
        }

        # ── Prometheus Metrics (Internal Only) ────────────────────────
        location = /metrics {
            allow 172.16.0.0/12;
            deny all;
            proxy_pass http://prometheus:9090;
        }

        # ── Frontend Static Files ─────────────────────────────────────
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

            # Cache static assets
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
                proxy_pass http://frontend;
                expires 1y;
                add_header Cache-Control "public, immutable";
                access_log off;
            }

            # No caching for HTML
            location ~* \.html$ {
                proxy_pass http://frontend;
                add_header Cache-Control "no-cache, no-store, must-revalidate";
                add_header Pragma "no-cache";
                add_header Expires "0";
            }
        }

        # ── Block Sensitive Paths ─────────────────────────────────────
        location ~ /\. {
            deny all;
            access_log off;
            log_not_found off;
        }

        location ~* \.(env|git|htaccess|htpasswd|ini|log|bak|sql)$ {
            deny all;
        }
    }
}
```

### 1.8 Development Docker Compose (Improved)

```yaml
# docker-compose.yml — Quantive Development Environment
# Usage: docker compose up -d

services:
  postgres:
    image: postgres:16.4-alpine
    container_name: quantive-dev-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: quantive_dev
      POSTGRES_USER: quantive
      POSTGRES_PASSWORD: devpassword
    volumes:
      - dev-postgres-data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U quantive -d quantive_dev"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7.4-alpine
    container_name: quantive-dev-redis
    restart: unless-stopped
    command: redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru
    ports:
      - "127.0.0.1:6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: builder
    container_name: quantive-dev-backend
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql+asyncpg://quantive:devpassword@postgres:5432/quantive_dev
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=dev-secret-key-not-for-production
      - ENVIRONMENT=development
      - DEBUG=true
      - LOG_LEVEL=INFO
    volumes:
      - ./backend:/app
      - dev-backend-logs:/app/logs
    ports:
      - "127.0.0.1:8000:8000"
    networks:
      - dev-network
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: build
    container_name: quantive-dev-frontend
    restart: unless-stopped
    environment:
      - VITE_API_URL=http://127.0.0.1:8000
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/public:/app/public
    ports:
      - "127.0.0.1:5173:5173"
    networks:
      - dev-network
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:5173/"]
      interval: 30s
      timeout: 5s
      retries: 3

networks:
  dev-network:
    driver: bridge

volumes:
  dev-postgres-data:
  dev-backend-logs:
```

---

## 2. Environment Variables

### 2.1 Complete Environment Variable Reference

```bash
# ============================================================
# Quantive Environment Variables — Production Reference
# ============================================================

# ── CORE SECURITY ─────────────────────────────────────────────────────
# Generate: python -c "import secrets; print(secrets.token_urlsafe(64))"
SECRET_KEY=                          # JWT signing key (64 chars minimum)

# ── DATABASE ──────────────────────────────────────────────────────────
POSTGRES_DB=quantive                  # Database name
POSTGRES_USER=quantive                # Database user
POSTGRES_PASSWORD=                    # Database password (32+ chars)
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}

# ── REDIS ─────────────────────────────────────────────────────────────
REDIS_PASSWORD=                       # Redis password (32+ chars)
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# ── CORS & DOMAINS ────────────────────────────────────────────────────
CORS_ORIGINS=https://yourdomain.gov   # Comma-separated allowed origins
ALLOWED_HOSTS=yourdomain.gov          # Comma-separated allowed hosts

# ── JWT TOKENS ────────────────────────────────────────────────────────
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ── RATE LIMITING ─────────────────────────────────────────────────────
RATE_LIMIT_PER_MINUTE=2000
RATE_LIMIT_AUTH_PER_MINUTE=60
RATE_LIMIT_OPTIMIZATION_PER_MINUTE=5

# ── OPTIMIZATION ──────────────────────────────────────────────────────
OPTIMIZATION_TIMEOUT_SECONDS=120
SOLVER_TIMEOUT_SECONDS=60
MAX_SCENARIO=10000
DEFAULT_SCENARIO=1000

# ── SERVER ────────────────────────────────────────────────────────────
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
WORKERS=4

# ── UPLOADS ───────────────────────────────────────────────────────────
MAX_UPLOAD_SIZE_MB=50
UPLOAD_DIR=/app/uploads

# ── STRIPE BILLING ────────────────────────────────────────────────────
STRIPE_SECRET_KEY=                    # sk_live_... (server-side only)
STRIPE_WEBHOOK_SECRET=               # whsec_... (webhook signing)
STRIPE_PUBLISHABLE_KEY=              # pk_live_... (client-side only)
STRIPE_SUCCESS_BASE_URL=

# ── EMAIL (Optional) ──────────────────────────────────────────────────
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@yourdomain.gov

# ── MONITORING (Optional) ─────────────────────────────────────────────
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.1
PROMETHEUS_ENABLED=true
GRAFANA_PASSWORD=

# ── FRED API (Optional — for enhanced market data) ────────────────────
FRED_API_KEY=

# ── YAHOO FINANCE (Optional) ──────────────────────────────────────────
YAHOO_FINANCE_ENABLED=true

# ── AIR-GAPPED MODE ──────────────────────────────────────────────────
AIR_GAPPED_MODE=false

# ── FRONTEND ──────────────────────────────────────────────────────────
VITE_API_URL=https://yourdomain.gov

# ── DOCKER BUILD ──────────────────────────────────────────────────────
DOCKER_BUILDKIT=1
COMPOSE_DOCKER_CLI_BUILD=1
```

### 2.2 Environment Validation Script

```bash
#!/bin/bash
# scripts/validate-env.sh — Validate environment variables before deployment
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

check_var() {
    local var_name=$1
    local min_length=${2:-1}
    local value="${!var_name:-}"

    if [ -z "$value" ]; then
        echo -e "${RED}✗ $var_name is not set${NC}"
        ((ERRORS++))
    elif [ ${#value} -lt $min_length ]; then
        echo -e "${RED}✗ $var_name is too short (minimum $min_length characters)${NC}"
        ((ERRORS++))
    else
        echo -e "${GREEN}✓ $var_name is set${NC}"
    fi
}

check_no_default() {
    local var_name=$1
    local default_value=$2
    local value="${!var_name:-}"

    if [ "$value" = "$default_value" ]; then
        echo -e "${RED}✗ $var_name is still the default value${NC}"
        ((ERRORS++))
    else
        echo -e "${GREEN}✓ $var_name is customized${NC}"
    fi
}

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       Quantive Environment Validation                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Load env file
if [ -f .env.production ]; then
    set -a
    source .env.production
    set +a
fi

echo "── Security ─────────────────────────────────────────────────"
check_var SECRET_KEY 64
check_no_default SECRET_KEY "change-me-to-a-random-64-char-string"

echo ""
echo "── Database ─────────────────────────────────────────────────"
check_var POSTGRES_PASSWORD 32
check_no_default POSTGRES_PASSWORD "change-me-to-a-secure-password"

echo ""
echo "── Redis ────────────────────────────────────────────────────"
check_var REDIS_PASSWORD 32
check_no_default REDIS_PASSWORD "change-me-to-a-secure-redis-password"

echo ""
echo "── Domain ───────────────────────────────────────────────────"
check_var CORS_ORIGINS 1

echo ""
echo "── Stripe ───────────────────────────────────────────────────"
if [ -n "${STRIPE_SECRET_KEY:-}" ]; then
    if [[ "$STRIPE_SECRET_KEY" == sk_live_* ]]; then
        echo -e "${GREEN}✓ STRIPE_SECRET_KEY is live mode${NC}"
    elif [[ "$STRIPE_SECRET_KEY" == sk_test_* ]]; then
        echo -e "${YELLOW}⚠ STRIPE_SECRET_KEY is test mode${NC}"
    else
        echo -e "${RED}✗ STRIPE_SECRET_KEY has invalid format${NC}"
        ((ERRORS++))
    fi
else
    echo -e "${YELLOW}⚠ STRIPE_SECRET_KEY not set (billing disabled)${NC}"
fi

echo ""
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}Validation failed with $ERRORS error(s)${NC}"
    exit 1
else
    echo -e "${GREEN}All checks passed${NC}"
    exit 0
fi
```

---

## 3. Secrets Management

### 3.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Secrets Management Architecture              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Dev: .env  │    │  Stage: SSM  │    │  Prod: Vault │      │
│  │   file       │    │  Parameter   │    │  / KMS       │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Docker Secrets / Environment               │   │
│  └─────────────────────────────────────────────────────────┘   │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           Application Runtime (FastAPI)                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Docker Secrets (Compose v2)

```yaml
# docker-compose.prod.yml — Secrets configuration
secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
  redis_password:
    file: ./secrets/redis_password.txt
  secret_key:
    file: ./secrets/secret_key.txt
  stripe_secret_key:
    file: ./secrets/stripe_secret_key.txt
  stripe_webhook_secret:
    file: ./secrets/stripe_webhook_secret.txt
  ssl_certificate:
    file: ./secrets/ssl/fullchain.pem
  ssl_private_key:
    file: ./secrets/ssl/privkey.pem

services:
  backend:
    secrets:
      - postgres_password
      - redis_password
      - secret_key
      - stripe_secret_key
      - stripe_webhook_secret
```

### 3.3 Secrets Directory Structure

```
secrets/
├── postgres_password.txt      # chmod 600
├── redis_password.txt         # chmod 600
├── secret_key.txt             # chmod 600
├── stripe_secret_key.txt      # chmod 600
├── stripe_webhook_secret.txt  # chmod 600
└── ssl/
    ├── fullchain.pem          # chmod 644
    └── privkey.pem            # chmod 600
```

### 3.4 Secrets Generation Script

```bash
#!/bin/bash
# scripts/generate-secrets.sh — Generate all production secrets
set -euo pipefail

SECRETS_DIR="./secrets"
SSL_DIR="$SECRETS_DIR/ssl"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       Quantive Secret Generation                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Create directories
mkdir -p "$SECRETS_DIR" "$SSL_DIR"

# Generate secrets
echo "Generating SECRET_KEY..."
python -c "import secrets; print(secrets.token_urlsafe(64))" > "$SECRETS_DIR/secret_key.txt"

echo "Generating POSTGRES_PASSWORD..."
python -c "import secrets; print(secrets.token_urlsafe(32))" > "$SECRETS_DIR/postgres_password.txt"

echo "Generating REDIS_PASSWORD..."
python -c "import secrets; print(secrets.token_urlsafe(32))" > "$SECRETS_DIR/redis_password.txt"

# Stripe keys (user must provide)
if [ ! -f "$SECRETS_DIR/stripe_secret_key.txt" ]; then
    echo ""
    echo "Enter Stripe Secret Key (sk_live_...):"
    read -r stripe_secret
    echo "$stripe_secret" > "$SECRETS_DIR/stripe_secret_key.txt"
fi

if [ ! -f "$SECRETS_DIR/stripe_webhook_secret.txt" ]; then
    echo "Enter Stripe Webhook Secret (whsec_...):"
    read -r stripe_webhook
    echo "$stripe_webhook" > "$SECRETS_DIR/stripe_webhook_secret.txt"
fi

# Generate self-signed SSL (replace with real certs in production)
if [ ! -f "$SSL_DIR/fullchain.pem" ]; then
    echo "Generating self-signed SSL certificate..."
    openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
        -keyout "$SSL_DIR/privkey.pem" \
        -out "$SSL_DIR/fullchain.pem" \
        -subj "/C=US/ST=State/L=City/O=Quantive/CN=yourdomain.gov" \
        2>/dev/null
fi

# Set permissions
chmod 600 "$SECRETS_DIR"/*.txt
chmod 600 "$SSL_DIR"/privkey.pem
chmod 644 "$SSL_DIR"/fullchain.pem

echo ""
echo "✓ Secrets generated in $SECRETS_DIR/"
echo ""
echo "IMPORTANT: Add secrets/ to .gitignore!"
echo "echo 'secrets/' >> .gitignore"
```

### 3.5 .gitignore Addition

```gitignore
# secrets
secrets/
*.pem
*.key
.env.production
.env.local
```

### 3.6 AWS Secrets Manager Integration (Optional)

```python
# backend/app/secrets_manager.py
"""AWS Secrets Manager integration for production deployments."""

import json
import os
from functools import lru_cache
from typing import Optional

import boto3
from botocore.exceptions import ClientError


class SecretsManager:
    """Fetch secrets from AWS Secrets Manager with caching."""

    def __init__(self, region_name: str = "us-east-1"):
        self.client = boto3.client("secretsmanager", region_name=region_name)
        self._cache: dict[str, str] = {}

    def get_secret(self, secret_name: str, key: Optional[str] = None) -> str:
        """Fetch a secret value."""
        if secret_name in self._cache:
            return self._cache[secret_name]

        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            secret_string = response["SecretString"]

            if key:
                secret_dict = json.loads(secret_string)
                value = secret_dict.get(key, "")
            else:
                value = secret_string

            self._cache[secret_name] = value
            return value

        except ClientError as e:
            raise RuntimeError(f"Failed to fetch secret {secret_name}: {e}")


@lru_cache()
def get_secrets_manager() -> SecretsManager:
    """Get cached Secrets Manager instance."""
    return SecretsManager(
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )


def get_secret(name: str, key: Optional[str] = None) -> str:
    """Convenience function to fetch a secret."""
    return get_secrets_manager().get_secret(name, key)
```

---

## 4. Backup Strategy

### 4.1 Backup Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Backup Strategy Overview                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │
│  │ PostgreSQL   │────▶│ pg_dump     │────▶│ S3/GCS      │       │
│  │ WAL Archiving│     │ + Compress  │     │ + Encryption│       │
│  └─────────────┘     └─────────────┘     └─────────────┘       │
│                                                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │
│  │ Redis        │────▶│ BGSAVE      │────▶│ Volume Snap │       │
│  │ Persistence  │     │ + AOF       │     │             │       │
│  └─────────────┘     └─────────────┘     └─────────────┘       │
│                                                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │
│  │ Uploads/     │────▶│ Tar + Gzip  │────▶│ S3/GCS      │       │
│  │ Files        │     │             │     │             │       │
│  └─────────────┘     └─────────────┘     └─────────────┘       │
│                                                                 │
│  Schedule:                                                      │
│  - Full backup: Daily 02:00 UTC                                │
│  - Incremental: Every 6 hours                                  │
│  - WAL archiving: Continuous                                   │
│  - Retention: 30 days local, 90 days cloud                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Backup Script

```bash
#!/bin/bash
# scripts/backup.sh — Quantive Production Backup
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────
BACKUP_DIR="/backups/quantive"
S3_BUCKET="s3://quantive-backups/$(hostname)"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/quantive_${TIMESTAMP}.sql.gz"
LOG_FILE="$BACKUP_DIR/backup_${TIMESTAMP}.log"

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# ── Pre-backup Checks ────────────────────────────────────────────────
log "Starting Quantive backup..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! docker compose ps postgres | grep -q "healthy"; then
    echo -e "${RED}Error: PostgreSQL is not healthy${NC}"
    exit 1
fi

mkdir -p "$BACKUP_DIR"

# ── Database Backup ───────────────────────────────────────────────────
log "Dumping PostgreSQL database..."

docker compose exec -T postgres pg_dump \
    -U quantive \
    -d quantive \
    --format=custom \
    --compress=9 \
    --verbose \
    --file=/tmp/backup_${TIMESTAMP}.dump

docker compose cp postgres:/tmp/backup_${TIMESTAMP}.dump "$BACKUP_DIR/"

log "Compressing backup..."
gzip -9 "$BACKUP_DIR/backup_${TIMESTAMP}.dump"
BACKUP_FILE="$BACKUP_DIR/backup_${TIMESTAMP}.dump.gz"

# ── Verify Backup ─────────────────────────────────────────────────────
log "Verifying backup integrity..."
if gzip -t "$BACKUP_FILE"; then
    log "✓ Backup integrity verified"
else
    log "✗ Backup integrity check failed!"
    exit 1
fi

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log "✓ Database backup completed: $BACKUP_SIZE"

# ── Upload to S3 (if configured) ─────────────────────────────────────
if command -v aws &> /dev/null && [ -n "${AWS_REGION:-}" ]; then
    log "Uploading to S3..."
    aws s3 cp "$BACKUP_FILE" "$S3_BUCKET/backups/" \
        --storage-class STANDARD_IA \
        --sse AES256 \
        --only-show-errors
    log "✓ Uploaded to S3: $S3_BUCKET/backups/"
fi

# ── Cleanup Old Backups ──────────────────────────────────────────────
log "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.log" -mtime +$RETENTION_DAYS -delete

# ── Summary ───────────────────────────────────────────────────────────
log ""
log "╔══════════════════════════════════════════════════════════════╗"
log "║       Backup Complete                                        ║"
log "╚══════════════════════════════════════════════════════════════╝"
log "  File: $BACKUP_FILE"
log "  Size: $BACKUP_SIZE"
log "  Log:  $LOG_FILE"
```

### 4.3 Restore Script

```bash
#!/bin/bash
# scripts/restore.sh — Quantive Database Restore
set -euo pipefail

BACKUP_FILE="${1:-}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./scripts/restore.sh <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh /backups/quantive/*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       Quantive Database Restore                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "⚠️  WARNING: This will OVERWRITE the current database!"
echo "Backup file: $BACKUP_FILE"
echo ""
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

# ── Stop Backend ──────────────────────────────────────────────────────
echo "Stopping backend..."
docker compose stop backend

# ── Drop and Recreate Database ────────────────────────────────────────
echo "Dropping and recreating database..."
docker compose exec -T postgres psql -U quantive -d postgres -c "
    SELECT pg_terminate_backend(pid) FROM pg_stat_activity
    WHERE datname = 'quantive' AND pid <> pg_backend_pid();
    DROP DATABASE IF EXISTS quantive;
    CREATE DATABASE quantive OWNER quantive;
"

# ── Restore from Backup ──────────────────────────────────────────────
echo "Restoring from backup..."
gunzip -c "$BACKUP_FILE" | docker compose exec -T postgres pg_dump \
    -U quantive \
    -d quantive \
    --no-owner \
    --no-privileges

# ── Run Migrations ────────────────────────────────────────────────────
echo "Running migrations..."
docker compose exec -T postgres psql -U quantive -d quantive -f /docker-entrypoint-initdb.d/01-init.sql

# ── Restart Services ──────────────────────────────────────────────────
echo "Restarting services..."
docker compose up -d

# ── Verify ────────────────────────────────────────────────────────────
echo "Waiting for services to be healthy..."
sleep 10

if curl -sf http://localhost/api/health > /dev/null 2>&1; then
    echo "✓ Restore completed successfully"
else
    echo "⚠ Backend is still starting..."
fi
```

### 4.4 Automated Backup Cron

```bash
# /etc/cron.d/quantive-backup
# Quantive automated backups

# Full backup daily at 02:00 UTC
0 2 * * * root /opt/quantive/scripts/backup.sh >> /var/log/quantive-backup.log 2>&1

# Cleanup old backups weekly on Sunday at 03:00 UTC
0 3 * * 0 root find /backups/quantive -name "*.sql.gz" -mtime +30 -delete

# Verify backup integrity daily at 04:00 UTC
0 4 * * * root /opt/quantive/scripts/verify-backup.sh >> /var/log/quantive-backup-verify.log 2>&1
```

---

## 5. Disaster Recovery

### 5.1 DR Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 Disaster Recovery Architecture                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PRIMARY SITE (Region A)          DR SITE (Region B)            │
│  ┌─────────────────┐              ┌─────────────────┐           │
│  │ PostgreSQL       │◄──WAL──────▶│ PostgreSQL       │           │
│  │ (Primary)        │  Streaming  │ (Standby)        │           │
│  └─────────────────┘              └─────────────────┘           │
│                                                                 │
│  ┌─────────────────┐              ┌─────────────────┐           │
│  │ Backend          │              │ Backend          │           │
│  │ (Active)         │              │ (Standby)        │           │
│  └─────────────────┘              └─────────────────┘           │
│                                                                 │
│  ┌─────────────────┐              ┌─────────────────┐           │
│  │ Frontend         │              │ Frontend         │           │
│  │ (Active)         │              │ (Standby)        │           │
│  └─────────────────┘              └─────────────────┘           │
│                                                                 │
│  RPO: 0 (WAL streaming)         RTO: < 5 minutes               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 RTO/RPO Targets

| Component | RPO | RTO | Strategy |
|-----------|-----|-----|----------|
| PostgreSQL | 0 (WAL) | < 5 min | Streaming replication + failover |
| Backend API | N/A | < 2 min | Auto-restart + load balancer |
| Frontend | N/A | < 1 min | Static files + CDN |
| Redis | 5 min | < 1 min | AOF persistence + replication |
| File Uploads | 0 | < 10 min | S3 cross-region replication |

### 5.3 Failover Script

```bash
#!/bin/bash
# scripts/failover.sh — DR Failover to Standby
set -euo pipefail

DR_SITE="${1:-}"

if [ -z "$DR_SITE" ]; then
    echo "Usage: ./scripts/failover.sh <dr-site-host>"
    exit 1
fi

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       Quantive DR Failover                                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "⚠️  CRITICAL: This will failover to DR site: $DR_SITE"
echo ""
read -p "Type 'FAILOVER' to confirm: " confirm

if [ "$confirm" != "FAILOVER" ]; then
    echo "Failover cancelled."
    exit 0
fi

# ── Step 1: Stop Primary Traffic ─────────────────────────────────────
echo "Step 1: Stopping traffic to primary..."
docker compose stop nginx

# ── Step 2: Verify Standby is Caught Up ──────────────────────────────
echo "Step 2: Verifying standby replication lag..."
STANDBY_LAG=$(ssh "$DR_SITE" "docker compose exec -T postgres psql -U quantive -d quantive -t -c 'SELECT CASE WHEN pg_is_in_recovery() THEN extract(epoch from now() - pg_last_xact_replay_timestamp())::int ELSE 0 END;'")

if [ "$STANDBY_LAG" -gt 60 ]; then
    echo "Warning: Standby is $STANDBY_LAG seconds behind"
    read -p "Continue anyway? (yes/no): " continue_anyway
    if [ "$continue_anyway" != "yes" ]; then
        exit 1
    fi
fi

# ── Step 3: Promote Standby ──────────────────────────────────────────
echo "Step 3: Promoting standby to primary..."
ssh "$DR_SITE" "docker compose exec -T postgres psql -U quantive -d postgres -c 'SELECT pg_promote();'"

# ── Step 4: Update DNS ──────────────────────────────────────────────
echo "Step 4: Updating DNS records..."
# This depends on your DNS provider (Route53, Cloudflare, etc.)
# Example for AWS Route53:
# aws route53 change-resource-record-sets \
#     --hosted-zone-id Z1234567890 \
#     --change-batch file://dns-failover.json

# ── Step 5: Start DR Services ───────────────────────────────────────
echo "Step 5: Starting DR services..."
ssh "$DR_SITE" "docker compose up -d"

# ── Step 6: Verify ──────────────────────────────────────────────────
echo "Step 6: Verifying DR site..."
sleep 15

if curl -sf "https://$DR_SITE/api/health" > /dev/null 2>&1; then
    echo "✓ DR failover completed successfully"
    echo "  DR Site: https://$DR_SITE"
else
    echo "⚠ DR site is still starting..."
fi
```

### 5.4 PostgreSQL Streaming Replication Setup

```bash
#!/bin/bash
# scripts/setup-replication.sh — Configure PostgreSQL streaming replication
set -euo pipefail

PRIMARY_HOST="${1:?Usage: $0 <primary-host>}"
STANDBY_HOST="${2:?Usage: $0 <primary-host> <standby-host>}"

echo "Setting up PostgreSQL streaming replication..."
echo "Primary: $PRIMARY_HOST"
echo "Standby: $STANDBY_HOST"

# ── On Primary: Create replication user ──────────────────────────────
ssh "$PRIMARY_HOST" "docker compose exec -T postgres psql -U quantive -d quantive -c \"
    CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD '\$(cat /run/secrets/postgres_password)';
\""

# ── On Primary: Update pg_hba.conf ───────────────────────────────────
ssh "$PRIMARY_HOST" "docker compose exec -T postgres bash -c \"
    echo 'host replication replicator $STANDBY_HOST/32 scram-sha-256' >> /etc/postgresql/pg_hba.conf
    pg_ctl reload
\""

# ── On Primary: Create replication slot ──────────────────────────────
ssh "$PRIMARY_HOST" "docker compose exec -T postgres psql -U quantive -d quantive -c \"
    SELECT pg_create_physical_replication_slot('standby_slot');
\""

# ── On Standby: Base backup from primary ─────────────────────────────
ssh "$STANDBY_HOST" "docker compose exec -T postgres bash -c \"
    rm -rf /var/lib/postgresql/data/*
    pg_basebackup -h $PRIMARY_HOST -U replicator -D /var/lib/postgresql/data -Fp -Xs -P -R
    echo 'primary_slot_name = '\''standby_slot'\''' >> /var/lib/postgresql/data/postgresql.auto.conf
    touch /var/lib/postgresql/data standby.signal
    chown -R postgres:postgres /var/lib/postgresql/data
\""

# ── On Standby: Start PostgreSQL ─────────────────────────────────────
ssh "$STANDBY_HOST" "docker compose restart postgres"

echo "✓ Replication setup complete"
```

---

## 6. Horizontal Scaling Plan

### 6.1 Scaling Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Horizontal Scaling Architecture                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                    ┌─────────────────┐                          │
│                    │   Load Balancer │                          │
│                    │   (Nginx/HAProxy)│                         │
│                    └────────┬────────┘                          │
│                             │                                   │
│              ┌──────────────┼──────────────┐                    │
│              │              │              │                    │
│              ▼              ▼              ▼                    │
│     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│     │ Backend-1   │ │ Backend-2   │ │ Backend-3   │           │
│     │ (4 workers) │ │ (4 workers) │ │ (4 workers) │           │
│     └──────┬──────┘ └──────┬──────┘ └──────┬──────┘           │
│            │               │               │                    │
│            └───────────────┼───────────────┘                    │
│                            │                                    │
│              ┌─────────────┼─────────────┐                      │
│              │             │             │                      │
│              ▼             ▼             ▼                      │
│     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│     │ PostgreSQL  │ │ PostgreSQL  │ │ Redis       │           │
│     │ Primary     │ │ Standby     │ │ Cluster     │           │
│     └─────────────┘ └─────────────┘ └─────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Scaling Triggers

| Metric | Threshold | Action |
|--------|-----------|--------|
| CPU > 70% | 5 min | Add backend instance |
| CPU < 30% | 15 min | Remove backend instance |
| Memory > 80% | 5 min | Add backend instance |
| Request queue > 100 | 1 min | Add backend instance |
| Response time > 2s | 5 min | Add backend instance |
| Connection pool > 80% | 5 min | Add PostgreSQL read replica |

### 6.3 Backend Scaling Script

```bash
#!/bin/bash
# scripts/scale-backend.sh — Scale backend instances
set -euo pipefail

ACTION="${1:-scale}"
COUNT="${2:-2}"

case "$ACTION" in
    scale)
        echo "Scaling backend to $COUNT instances..."
        docker compose -f docker-compose.prod.yml up -d --scale backend=$COUNT
        ;;
    status)
        echo "Backend instances:"
        docker compose -f docker-compose.prod.yml ps backend
        ;;
    *)
        echo "Usage: $0 <scale|status> [count]"
        exit 1
        ;;
esac
```

### 6.4 Database Read Replica Configuration

```python
# backend/app/database_read_replica.py
"""Read replica routing for horizontal scaling."""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Primary database (read/write)
PRIMARY_DATABASE_URL = os.getenv("DATABASE_URL")

# Read replica (read-only)
REPLICA_DATABASE_URL = os.getenv(
    "REPLICA_DATABASE_URL",
    PRIMARY_DATABASE_URL  # Falls back to primary if no replica
)

# Engines
primary_engine = create_engine(
    PRIMARY_DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

replica_engine = create_engine(
    REPLICA_DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

PrimarySessionLocal = sessionmaker(bind=primary_engine)
ReplicaSessionLocal = sessionmaker(bind=replica_engine)


@contextmanager
def get_primary_db() -> Generator[Session, None, None]:
    """Get primary database session (for writes)."""
    session = PrimarySessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_replica_db() -> Generator[Session, None, None]:
    """Get replica database session (for reads)."""
    session = ReplicaSessionLocal()
    try:
        yield session
    except Exception:
        raise
    finally:
        session.close()


def get_db_read_only() -> Generator[Session, None, None]:
    """FastAPI dependency for read-only operations."""
    with get_replica_db() as session:
        yield session


def get_db_read_write() -> Generator[Session, None, None]:
    """FastAPI dependency for read-write operations."""
    with get_primary_db() as session:
        yield session
```

---

## 7. Load Balancing

### 7.1 Nginx Load Balancer Configuration

```nginx
# deployment/nginx-lb.conf — Dedicated load balancer configuration
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    multi_accept on;
    use epoll;
}

http {
    # ── Upstream Backends ─────────────────────────────────────────────
    upstream backend_pool {
        least_conn;

        # Active servers
        server backend-1:8000 max_fails=3 fail_timeout=30s weight=5;
        server backend-2:8000 max_fails=3 fail_timeout=30s weight=5;
        server backend-3:8000 max_fails=3 fail_timeout=30s weight=5;
        server backend-4:8000 max_fails=3 fail_timeout=30s weight=5;

        # Backup server (used when all active are down)
        server backend-backup:8000 backup;

        # Keepalive connections
        keepalive 128;
        keepalive_timeout 60s;
        keepalive_requests 1000;
    }

    # ── Upstream Frontends ────────────────────────────────────────────
    upstream frontend_pool {
        server frontend-1:80;
        server frontend-2:80;
        keepalive 64;
    }

    # ── Connection Tracking ───────────────────────────────────────────
    limit_conn_zone $binary_remote_addr zone=conn:10m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=1r/s;

    # ── Main Server ───────────────────────────────────────────────────
    server {
        listen 443 ssl http2;
        server_name yourdomain.gov;

        # SSL configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        # Security headers
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "DENY" always;

        # Connection limits
        limit_conn conn 50;

        # API routes
        location /api/ {
            limit_req zone=api burst=20 nodelay;

            proxy_pass http://backend_pool;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Request-ID $request_id;

            # Connection keepalive
            proxy_http_version 1.1;
            proxy_set_header Connection "";

            # Timeouts
            proxy_connect_timeout 10s;
            proxy_send_timeout 30s;
            proxy_read_timeout 60s;
        }

        # WebSocket routes
        location /ws/ {
            proxy_pass http://backend_pool;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 86400;
        }

        # Frontend
        location / {
            proxy_pass http://frontend_pool;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Health check
        location = /health {
            proxy_pass http://backend_pool;
            access_log off;
        }
    }
}
```

### 7.2 HAProxy Configuration (Alternative)

```haproxy
# deployment/haproxy.cfg — HAProxy load balancer
global
    log stdout format raw local0
    maxconn 10000
    ssl-default-bind-ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384
    ssl-default-bind-options ssl-min-ver TLSv1.2
    tune.ssl.default-dh-param 2048

defaults
    log     global
    mode    http
    option  httplog
    option  dontlognull
    timeout connect 10s
    timeout client  30s
    timeout server  60s
    retries 3

# ── Stats Dashboard ──────────────────────────────────────────────
listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 10s
    stats admin if LOCALHOST

# ── Frontend SSL Termination ─────────────────────────────────────
frontend https
    bind *:443 ssl crt /etc/haproxy/certs/
    bind *:80
    redirect scheme https code 301 if !{ ssl_fc }

    # Security headers
    http-response set-header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
    http-response set-header X-Content-Type-Options "nosniff"
    http-response set-header X-Frame-Options "DENY"

    # Rate limiting
    stick-table type ip size 100k expire 30s store http_req_rate(10s)
    http-request track-sc0 src
    http-request deny deny_status 429 if { sc_http_req_rate(0) gt 100 }

    # Routing
    acl is_api path_beg /api/
    acl is_ws path_beg /ws/
    acl is_health path /api/health

    use_platform backend_api if is_api
    use_platform backend_ws if is_ws
    use_platform backend_health if is_health
    default_backend frontend

# ── Backend Servers ──────────────────────────────────────────────
backend backend_api
    balance leastconn
    option httpchk GET /api/health
    http-check expect status 200

    server backend-1 backend-1:8000 check inter 10s fall 3 rise 2 weight 5
    server backend-2 backend-2:8000 check inter 10s fall 3 rise 2 weight 5
    server backend-3 backend-3:8000 check inter 10s fall 3 rise 2 weight 5
    server backend-4 backend-4:8000 check inter 10s fall 3 rise 2 weight 5 backup

backend backend_ws
    balance source
    timeout tunnel 3600s
    timeout server 3600s

    server backend-1 backend-1:8000 check
    server backend-2 backend-2:8000 check
    server backend-3 backend-3:8000 check

backend backend_health
    balance roundrobin
    option httpchk GET /api/health

    server backend-1 backend-1:8000 check

# ── Frontend Servers ─────────────────────────────────────────────
backend frontend
    balance roundrobin
    option httpchk GET /

    server frontend-1 frontend-1:80 check
    server frontend-2 frontend-2:80 check
```

---

## 8. Production Deployment Checklist

### 8.1 Pre-Deployment

```markdown
# Pre-Deployment Checklist

## Security
- [ ] SECRET_KEY generated (64+ chars, not default)
- [ ] POSTGRES_PASSWORD generated (32+ chars, not default)
- [ ] REDIS_PASSWORD generated (32+ chars, not default)
- [ ] SSL certificates installed (not self-signed)
- [ ] .env.production file created (not committed to git)
- [ ] secrets/ directory in .gitignore
- [ ] DEBUG=false
- [ ] CORS_ORIGINS set to production domain only
- [ ] Stripe keys are live mode (sk_live_, pk_live_)

## Infrastructure
- [ ] Docker installed and running
- [ ] Docker Compose v2 installed
- [ ] Sufficient disk space (>50GB)
- [ ] Sufficient memory (>16GB)
- [ ] Firewall configured (ports 80, 443 only)
- [ ] DNS configured for production domain
- [ ] NTP configured (chrony/ntpd)

## Database
- [ ] PostgreSQL 16 running
- [ ] init-db.sql executed
- [ ] Database backups configured
- [ ] WAL archiving enabled
- [ ] Connection pooling configured
- [ ] Monitoring enabled (pg_stat_statements)

## Application
- [ ] Backend builds successfully
- [ ] Frontend builds successfully
- [ ] All tests pass
- [ ] Linting passes
- [ ] Type checking passes
- [ ] Health checks configured
- [ ] Logging configured
- [ ] Error tracking (Sentry) configured

## Monitoring
- [ ] Prometheus configured
- [ ] Grafana dashboards configured
- [ ] Loki log aggregation configured
- [ ] Alert rules configured
- [ ] On-call rotation established
```

### 8.2 Deployment Steps

```bash
#!/bin/bash
# scripts/deploy-production.sh — Full production deployment
set -euo pipefail

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       Quantive Production Deployment                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Validate Environment ─────────────────────────────────────
echo "Step 1: Validating environment..."
./scripts/validate-env.sh
if [ $? -ne 0 ]; then
    echo "Environment validation failed!"
    exit 1
fi

# ── Step 2: Generate Secrets ─────────────────────────────────────────
echo "Step 2: Generating secrets..."
if [ ! -d secrets ]; then
    ./scripts/generate-secrets.sh
fi

# ── Step 3: Build Images ─────────────────────────────────────────────
echo "Step 3: Building Docker images..."
docker compose -f docker-compose.prod.yml build --no-cache

# ── Step 4: Run Tests ────────────────────────────────────────────────
echo "Step 4: Running tests..."
docker compose -f docker-compose.prod.yml run --rm backend python -m pytest tests/ -q
docker compose -f docker-compose.prod.yml run --rm frontend npm test

# ── Step 5: Backup Current State ─────────────────────────────────────
echo "Step 5: Backing up current state..."
./scripts/backup.sh

# ── Step 6: Deploy ───────────────────────────────────────────────────
echo "Step 6: Deploying services..."
docker compose -f docker-compose.prod.yml up -d

# ── Step 7: Health Checks ────────────────────────────────────────────
echo "Step 7: Running health checks..."
sleep 30

services=("postgres" "redis" "backend" "frontend" "nginx")
for service in "${services[@]}"; do
    if docker compose -f docker-compose.prod.yml ps $service | grep -q "healthy\|running"; then
        echo "✓ $service is healthy"
    else
        echo "✗ $service failed health check"
        docker compose -f docker-compose.prod.yml logs $service | tail -20
    fi
done

# ── Step 8: Run Migrations ───────────────────────────────────────────
echo "Step 8: Running database migrations..."
docker compose -f docker-compose.prod.yml exec -T postgres psql -U quantive -d quantive -f /docker-entrypoint-initdb.d/01-init.sql

# ── Step 9: Verify ───────────────────────────────────────────────────
echo "Step 9: Verifying deployment..."
if curl -sf https://yourdomain.gov/api/health > /dev/null 2>&1; then
    echo "✓ Deployment successful!"
else
    echo "⚠ Health check failed - check logs"
    docker compose -f docker-compose.prod.yml logs backend | tail -50
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       Deployment Complete                                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
```

### 8.3 Post-Deployment Verification

```bash
#!/bin/bash
# scripts/verify-deployment.sh — Post-deployment verification
set -euo pipefail

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       Quantive Deployment Verification                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

ERRORS=0

# ── Check 1: API Health ──────────────────────────────────────────────
echo "Checking API health..."
if curl -sf https://yourdomain.gov/api/health > /dev/null 2>&1; then
    echo "✓ API is responding"
else
    echo "✗ API is not responding"
    ((ERRORS++))
fi

# ── Check 2: Database Connectivity ───────────────────────────────────
echo "Checking database connectivity..."
DB_STATUS=$(curl -sf https://yourdomain.gov/api/health | python -c "import sys, json; print(json.load(sys.stdin).get('database', 'unknown'))")
if [ "$DB_STATUS" = "healthy" ]; then
    echo "✓ Database is connected"
else
    echo "✗ Database status: $DB_STATUS"
    ((ERRORS++))
fi

# ── Check 3: SSL Certificate ────────────────────────────────────────
echo "Checking SSL certificate..."
SSL_EXPIRY=$(echo | openssl s_client -servername yourdomain.gov -connect yourdomain.gov:443 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
if [ -n "$SSL_EXPIRY" ]; then
    echo "✓ SSL certificate valid until: $SSL_EXPIRY"
else
    echo "✗ SSL certificate check failed"
    ((ERRORS++))
fi

# ── Check 4: Response Time ──────────────────────────────────────────
echo "Checking response time..."
RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' https://yourdomain.gov/api/health)
if (( $(echo "$RESPONSE_TIME < 2.0" | bc -l) )); then
    echo "✓ Response time: ${RESPONSE_TIME}s"
else
    echo "⚠ Response time slow: ${RESPONSE_TIME}s"
fi

# ── Check 5: Container Status ────────────────────────────────────────
echo "Checking container status..."
docker compose -f docker-compose.prod.yml ps --format "table {{.Name}}\t{{.Status}}" | while read line; do
    echo "  $line"
done

# ── Summary ───────────────────────────────────────────────────────────
echo ""
if [ $ERRORS -gt 0 ]; then
    echo "✗ Verification failed with $ERRORS error(s)"
    exit 1
else
    echo "✓ All verification checks passed"
    exit 0
fi
```

---

## 9. 30-Day Implementation Plan

### Phase 1: Critical Foundation (Day 1-7) — P0

| Day | Task | Time | Complexity | Dependencies | Risk |
|-----|------|------|------------|--------------|------|
| 1-2 | Docker Compose improvements | 16h | Medium | None | Low |
| 1-2 | Backend multi-stage Dockerfile | 4h | Low | None | Low |
| 1-2 | Frontend multi-stage Dockerfile | 4h | Low | None | Low |
| 2-3 | PostgreSQL configuration | 8h | Medium | Docker Compose | Medium |
| 2-3 | Secrets management | 8h | Medium | None | Medium |
| 3-4 | Environment validation | 4h | Low | Secrets | Low |
| 4-5 | Backup script | 8h | Medium | PostgreSQL | Low |
| 5-6 | Health check improvements | 4h | Low | Docker | Low |
| 6-7 | Security hardening (seccomp, cap_drop) | 8h | High | Docker | Medium |
| **Total** | | **64h** | | | |

### Phase 2: Monitoring & Observability (Day 8-14) — P0

| Day | Task | Time | Complexity | Dependencies | Risk |
|-----|------|------|------------|--------------|------|
| 8-9 | Prometheus setup | 8h | Medium | Docker | Low |
| 9-10 | Grafana dashboards | 8h | Medium | Prometheus | Low |
| 10-11 | Loki log aggregation | 8h | High | Docker | Medium |
| 11-12 | Backend metrics endpoint | 4h | Low | Prometheus | Low |
| 12-13 | Alert rules configuration | 8h | Medium | Prometheus, Grafana | Medium |
| 13-14 | Logging configuration | 4h | Low | Loki | Low |
| **Total** | | **40h** | | | |

### Phase 3: Disaster Recovery (Day 15-21) — P1

| Day | Task | Time | Complexity | Dependencies | Risk |
|-----|------|------|------------|--------------|------|
| 15-16 | WAL archiving setup | 8h | High | PostgreSQL | Medium |
| 16-17 | Streaming replication | 12h | High | PostgreSQL | High |
| 17-18 | Failover script | 8h | High | Replication | High |
| 18-19 | Backup verification | 4h | Medium | Backup script | Low |
| 19-20 | DR runbook documentation | 4h | Low | All DR | Low |
| 20-21 | DR testing | 8h | Medium | All DR | Medium |
| **Total** | | **44h** | | | |

### Phase 4: Horizontal Scaling (Day 22-26) — P1

| Day | Task | Time | Complexity | Dependencies | Risk |
|-----|------|------|------------|--------------|------|
| 22-23 | Load balancer configuration | 8h | Medium | Docker | Low |
| 23-24 | Backend scaling scripts | 4h | Low | Load balancer | Low |
| 24-25 | Database read replicas | 12h | High | PostgreSQL | High |
| 25-26 | Connection pooling | 8h | Medium | Read replicas | Medium |
| **Total** | | **32h** | | | |

### Phase 5: Production Hardening (Day 27-30) — P2

| Day | Task | Time | Complexity | Dependencies | Risk |
|-----|------|------|------------|--------------|------|
| 27-28 | Deployment automation | 8h | Medium | All P0 | Low |
| 28-29 | Performance testing | 8h | High | Scaling | Medium |
| 29-30 | Security audit | 8h | High | All P0 | Medium |
| 30 | Documentation | 4h | Low | All | Low |
| **Total** | | **28h** | | | |

---

### Summary

| Phase | Priority | Duration | Complexity | Risk |
|-------|----------|----------|------------|------|
| Critical Foundation | P0 | 64h | Medium | Low-Medium |
| Monitoring & Observability | P0 | 40h | Medium | Low-Medium |
| Disaster Recovery | P1 | 44h | High | High |
| Horizontal Scaling | P1 | 32h | High | High |
| Production Hardening | P2 | 28h | Medium | Medium |
| **Total** | | **208h** | | |

**Estimated Timeline:** 30 calendar days (assuming 1 developer, 8h/day)
**Recommended Team:** 2-3 developers (reduces to ~15 calendar days)
**Critical Path:** Docker Compose → PostgreSQL → Secrets → Monitoring → DR → Scaling

---

## Appendix A: File Structure

```
deployment/
├── docker-compose.prod.yml
├── docker-compose.override.yml
├── nginx.prod.conf
├── nginx-lb.conf
├── haproxy.cfg
├── ssl/
│   ├── fullchain.pem
│   └── privkey.pem
├── postgres/
│   ├── postgresql.conf
│   └── pg_hba.conf
├── prometheus/
│   ├── prometheus.yml
│   └── alerts.yml
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   └── dashboards/
│   └── dashboards/
│       ├── quantive-overview.json
│       ├── quantive-backend.json
│       └── quantive-database.json
├── loki/
│   └── loki.yml
└── backup/
    ├── backup.sh
    ├── restore.sh
    └── verify.sh

scripts/
├── deploy-prod.sh
├── deploy-production.sh
├── backup.sh
├── restore.sh
├── verify-backup.sh
├── verify-deployment.sh
├── validate-env.sh
├── generate-secrets.sh
├── setup-replication.sh
├── failover.sh
├── scale-backend.sh
├── init-db.sql
├── init-extensions.sql
├── init-partitions.sql
└── setup_rls.py

secrets/                          # NOT committed to git
├── postgres_password.txt
├── redis_password.txt
├── secret_key.txt
├── stripe_secret_key.txt
├── stripe_webhook_secret.txt
└── ssl/
    ├── fullchain.pem
    └── privkey.pem
```

## Appendix B: Monitoring Queries

```sql
-- Database performance monitoring
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    n_live_tup,
    n_dead_tup,
    last_vacuum,
    last_autovacuum,
    last_analyze
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Connection monitoring
SELECT
    datname,
    numbackends,
    xact_commit,
    xact_rollback,
    blks_read,
    blks_hit,
    tup_returned,
    tup_fetched
FROM pg_stat_database
WHERE datname = 'quantive';

-- Query performance (requires pg_stat_statements)
SELECT
    calls,
    mean_exec_time,
    max_exec_time,
    query
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

## Appendix C: Emergency Runbook

```markdown
# Emergency Runbook

## Database Down
1. Check container: `docker compose ps postgres`
2. Check logs: `docker compose logs postgres | tail -50`
3. Restart: `docker compose restart postgres`
4. If persistent: `docker compose up -d postgres`

## Backend Down
1. Check container: `docker compose ps backend`
2. Check logs: `docker compose logs backend | tail -50`
3. Restart: `docker compose restart backend`
4. If persistent: `docker compose up -d backend`

## SSL Certificate Expired
1. Check expiry: `echo | openssl s_client -servername yourdomain.gov -connect yourdomain.gov:443 2>/dev/null | openssl x509 -noout -enddate`
2. Renew: Use certbot or contact certificate provider
3. Reload nginx: `docker compose exec nginx nginx -s reload`

## Disk Space Low
1. Check: `docker system df`
2. Clean: `docker system prune -a`
3. Backup cleanup: `find /backups -name "*.sql.gz" -mtime +7 -delete`

## High Memory Usage
1. Check: `docker stats`
2. Restart culprit: `docker compose restart <service>`
3. Scale: `docker compose up -d --scale backend=3`
```
