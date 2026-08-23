.PHONY: dev test lint typecheck docker-up docker-down migrate demo

dev-backend:
	cd backend && python -m uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

dev: dev-backend dev-frontend

test-backend:
	cd backend && python -m pytest tests -q

test-engine:
	python -m pytest tests -q

test-frontend:
	cd frontend && npm run build

test: test-backend test-engine test-frontend

lint:
	cd frontend && npm run lint
	cd backend && python -m ruff check app/ tests/

typecheck:
	cd frontend && npx tsc --noEmit
	cd backend && python -m mypy app/ --ignore-missing-imports

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

migrate:
	cd backend && python -m alembic upgrade head

demo:
	python scripts/demo.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
