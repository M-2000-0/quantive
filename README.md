# Quantive — Quantum-AI Sovereign Debt Optimizer

> AI-powered investment analytics platform with quantum computing, Monte Carlo simulation, and real-time market data integration.

## Architecture

```
backend/
├── app/
│   ├── api/              # FastAPI route handlers (82 modules)
│   ├── data/             # DuckDB, yield fetcher, financial models
│   ├── market_data/      # Real-time Treasury, FRED, World Bank data
│   ├── optimization/     # QUBO, Monte Carlo, policy engine
│   ├── quantum/          # QAOA circuit, hybrid solver, state encoder
│   ├── security/         # CSRF, RBAC, rate limiter, idempotency
│   ├── templates/        # Jinja2 HTML templates (102 pages)
│   ├── static/           # CSS, JS, Chart.js
│   └── main.py           # FastAPI application entry
├── tests/                # Test suite
└── requirements.txt      # Python dependencies
```

## Quick Start

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run development server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Open in browser
# http://127.0.0.1:8000/dashboard
```

## Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/dashboard` | GET | Main analytics dashboard |
| `/debt-optimizer` | GET | Quantum debt optimizer |
| `/trading-hub` | GET | Trading intelligence hub |
| `/api/optimize-debt/quick` | POST | Quick optimization (real Treasury data) |
| `/api/v1/optimize` | POST | Enterprise QUBO optimization |
| `/api/v1/simulate` | POST | 10K Monte Carlo stress tests |
| `/api/v1/report` | POST | AI policy briefing generation |
| `/api/v1/status` | GET | System health check |

## Features

- **Quantum Optimization**: QUBO formulation with QAOA circuit simulation
- **Monte Carlo Simulation**: 10,000+ path stress testing with 8 scenarios
- **Real-Time Data**: US Treasury yield curve, FRED API, World Bank data
- **AI Policy Engine**: LLM-powered policy briefings (Ollama/OpenAI/Anthropic)
- **Security**: CSRF, RBAC, rate limiting, MFA, idempotency keys
- **Data Pipeline**: DuckDB storage, async ingestion, schema validation
- **Backup System**: Automated compressed backups with rotation
- **Rate Limiting**: Per-IP sliding window throttling

## Configuration

Environment variables (set in `.env`):

```bash
SECRET_KEY=your-secret-key
FRED_API_KEY=your-fred-api-key  # Optional, for enhanced data
DATABASE_URL=sqlite:///app/data/quantive.db
```

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

## Production

```bash
# Run with Gunicorn
cd backend
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## License

Proprietary — Quantive
