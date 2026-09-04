"""FastAPI application entrypoint."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from quantive import __version__
from quantive.api.routers import (
    optimization,
    portfolios,
    risk,
    procurement,
    early_warning,
    reasoning,
)

# CORS configuration from environment variables
# Default to development-friendly settings; override in production
CORS_ORIGINS = os.getenv(
    "QUANTIVE_CORS_ORIGINS", ""
).split(",") if os.getenv("QUANTIVE_CORS_ORIGINS") else ["*"]

CORS_METHODS = os.getenv(
    "QUANTIVE_CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS"
).split(",")

CORS_HEADERS = os.getenv(
    "QUANTIVE_CORS_HEADERS", "Authorization,Content-Type"
).split(",")

app = FastAPI(
    title="Quantive — Optimization Engine",
    version=__version__,
    description="Public debt optimization API. Optimization is the product; "
                "quantum is a computational capability, not a marketing claim.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
)

app.include_router(portfolios.router)
app.include_router(optimization.router)
app.include_router(procurement.router)
app.include_router(early_warning.router)
app.include_router(risk.router)
app.include_router(reasoning.router)


@app.get("/")
def root() -> dict:
    return {
        "name": "Quantive",
        "version": __version__,
        "docs": "/docs",
        "health": "ok",
        "endpoints": [
            "POST /portfolios",
            "GET /portfolios/{id}",
            "POST /optimization",
            "GET /optimization/{id}",
            "POST /optimization/{id}/run",
            "GET /optimization/{id}/results",
            "GET /optimization/{id}/strategies",
            "GET /optimization/{id}/benchmark",
            "GET /optimization/{id}/scenarios",
            "GET /optimization/{id}/stress",
            "GET /risk/cyber/summary",
            "GET /risk/fiscal/summary",
            "GET /risk/climate/summary",
            "GET /risk/infrastructure/summary",
            "GET /risk/geopolitical/summary",
            "GET /risk/supply-chain/summary",
            "GET /risk/aggregate/{entity_id}",
            "GET /risk/early-warning/{entity_id}",
            "GET /early-warning/signals/{entity_id}",
            "POST /early-warning/detect/{entity_id}",
            "GET /early-warning/indicators",
            "GET /early-warning/categories",
            "GET /early-warning/scenarios/project",
            "GET /procurement/health/check",
            "GET /reasoning/refinancing/{portfolio_id}",
            "GET /reasoning/profile/{portfolio_id}",
            "POST /reasoning/dangerous-assumptions",
            "POST /reasoning/cross-layer",
        ],
    }