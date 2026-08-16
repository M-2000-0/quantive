.PHONY: dev build up down seed lint typecheck

# Backend
dev:
	cd backend && npm run dev

build:
	cd backend && npm run build

up:
	docker compose -f backend/docker-compose.yml up -d

down:
	docker compose -f backend/docker-compose.yml down

seed:
	cd backend && npx prisma db push && npx tsx prisma/seed.ts

lint:
	cd backend && npm run lint

typecheck:
	cd backend && npm run typecheck

# Frontend
dev-frontend:
	cd frontend && npm run dev

build-frontend:
	cd frontend && npm run build

# Full stack
dev-all:
	@echo "Starting API, frontend, and workers..."
	@cd backend && npm run dev &
	@cd frontend && npm run dev &
	@wait

# Database
db-generate:
	cd backend && npx prisma generate

db-push:
	cd backend && npx prisma db push

db-migrate:
	cd backend && npx prisma migrate dev

# Setup fresh
setup:
	cd backend && npm install
	cd frontend && npm install
	docker compose -f backend/docker-compose.yml up -d
	cd backend && npx prisma generate && npx prisma db push && npx tsx prisma/seed.ts
	@echo "Ready! Run 'make dev-all' to start development."
