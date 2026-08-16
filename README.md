# Quantive

Blockchain compliance and risk monitoring for crypto teams that need a focused, fast, and audit-ready platform — without enterprise bloat.

## Architecture

- **Backend** — Node.js + Express + TypeScript API (PostgreSQL, Redis, BullMQ, MinIO)
- **Frontend** — React 18 + TypeScript + Vite + Tailwind CSS SPA
- **Automation** — n8n workflow integration (55+ automation templates)

## Quick start

```bash
# Start infrastructure (PostgreSQL, Redis, MinIO)
docker compose -f backend/docker-compose.yml up -d

# Install dependencies
cd backend && npm install
cd ../frontend && npm install

# Setup database
cd ../backend && npx prisma generate && npx prisma db push && npx tsx prisma/seed.ts

# Start development
make dev-all
```

The API runs on `http://localhost:4000` and the frontend on `http://localhost:3000`.

## API docs

Swagger UI available at `http://localhost:4000/api/v1/docs` when the server is running.

## Environment

Copy `backend/.env.example` to `backend/.env` and fill in the required values.
