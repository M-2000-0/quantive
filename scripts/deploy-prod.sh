#!/bin/bash
# Quantive Production Deployment Script
# Usage: ./scripts/deploy-prod.sh

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Quantive Production Deployment                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── Check Prerequisites ──────────────────────────────────────────────
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Install: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Install: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker installed${NC}"
echo -e "${GREEN}✓ Docker Compose installed${NC}"

# ── Check Environment File ───────────────────────────────────────────
if [ ! -f .env.production ]; then
    echo ""
    echo -e "${YELLOW}No .env.production file found.${NC}"
    echo "Creating from template..."
    cp .env.production.example .env.production
    echo ""
    echo -e "${YELLOW}⚠️  Please edit .env.production with secure values before continuing.${NC}"
    echo ""
    echo "Required changes:"
    echo "  1. SECRET_KEY - Generate with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    echo "  2. POSTGRES_PASSWORD - Secure database password"
    echo "  3. REDIS_PASSWORD - Secure Redis password"
    echo "  4. CORS_ORIGINS - Your production domain"
    echo ""
    echo "After editing, run this script again."
    exit 0
fi

# ── Generate Secrets if Default ──────────────────────────────────────
source .env.production

if [ "$SECRET_KEY" = "change-me-to-a-random-64-char-string" ]; then
    echo -e "${RED}Error: SECRET_KEY is still the default value${NC}"
    echo "Generate a secure key: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    exit 1
fi

if [ "$POSTGRES_PASSWORD" = "change-me-to-a-secure-password" ]; then
    echo -e "${RED}Error: POSTGRES_PASSWORD is still the default value${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Environment configured${NC}"

# ── Create SSL Directory ─────────────────────────────────────────────
mkdir -p deployment/ssl

if [ ! -f deployment/ssl/fullchain.pem ]; then
    echo ""
    echo -e "${YELLOW}⚠️  No SSL certificates found in deployment/ssl/${NC}"
    echo ""
    echo "Options:"
    echo "  1. Place your SSL certificates:"
    echo "     - deployment/ssl/fullchain.pem"
    echo "     - deployment/ssl/privkey.pem"
    echo ""
    echo "  2. Or generate self-signed (development only):"
    echo "     openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\"
    echo "       -keyout deployment/ssl/privkey.pem \\"
    echo "       -out deployment/ssl/fullchain.pem \\"
    echo "       -subj '/CN=localhost'"
    echo ""
    echo -e "${YELLOW}Proceeding with self-signed certificate for now...${NC}"
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout deployment/ssl/privkey.pem \
        -out deployment/ssl/fullchain.pem \
        -subj '/CN=localhost' 2>/dev/null
    
    echo -e "${GREEN}✓ Self-signed certificate generated${NC}"
fi

# ── Build and Deploy ─────────────────────────────────────────────────
echo ""
echo "Building production images..."
docker compose -f docker-compose.prod.yml build --no-cache

echo ""
echo "Starting services..."
docker compose -f docker-compose.prod.yml up -d

# ── Wait for Health Checks ──────────────────────────────────────────
echo ""
echo "Waiting for services to be healthy..."
sleep 10

# Check PostgreSQL
if docker compose -f docker-compose.prod.yml exec -T postgres pg_isready -U quantive; then
    echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
else
    echo -e "${RED}✗ PostgreSQL failed to start${NC}"
fi

# Check Redis
if docker compose -f docker-compose.prod.yml exec -T redis redis-cli -a "$REDIS_PASSWORD" ping | grep -q PONG; then
    echo -e "${GREEN}✓ Redis is ready${NC}"
else
    echo -e "${RED}✗ Redis failed to start${NC}"
fi

# Check Backend
if curl -sf http://localhost/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is ready${NC}"
else
    echo -e "${YELLOW}⏳ Backend is still starting...${NC}"
fi

# ── Summary ──────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Deployment Complete!                                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Services:"
echo "  - Backend API:   https://yourdomain.gov/api"
echo "  - Frontend:      https://yourdomain.gov"
echo "  - Health Check:  https://yourdomain.gov/api/health"
echo "  - PostgreSQL:    localhost:5432 (internal only)"
echo "  - Redis:         localhost:6379 (internal only)"
echo ""
echo "Useful commands:"
echo "  - View logs:     docker compose -f docker-compose.prod.yml logs -f"
echo "  - Stop services: docker compose -f docker-compose.prod.yml down"
echo "  - Restart:       docker compose -f docker-compose.prod.yml restart"
echo "  - Scale backend: docker compose -f docker-compose.prod.yml up -d --scale backend=2"
echo ""
