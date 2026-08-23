# Contributing to Quantive

## Development Setup

1. Clone the repository
2. Set up the backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   cp ../.env.example .env
   ```
3. Set up the frontend:
   ```bash
   cd frontend
   npm install
   ```

## Running Locally

Backend:
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm run dev
```

## Code Style

### Python
- Follow PEP 8
- Use type hints
- Keep functions focused and small

### TypeScript
- Use strict TypeScript
- Prefer functional components
- Keep components focused

## Testing

Run all tests:
```bash
cd backend
python -m pytest tests/ -v
```

Key test categories:
- `test_auth.py` - Authentication and authorization
- `test_portfolios.py` - Portfolio CRUD and file upload
- `test_optimization.py` - Optimization workflow
- `test_e2e.py` - Full end-to-end integration test
- `test_failures.py` - Error handling and edge cases

## Commit Messages

Use clear, descriptive commit messages:
- `feat: add scenario generator`
- `fix: handle empty portfolio in optimizer`
- `test: add failure tests for upload validation`

## Security

- Never commit secrets or API keys
- Validate all user input
- Use parameterized queries (SQLAlchemy handles this)
- Follow the existing authentication patterns
