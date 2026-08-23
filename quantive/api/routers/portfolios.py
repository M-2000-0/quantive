"""Portfolio endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from quantive.api.schemas import PortfolioCreateRequest, PortfolioUploadRequest, SyntheticPortfolioRequest
from quantive.api.state import state
from quantive.data.synthetic import SyntheticPortfolioGenerator
from quantive.models.instruments import Portfolio, make_portfolio

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post("", status_code=201)
def create_portfolio(request: PortfolioCreateRequest) -> Portfolio:
    if isinstance(request, SyntheticPortfolioRequest):
        portfolio_id = request.portfolio_id or f"portfolio-{uuid.uuid4().hex[:8]}"
        portfolio = SyntheticPortfolioGenerator(seed=request.seed).portfolio(
            portfolio_id=portfolio_id, name=request.name,
        )
    else:
        request: PortfolioUploadRequest
        portfolio_id = request.portfolio_id or f"portfolio-{uuid.uuid4().hex[:8]}"
        portfolio = make_portfolio(
            portfolio_id=portfolio_id,
            name=request.name,
            instruments=request.instruments,
            reference_currency=request.reference_currency,
            description=request.description,
            tags=request.tags,
        )
    state.add_portfolio(portfolio)
    return portfolio


@router.get("")
def list_portfolios() -> list[Portfolio]:
    return list(state.portfolios.values())


@router.get("/{portfolio_id}")
def get_portfolio(portfolio_id: str) -> Portfolio:
    portfolio = state.get_portfolio(portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail=f"portfolio {portfolio_id!r} not found")
    return portfolio